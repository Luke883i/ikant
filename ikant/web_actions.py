from __future__ import annotations

import hashlib
import json
from typing import Any

from .web_snapshot import canonical_url, validate_snapshot
from .human_frame import normalize_capability, normalize_resource

WEB_ACTION_SCHEMA = 'ikant-web-action/v0.21-test'
_ALLOWED = {'NAVIGATE': 'web.navigate', 'CLICK': 'web.click', 'FILL': 'web.fill'}
_MAX_VALUE_BYTES = 64 * 1024
_FORBIDDEN_FILL_TYPES = frozenset({'password', 'file', 'hidden', 'submit', 'button', 'reset', 'image'})


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _value_sha(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _target(snapshot: dict[str, Any], target_id: str) -> dict[str, Any]:
    rows = [x for x in snapshot.get('controls', []) or [] if x.get('control_id') == target_id]
    if len(rows) != 1:
        raise ValueError('web target is missing or ambiguous in snapshot')
    return rows[0]


def build_web_action(snapshot: dict[str, Any], *, verb: str, target_id: str | None = None, url: str | None = None, value: str | None = None) -> dict[str, Any]:
    ok, errors = validate_snapshot(snapshot)
    if not ok:
        raise ValueError('invalid snapshot: ' + '; '.join(errors))
    action_verb = str(verb or '').upper()
    capability = _ALLOWED.get(action_verb)
    if not capability:
        raise ValueError('unsupported web action verb')
    target = None
    target_url = None
    plaintext = None
    value_sha256 = None
    if action_verb == 'NAVIGATE':
        if target_id is not None or value is not None:
            raise ValueError('navigate accepts url only')
        target_url = canonical_url(url)
        if target_url == 'about:blank':
            raise ValueError('about:blank is internal state, not a material navigation target')
        resource = 'web-url:' + target_url
    else:
        if url is not None:
            raise ValueError('target action does not accept url')
        if not target_id:
            raise ValueError('target_id required')
        target = _target(snapshot, str(target_id))
        if target.get('disabled'):
            raise ValueError('disabled web target')
        base = 'web-target:' + snapshot['origin'] + '/' + snapshot['sha256'] + '/' + target['control_id']
        if action_verb == 'CLICK':
            if value is not None:
                raise ValueError('click does not accept value')
            if target.get('tag') != 'a' or not target.get('href'):
                raise ValueError('S3 click is restricted to explicit http(s) links')
            target_url = canonical_url(target['href'])
            resource = base
        else:
            if target.get('tag') not in {'input', 'textarea'}:
                raise ValueError('fill target must be input or textarea in S3')
            if str(target.get('input_type') or '').lower() in _FORBIDDEN_FILL_TYPES:
                raise ValueError('sensitive or side-effecting fill target type forbidden in S3')
            plaintext = str(value if value is not None else '')
            if len(plaintext.encode('utf-8')) > _MAX_VALUE_BYTES:
                raise ValueError('fill value exceeds bound')
            value_sha256 = _value_sha(plaintext)
            resource = base + '/sha256-' + value_sha256
    capability = normalize_capability(capability)
    resource = normalize_resource(resource)
    meta = {
        'schema': WEB_ACTION_SCHEMA,
        'session_id': snapshot['session_id'],
        'browser_id': snapshot['browser_id'],
        'page_id': snapshot['page_id'],
        'navigation_epoch': snapshot['navigation_epoch'],
        'snapshot_sha256': snapshot['sha256'],
        'verb': action_verb,
        'capability': capability,
        'resource': resource,
        'target_id': None if target is None else target['control_id'],
        'target_url': target_url,
        'value_sha256': value_sha256,
        'web_content_is_untrusted': True,
        'selector_generated_by_model': False,
        'arbitrary_javascript_allowed': False,
        'requires_s1_lease': True,
        'requires_fresh_host_revalidation': True,
        'epistemic_authority': 0.0,
        'execution_authority': 0.0,
    }
    meta['sha256'] = _digest(meta)
    if plaintext is not None:
        meta['value'] = plaintext
    return meta


def bound_web_resource(action: dict[str, Any], envelope: dict[str, Any]) -> str:
    action_sha = str(action.get('sha256') or '')
    handoff_id = str(envelope.get('handoff_id') or '')
    fingerprint = str(envelope.get('action_fingerprint') or '')
    idempotency = str(envelope.get('idempotency_key') or '')
    if len(action_sha) != 64 or not handoff_id or not fingerprint or not idempotency:
        raise ValueError('web execution binding incomplete')
    return normalize_resource(
        'web-action:' + action_sha + '/' + handoff_id + '/af-' + _value_sha(fingerprint) + '/ik-' + _value_sha(idempotency)
    )


def required_entitlements(action: dict[str, Any], envelope: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    capability = normalize_capability(action.get('capability'))
    required = tuple(sorted({normalize_capability(x) for x in envelope.get('required_capabilities', []) or []}))
    if required != (capability,):
        raise ValueError('handoff required capabilities do not exactly bind web action')
    return ((capability, bound_web_resource(action, envelope)),)


def validate_web_action(action: dict[str, Any], snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    raw = dict(action or {})
    errors: list[str] = []
    ok, se = validate_snapshot(snapshot)
    if not ok:
        errors.extend('snapshot:' + x for x in se)
    if raw.get('schema') != WEB_ACTION_SCHEMA:
        errors.append('action schema')
    verb = str(raw.get('verb') or '')
    if _ALLOWED.get(verb) != raw.get('capability'):
        errors.append('action capability')
    for key in ('session_id', 'browser_id', 'page_id', 'navigation_epoch'):
        if raw.get(key) != snapshot.get(key):
            errors.append('action ' + key)
    if raw.get('snapshot_sha256') != snapshot.get('sha256'):
        errors.append('action snapshot')
    if raw.get('web_content_is_untrusted') is not True or raw.get('selector_generated_by_model') is not False or raw.get('arbitrary_javascript_allowed') is not False:
        errors.append('action trust boundary')
    if raw.get('requires_s1_lease') is not True or raw.get('requires_fresh_host_revalidation') is not True:
        errors.append('action governance')
    if raw.get('epistemic_authority') not in {0, 0.0} or raw.get('execution_authority') not in {0, 0.0}:
        errors.append('action authority')
    if verb == 'NAVIGATE':
        try:
            target_url = canonical_url(raw.get('target_url'))
        except ValueError:
            errors.append('action target url')
            target_url = ''
        if target_url and raw.get('resource') != 'web-url:' + target_url:
            errors.append('action navigate resource')
        if raw.get('target_id') is not None or raw.get('value_sha256') is not None or 'value' in raw:
            errors.append('action navigate shape')
    elif verb in {'CLICK', 'FILL'}:
        try:
            target = _target(snapshot, str(raw.get('target_id') or ''))
        except ValueError:
            errors.append('action target')
            target = None
        base = None if target is None else 'web-target:' + snapshot['origin'] + '/' + snapshot['sha256'] + '/' + target['control_id']
        if verb == 'CLICK':
            if target is not None and (target.get('tag') != 'a' or not target.get('href')):
                errors.append('action click target kind')
            expected_url = None
            if target is not None and target.get('href'):
                try: expected_url = canonical_url(target['href'])
                except ValueError: errors.append('action click href')
            if raw.get('target_url') != expected_url:
                errors.append('action click target url')
            if base and raw.get('resource') != base:
                errors.append('action click resource')
            if raw.get('value_sha256') is not None or 'value' in raw:
                errors.append('action click value')
        else:
            if target is not None and (target.get('tag') not in {'input', 'textarea'} or str(target.get('input_type') or '').lower() in _FORBIDDEN_FILL_TYPES):
                errors.append('action fill target kind')
            if raw.get('target_url') is not None:
                errors.append('action fill target url')
            value = raw.get('value')
            if not isinstance(value, str) or len(value.encode('utf-8')) > _MAX_VALUE_BYTES:
                errors.append('action fill value')
            expected_sha = _value_sha(value) if isinstance(value, str) else None
            if raw.get('value_sha256') != expected_sha:
                errors.append('action fill digest')
            if base and expected_sha and raw.get('resource') != base + '/sha256-' + expected_sha:
                errors.append('action fill resource')
    material = {k: v for k, v in raw.items() if k not in {'sha256', 'value'}}
    if raw.get('sha256') != _digest(material):
        errors.append('action digest')
    return not errors, errors
