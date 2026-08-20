from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Any
from urllib.parse import urljoin

from .web_actions import validate_web_action
from .web_snapshot import build_snapshot, canonical_url, origin_from_url


class WebDriverError(RuntimeError):
    pass


@dataclass
class PreparedWebAction:
    action: dict[str, Any]
    snapshot: dict[str, Any]
    opaque: Any = None


class InMemoryBrowserAdapter:
    """Deterministic browser model used for executable boundary tests."""
    def __init__(self, *, session_id='S', browser_id='B', page_id='P', url='https://example.test/', title='Example', text='Example page', controls=()):
        self.session_id = session_id; self.browser_id = browser_id; self.page_id = page_id
        self.url = canonical_url(url); self.title = title; self.text = text; self.controls = list(controls); self.navigation_epoch = 0; self.executions = 0

    def snapshot(self):
        return build_snapshot(session_id=self.session_id, browser_id=self.browser_id, page_id=self.page_id, navigation_epoch=self.navigation_epoch, url=self.url, title=self.title, visible_text=self.text, controls=self.controls)

    def preflight(self, action):
        snap = self.snapshot(); ok, errors = validate_web_action(action, snap)
        if not ok: raise WebDriverError('web action preflight failed: ' + '; '.join(errors))
        return PreparedWebAction(dict(action), snap, None)

    def commit(self, prepared: PreparedWebAction, *, allowed_navigation_origins: set[str] | frozenset[str]):
        current = self.snapshot()
        if current['sha256'] != prepared.snapshot['sha256']:
            raise WebDriverError('web snapshot drift before commit')
        action = prepared.action; self.executions += 1
        if action['verb'] == 'NAVIGATE':
            target = canonical_url(action['target_url'])
            if origin_from_url(target) not in set(allowed_navigation_origins):
                raise WebDriverError('navigation origin not leased')
            self.url = target; self.navigation_epoch += 1
        elif action['verb'] == 'CLICK':
            target = next(x for x in current['controls'] if x['control_id'] == action['target_id'])
            if target.get('href'):
                dest = canonical_url(target['href'])
                if origin_from_url(dest) not in set(allowed_navigation_origins):
                    raise WebDriverError('click navigation origin not leased')
                self.url = dest; self.navigation_epoch += 1
        elif action['verb'] == 'FILL':
            pass
        else:
            raise WebDriverError('unsupported web action')
        return {'status': 'EXECUTED', 'execution_ref': 'webmem-' + secrets.token_hex(8), 'post_snapshot': self.snapshot(), 'observed_predicates': [], 'world_truth_verified': False, 'epistemic_authority': 0.0}


