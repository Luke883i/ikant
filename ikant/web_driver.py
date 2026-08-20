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

    def security_status(self):
        return {'isolated_context': True, 'javascript_disabled': True, 'service_workers_blocked': True, 'websockets_blocked': True, 'downloads_disabled': True, 'arbitrary_http_methods_blocked': True, 'extra_pages_blocked': True}

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
        action = prepared.action
        if action['verb'] in {'NAVIGATE', 'CLICK'}:
            target = canonical_url(action['target_url'])
            if origin_from_url(target) not in set(allowed_navigation_origins):
                raise WebDriverError('navigation origin not leased')
            self.executions += 1
            self.url = target; self.navigation_epoch += 1
        elif action['verb'] == 'FILL':
            self.executions += 1
        else:
            raise WebDriverError('unsupported web action')
        return {'status': 'EXECUTED', 'execution_ref': 'webmem-' + secrets.token_hex(8), 'post_snapshot': self.snapshot(), 'observed_predicates': [], 'world_truth_verified': False, 'epistemic_authority': 0.0, 'blocked_subrequests': 0}


class PlaywrightBrowserAdapter:
    """Optional isolated Chromium actuator with a deny-by-default network sandbox.

    Page JavaScript, Service Workers, WebSockets, downloads, extra pages and non-GET/HEAD
    requests are disabled or blocked. S3 actions never accept selectors or JavaScript and CLICK
    follows the exact snapshot href with page.goto rather than firing arbitrary page handlers.
    """
    def __init__(self, *, session_id: str, headless: bool = True):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise WebDriverError('Playwright is optional; install the web extra and browser runtime') from exc
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=bool(headless))
        self._context = self._browser.new_context(accept_downloads=False, java_script_enabled=False, service_workers='block')
        self._page = self._context.new_page()
        self.session_id = str(session_id); self.browser_id = 'pw-' + secrets.token_hex(8); self.page_id = 'page-' + secrets.token_hex(8); self.navigation_epoch = 0
        self._network_enabled = False; self._allowed_origins: set[str] = set(); self._exact_navigation_urls: set[str] = set(); self._blocked_subrequests: list[str] = []
        self._context.route('**/*', self._route_request)
        if hasattr(self._page, 'route_web_socket'):
            self._page.route_web_socket('**/*', lambda ws: ws.close())
        self._context.on('page', self._reject_extra_page)
        # Starts at about:blank. No network request occurs before an authorized S3 commit.

    def security_status(self):
        return {'isolated_context': True, 'javascript_disabled': True, 'service_workers_blocked': True, 'websockets_blocked': True, 'downloads_disabled': True, 'arbitrary_http_methods_blocked': True, 'extra_pages_blocked': True}

    def _reject_extra_page(self, page):
        if page != self._page:
            try: page.close()
            except Exception: pass

    def _route_request(self, route):
        request = route.request
        if not self._network_enabled:
            return route.abort()
        if str(request.method).upper() not in {'GET', 'HEAD'}:
            self._blocked_subrequests.append(request.url); return route.abort()
        try:
            current = canonical_url(request.url); origin = origin_from_url(current)
        except ValueError:
            self._blocked_subrequests.append(request.url); return route.abort()
        if origin not in self._allowed_origins:
            self._blocked_subrequests.append(request.url); return route.abort()
        if request.is_navigation_request():
            if request.frame != self._page.main_frame:
                self._blocked_subrequests.append(request.url); return route.abort()
            if self._exact_navigation_urls and current not in self._exact_navigation_urls:
                self._blocked_subrequests.append(request.url); return route.abort()
        return route.continue_()

    def close(self):
        try: self._context.close()
        finally:
            try: self._browser.close()
            finally: self._pw.stop()

    def _controls(self):
        locator = self._page.locator('a,input,textarea')
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
        if action['verb'] == 'FILL':
            target = next(x for x in snap['controls'] if x['control_id'] == action['target_id'])
            locator = self._page.locator('a,input,textarea').nth(int(target['ordinal']))
            opaque = locator.element_handle(timeout=1000)
            if opaque is None: raise WebDriverError('target element unavailable')
        return PreparedWebAction(dict(action), snap, opaque)

    def commit(self, prepared: PreparedWebAction, *, allowed_navigation_origins):
        current = self.snapshot()
        if current['sha256'] != prepared.snapshot['sha256']:
            raise WebDriverError('web snapshot drift before commit')
        action = prepared.action
        self._blocked_subrequests = []
        try:
            if action['verb'] in {'NAVIGATE', 'CLICK'}:
                target = canonical_url(action['target_url'])
                self._allowed_origins = set(allowed_navigation_origins)
                self._exact_navigation_urls = {target}
                self._network_enabled = True
                self._page.goto(target, wait_until='domcontentloaded', timeout=15000)
                if canonical_url(self._page.url) != target:
                    raise WebDriverError('navigation redirected away from exact authorized URL')
                self.navigation_epoch += 1
            elif action['verb'] == 'FILL':
                if prepared.opaque is None: raise WebDriverError('missing exact target handle')
                # Network remains deny-all during fill; page JavaScript is disabled.
                prepared.opaque.fill(action['value'], timeout=5000)
            else:
                raise WebDriverError('unsupported web action')
            return {'status': 'EXECUTED', 'execution_ref': 'webpw-' + secrets.token_hex(8), 'post_snapshot': self.snapshot(), 'observed_predicates': [], 'world_truth_verified': False, 'epistemic_authority': 0.0, 'blocked_subrequests': len(self._blocked_subrequests)}
        finally:
            self._network_enabled = False
            self._allowed_origins = set()
            self._exact_navigation_urls = set()
