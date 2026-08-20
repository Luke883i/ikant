from __future__ import annotations
from typing import Any
from .human_frame import build_human_frame
from .native_actions import required_entitlements,validate_native_action
from .native_snapshot import validate_target_snapshot

def native_action_summary(action:dict[str,Any],snapshot:dict[str,Any],envelope:dict[str,Any])->str:
    ok,e=validate_native_action(action,snapshot)
    if not ok:raise ValueError('invalid native action: '+'; '.join(e))
    h=str(envelope.get('handoff_id') or '')
    if not h:raise ValueError('native action summary requires handoff binding')
    if action['verb']=='READ_FILE':effect=f"Read exactly the UTF-8 text file {action['path']!r} inside the configured native workspace."
    else:effect=f"Create exactly the previously absent UTF-8 text file {action['path']!r} with the following exact content (sha256 {action['content_sha256']}):\n---\n{action['text']}\n---"
    return effect+f" Authorization is one-shot and bound to execution handoff {h}."

def build_native_grant_frame(snapshot:dict[str,Any],action:dict[str,Any],envelope:dict[str,Any],*,actor_binding_id:str,frame_seq:int,expires_at:float|None=None)->dict[str,Any]:
    ok,e=validate_target_snapshot(snapshot)
    if not ok:raise ValueError('invalid native snapshot: '+'; '.join(e))
    entitlements=required_entitlements(action,envelope)
    return build_human_frame(session_id=snapshot['session_id'],actor_binding_id=str(actor_binding_id),frame_seq=int(frame_seq),purpose='CAPABILITY_GRANT',title='Authorize one native file action',body=native_action_summary(action,snapshot,envelope),entitlements=entitlements,action_fingerprint=action['sha256'],handoff_id=str(envelope.get('handoff_id') or ''),max_uses=1,expires_at=expires_at)
