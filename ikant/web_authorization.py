from __future__ import annotations

from typing import Any

from .human_frame import build_human_frame
from .web_actions import required_entitlements, validate_web_action
from .web_snapshot import validate_snapshot


def web_action_summary(action: dict[str, Any], snapshot: dict[str, Any], envelope: dict[str, Any]) -> str:
    ok, errors = validate_web_action(action, snapshot)
    if not ok:
        raise ValueError('invalid web action: ' + '; '.join(errors))
    handoff = str(envelope.get('handoff_id') or '')
    if not handoff:
        raise ValueError('web action summary requires handoff binding')
    if action['verb'] == 'NAVIGATE':
        effect = f"Navigate the isolated browser to exactly {action['target_url']}."
    else:
        target = next(x for x in snapshot['controls'] if x['control_id'] == action['target_id'])
        label = target.get('name') or target.get('role') or target.get('tag') or target['control_id']
        if action['verb'] == 'CLICK':
            effect = f"Follow exactly the current-page link {label!r} ({target['control_id']}) to {action['target_url']}."
        else:
            effect = f"Fill exactly the current-page control {label!r} ({target['control_id']}) on {snapshot['origin']} with {action['value']!r}."
    return effect + f" Authorization is bound to execution handoff {handoff}."


def build_web_grant_frame(snapshot: dict[str, Any], action: dict[str, Any], envelope: dict[str, Any], *, actor_binding_id: str, frame_seq: int, expires_at: float | None = None) -> dict[str, Any]:
    ok, errors = validate_snapshot(snapshot)
    if not ok:
        raise ValueError('invalid web snapshot: ' + '; '.join(errors))
    ok, errors = validate_web_action(action, snapshot)
    if not ok:
        raise ValueError('invalid web action: ' + '; '.join(errors))
    entitlements = required_entitlements(action, envelope)
    return build_human_frame(
        session_id=snapshot['session_id'], actor_binding_id=str(actor_binding_id), frame_seq=int(frame_seq),
        purpose='CAPABILITY_GRANT', title='Authorize one web action', body=web_action_summary(action, snapshot, envelope),
        entitlements=entitlements, action_fingerprint=action['sha256'], handoff_id=str(envelope.get('handoff_id') or ''),
        max_uses=1, expires_at=expires_at,
    )
