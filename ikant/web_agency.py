from __future__ import annotations

from typing import Any

from .execution_receipts import EXECUTION_RECEIPT_SCHEMA, seal_receipt
from .web_actions import required_entitlements, validate_web_action
from .web_snapshot import origin_from_url

WEB_EXECUTION_SCHEMA = 'ikant-web-execution/v0.21-test'


class WebAgencyError(PermissionError):
    pass


def _lease_entitlements(lease: dict[str, Any]) -> set[tuple[str, str]]:
    return {(str(x.get('capability') or ''), str(x.get('resource') or '')) for x in lease.get('entitlements', []) or []}


def _allowed_origins(action: dict[str, Any], snapshot: dict[str, Any], lease: dict[str, Any]) -> frozenset[str]:
    origins = {snapshot['origin']}
    if action.get('verb') == 'NAVIGATE':
        origins.add(origin_from_url(action['target_url']))
    for cap, resource in _lease_entitlements(lease):
        if cap == 'web.navigate' and resource.startswith('web-url:'):
            try: origins.add(origin_from_url(resource[len('web-url:'):]))
            except ValueError: pass
    return frozenset(origins)


class WebAgency:
    """Conjunctive browser actuator: current snapshot + exact S1 lease + v0.18 host revalidation.

    It intentionally owns the material browser call: S1 and v0.18 remain zero-authority preconditions.
    The lease is consumed immediately before the external browser commit, making retries require a new
    lease while preserving a clear commit point.
    """
    def __init__(self, *, browser, agency_kernel, agency_host_binding):
        self.browser = browser
        self.agency = agency_kernel
        self.host = agency_host_binding

    def observe(self):
        return self.browser.snapshot()

    def execute(self, action: dict[str, Any], envelope: dict[str, Any], lease: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.browser.snapshot()
        ok, errors = validate_web_action(action, snapshot)
        if not ok:
            raise WebAgencyError('web action invalid or stale: ' + '; '.join(errors))
        expected = set(required_entitlements(action))
        actual = _lease_entitlements(lease)
        if actual != expected:
            raise WebAgencyError('S1 lease entitlements do not exactly bind web action')
        required_caps = {str(x).strip().casefold() for x in envelope.get('required_capabilities', []) or []}
        if required_caps != {action['capability']}:
            raise WebAgencyError('handoff required capabilities do not exactly bind web action')
        preflight = self.browser.preflight(action)
        if preflight.snapshot['sha256'] != snapshot['sha256']:
            raise WebAgencyError('web snapshot drift during preflight')
        revalidation = self.host.revalidate_execution(envelope, lease)
        after_host = self.browser.snapshot()
        if after_host['sha256'] != snapshot['sha256']:
            raise WebAgencyError('web snapshot drift after host revalidation')
        self.agency.consume_lease(lease['lease_id'], reason='S3 browser actuator commit point reached')
        allowed_origins = _allowed_origins(action, snapshot, lease)
        try:
            outcome = self.browser.commit(preflight, allowed_navigation_origins=allowed_origins)
            status = 'EXECUTED'
            execution_ref = str(outcome.get('execution_ref') or '')
        except Exception as exc:
            outcome = {'status': 'FAILED', 'error_type': type(exc).__name__, 'observed_predicates': [], 'world_truth_verified': False, 'epistemic_authority': 0.0}
            status = 'FAILED'
            execution_ref = 'web-failed-' + action['sha256'][:16]
        receipt = seal_receipt({'schema': EXECUTION_RECEIPT_SCHEMA, **{k: envelope.get(k) for k in ('session_id', 'cycle_id', 'intent_sha256', 'handoff_id', 'idempotency_key', 'action_fingerprint', 'action_ledger_sha256', 'plan_ledger_sha256')}, 'actor_type': 'host', 'outcome': status, 'execution_ref': execution_ref, 'observed_predicates': list(outcome.get('observed_predicates') or []), 'runtime_epistemic_authority': 0.0, 'grants_runtime_execution_authority': False, 'causes_runtime_execution': False})
        return {'schema': WEB_EXECUTION_SCHEMA, 'action_sha256': action['sha256'], 'snapshot_sha256': snapshot['sha256'], 'lease_id': lease['lease_id'], 'lease_consumed_before_external_commit': True, 'host_revalidation': revalidation.get('host_revalidation') if isinstance(revalidation, dict) else revalidation, 'browser_outcome': outcome, 'execution_receipt': receipt, 'world_truth_verified': False, 'web_content_was_authority': False, 'epistemic_authority': 0.0, 'execution_authority': 0.0}