class PlaywrightBrowserAdapter:
    """Optional isolated Chromium actuator. Playwright is imported lazily.

    The model never supplies selectors or JavaScript. S3 captures a bounded control set and actions
    reference only generated control IDs from the exact current snapshot.
    """
    def __init__(self, *, session_id: str, headless: bool = True):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise WebDriverError('Playwright is optional; install the web extra and browser runtime') from exc
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=bool(headless))
        self._context = self._browser.new_context(accept_downloads=False)
        self._page = self._context.new_page()
        self.session_id = str(session_id); self.browser_id = 'pw-' + secrets.token_hex(8); self.page_id = 'page-' + secrets.token_hex(8); self.navigation_epoch = 0
        # The real browser starts at about:blank. Any network navigation must pass through S1/S3.

    def close(self):
        try: self._context.close()
        finally:
            try: self._browser.close()
            finally: self._pw.stop()

    def _controls(self):
        locator = self._page.locator('a,button,input,textarea,select,[role="button"],[role="link"],[role="textbox"],[role="searchbox"],[role="combobox"]')
        count = min(locator.count(), 256); out = []
        for i in range(count):
            loc = locator.nth(i)
            try:
                tag = loc.evaluate('(el) => el.tagName.toLowerCase()')
                role = loc.get_attribute('role') or ''
                label = loc.get_attribute('aria-label') or loc.get_attribute('placeholder') or ''
                if not label:
                    try: label = loc.inner_text(timeout=150)
                    except Exception: label = ''
                href = loc.get_attribute('href')
                if href: href = urljoin(self._page.url, href)
                out.append({'ordinal': i, 'tag': tag, 'role': role, 'name': label[:4096], 'href': href, 'input_type': loc.get_attribute('type') or '', 'disabled': loc.is_disabled()})
            except Exception:
                continue
        return out

    def snapshot(self):
        try: text = self._page.locator('body').inner_text(timeout=1000)
        except Exception: text = ''
        try: title = self._page.title()
        except Exception: title = ''
        return build_snapshot(session_id=self.session_id, browser_id=self.browser_id, page_id=self.page_id, navigation_epoch=self.navigation_epoch, url=self._page.url, title=title, visible_text=text, controls=self._controls())

    def preflight(self, action):
        snap = self.snapshot(); ok, errors = validate_web_action(action, snap)
        if not ok: raise WebDriverError('web action preflight failed: ' + '; '.join(errors))
        opaque = None
        if action['verb'] in {'CLICK', 'FILL'}:
            target = next(x for x in snap['controls'] if x['control_id'] == action['target_id'])
            locator = self._page.locator('a,button,input,textarea,select,[role="button"],[role="link"],[role="textbox"],[role="searchbox"],[role="combobox"]').nth(int(target['ordinal']))
            opaque = locator.element_handle(timeout=1000)
            if opaque is None: raise WebDriverError('target element unavailable')
        return PreparedWebAction(dict(action), snap, opaque)

    def _guard_navigation(self, allowed_origins, *, exact_urls=()):
        allowed = set(allowed_origins); exact = {canonical_url(x) for x in exact_urls}
        blocked = []
        def handler(route):
            request = route.request
            if request.is_navigation_request():
                # Popups/new top-level pages are never a permitted side channel in S3.
                if request.frame != self._page.main_frame and getattr(request.frame, 'parent_frame', None) is None:
                    blocked.append(request.url); return route.abort()
                if request.frame == self._page.main_frame:
                    try:
                        current = canonical_url(request.url); origin = origin_from_url(current)
                    except ValueError:
                        blocked.append(request.url); return route.abort()
                    if origin not in allowed or (exact and current not in exact):
                        blocked.append(request.url); return route.abort()
            return route.continue_()
        self._context.route('**/*', handler)
        return blocked

    def commit(self, prepared: PreparedWebAction, *, allowed_navigation_origins):
        current = self.snapshot()
        if current['sha256'] != prepared.snapshot['sha256']:
            raise WebDriverError('web snapshot drift before commit')
        action = prepared.action
        exact_urls = (action['target_url'],) if action['verb'] == 'NAVIGATE' else ()
        blocked = self._guard_navigation(allowed_navigation_origins, exact_urls=exact_urls)
        try:
            if action['verb'] == 'NAVIGATE':
                self._page.goto(action['target_url'], wait_until='domcontentloaded', timeout=15000)
                self.navigation_epoch += 1
            elif action['verb'] == 'CLICK':
                if prepared.opaque is None: raise WebDriverError('missing exact target handle')
                prepared.opaque.click(timeout=5000)
            elif action['verb'] == 'FILL':
                if prepared.opaque is None: raise WebDriverError('missing exact target handle')
                prepared.opaque.fill(action['value'], timeout=5000)
            else:
                raise WebDriverError('unsupported web action')
            if blocked:
                raise WebDriverError('browser blocked unleased navigation')
            return {'status': 'EXECUTED', 'execution_ref': 'webpw-' + secrets.token_hex(8), 'post_snapshot': self.snapshot(), 'observed_predicates': [], 'world_truth_verified': False, 'epistemic_authority': 0.0}
        finally:
            self._context.unroute('**/*')
