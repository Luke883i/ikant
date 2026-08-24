from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import append_jsonl, atomic_json_write, fsync_parent

CAUSAL_LEDGER_SCHEMA = 'ikant-causal-ledger/v1-test'
CAUSAL_EVENT_SCHEMA = 'ikant-causal-event/v1-test'
UNDO_SCHEMA = 'ikant-causal-undo/v1-test'
TERMINAL = {'TURN_COMMITTED', 'TURN_ABORTED'}
_STAGE = {
    'TURN_OPEN': 0,
    'COGNITIVE_PREPARED': 1,
    'USER_CHAT_BOUND': 2,
    'SURFACE_A_VALIDATED': 3,
    'VISIBLE_CHAT_BOUND': 4,
    'FRAME_SEALED': 5,
    'TURN_COMMITTED': 6,
    'TURN_ABORTED': 6,
}
_EXCLUDED_PREFIXES = (
    'causal-ledger.jsonl', 'causal-undo/', 'egress.json', 'egress-events.jsonl',
    'egress-frames/', 'chat/transcript.jsonl', 'artifacts/'
)
_MAX_UNDO_BYTES = 64 * 1024 * 1024
_FORBIDDEN_KEYS = {'text','prompt','response_text','reasoning','chain_of_thought','cot','raw_prompt','raw_response'}

def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _canonical(v: Any) -> bytes: return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
def _sha(v: Any) -> str: return hashlib.sha256(_canonical(v)).hexdigest()
def _file_sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _ledger_path(runtime: Any) -> Path: return Path(runtime.state_dir) / 'causal-ledger.jsonl'
def _undo_root(runtime: Any) -> Path: return Path(runtime.state_dir) / 'causal-undo'
def _rel(path: Path, root: Path) -> str: return path.relative_to(root).as_posix()
def _included(rel: str) -> bool: return not any(rel == p or rel.startswith(p) for p in _EXCLUDED_PREFIXES)

def _sanitize_refs(refs: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(refs or {})
    stack = [out]
    while stack:
        cur = stack.pop()
        for k, v in list(cur.items()):
            if str(k).casefold() in _FORBIDDEN_KEYS:
                raise ValueError(f'private causal field forbidden: {k}')
            if isinstance(v, dict): stack.append(v)
            elif isinstance(v, str) and len(v.encode('utf-8')) > 4096:
                raise ValueError('causal reference string exceeds bound')
    return out

def _rows(runtime: Any) -> list[dict[str, Any]]:
    path = _ledger_path(runtime)
    if not path.exists(): return []
    rows=[]
    for n,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as exc: raise RuntimeError(f'causal ledger malformed at line {n}') from exc
    return rows

def verify(runtime: Any) -> dict[str, Any]:
    rows=_rows(runtime); prev='0'*64; session=str(runtime.runtime.get('session_id') or '')
    turns: dict[str, dict[str, Any]]={}
    for seq,row in enumerate(rows,1):
        if row.get('schema') != CAUSAL_EVENT_SCHEMA or row.get('seq') != seq: raise RuntimeError('causal ledger schema/sequence drift')
        if row.get('runtime_session_id') != session: raise RuntimeError('causal ledger session drift')
        if row.get('prev_sha256') != prev: raise RuntimeError('causal ledger predecessor drift')
        supplied=row.get('sha256'); material=dict(row); material.pop('sha256',None)
        if supplied != _sha(material): raise RuntimeError('causal ledger digest mismatch')
        event=str(row.get('event') or ''); tid=str(row.get('turn_id') or '')
        if event not in _STAGE or not tid: raise RuntimeError('causal ledger event/turn invalid')
        prior=turns.get(tid)
        if prior:
            if prior['event'] in TERMINAL: raise RuntimeError('causal event after terminal')
            if _STAGE[event] < _STAGE[prior['event']]: raise RuntimeError('causal stage regression')
            pc=prior.get('cycle_id'); cc=row.get('cycle_id')
            if pc and cc and pc != cc: raise RuntimeError('causal cycle drift')
        turns[tid]=row; prev=supplied
    active=[r for r in turns.values() if r['event'] not in TERMINAL]
    if len(active)>1: raise RuntimeError('multiple active causal turns')
    return {'schema':CAUSAL_LEDGER_SCHEMA,'ok':True,'events':len(rows),'turns':len(turns),'active_turn_id':active[0]['turn_id'] if active else None,'last_sha256':prev}

def _append(runtime: Any, event: str, turn_id: str, *, cycle_id: str | None = None, refs: dict[str, Any] | None = None) -> dict[str, Any]:
    if event not in _STAGE: raise ValueError('unknown causal event')
    verify(runtime); rows=_rows(runtime); prev=rows[-1]['sha256'] if rows else '0'*64
    row={'schema':CAUSAL_EVENT_SCHEMA,'seq':len(rows)+1,'at':_now(),'runtime_session_id':str(runtime.runtime.get('session_id') or ''),'event':event,'turn_id':str(turn_id),'cycle_id':cycle_id,'runtime_epoch_id':str((runtime.runtime.get('runtime_epoch') or {}).get('epoch_id') or '') or None,'runtime_epoch_ordinal':(runtime.runtime.get('runtime_epoch') or {}).get('ordinal'),'refs':_sanitize_refs(refs),'private_chain_of_thought':False,'epistemic_authority':0.0,'execution_authority':0.0,'prev_sha256':prev}
    row['sha256']=_sha(row); append_jsonl(_ledger_path(runtime),row); verify(runtime); return row

def active_turn(runtime: Any) -> dict[str, Any] | None:
    verify(runtime); latest: dict[str, dict[str, Any]]={}
    for row in _rows(runtime): latest[row['turn_id']]=row
    active=[r for r in latest.values() if r['event'] not in TERMINAL]
    return active[0] if active else None

def _capture_undo(runtime: Any, turn_id: str) -> dict[str, Any]:
    state=Path(runtime.state_dir); dest=_undo_root(runtime)/turn_id; files=dest/'files'; files.mkdir(parents=True,exist_ok=False)
    entries=[]; total=0
    for path in sorted(p for p in state.rglob('*') if p.is_file()):
        rel=_rel(path,state)
        if not _included(rel): continue
        size=path.stat().st_size; total += size
        if total > _MAX_UNDO_BYTES:
            shutil.rmtree(dest,ignore_errors=True); raise RuntimeError('causal undo preimage exceeds 64 MiB bound')
        target=files/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        with target.open('rb') as h: os.fsync(h.fileno())
        entries.append({'path':rel,'size':size,'sha256':_file_sha(path)})
    manifest={'schema':UNDO_SCHEMA,'turn_id':turn_id,'runtime_session_id':str(runtime.runtime.get('session_id') or ''),'entries':entries,'total_bytes':total}
    manifest['sha256']=_sha(manifest); atomic_json_write(dest/'manifest.json',manifest); fsync_parent(dest/'manifest.json'); return manifest

def _remove_undo(runtime: Any, turn_id: str) -> None:
    dest=_undo_root(runtime)/turn_id
    if dest.exists(): shutil.rmtree(dest); fsync_parent(dest)

def _restore_undo(runtime: Any, turn_id: str) -> dict[str, Any]:
    state=Path(runtime.state_dir); dest=_undo_root(runtime)/turn_id; manifest=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
    supplied=manifest.get('sha256'); material=dict(manifest); material.pop('sha256',None)
    if supplied != _sha(material) or manifest.get('runtime_session_id') != runtime.runtime.get('session_id'): raise RuntimeError('causal undo manifest integrity drift')
    before={e['path']:e for e in manifest['entries']}
    for path in sorted((p for p in state.rglob('*') if p.is_file()), reverse=True):
        rel=_rel(path,state)
        if _included(rel) and rel not in before: path.unlink(); fsync_parent(path)
    for rel,entry in before.items():
        src=dest/'files'/rel; target=state/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,target)
        with target.open('rb') as h: os.fsync(h.fileno())
        fsync_parent(target)
        if _file_sha(target) != entry['sha256']: raise RuntimeError('causal undo restore digest mismatch')
    _remove_undo(runtime,turn_id); return {'restored_files':len(before),'restored_bytes':manifest['total_bytes']}

def _legacy_surface_abort_if_needed(runtime: Any) -> None:
    current=active_turn(runtime)
    if not current: return
    marker=runtime.runtime.get('egress_guard') if isinstance(runtime.runtime.get('egress_guard'),dict) else {}
    pending=(runtime.runtime.get('cognitive') or {}).get('pending_surface_a_cycle_id')
    if not marker.get('required') and not pending and current['event'] in {'SURFACE_A_VALIDATED','VISIBLE_CHAT_BOUND'}:
        _append(runtime,'TURN_ABORTED',current['turn_id'],cycle_id=current.get('cycle_id'),refs={'reason_code':'LEGACY_NON_ACK_SURFACE','committed':False})

def begin_turn(runtime: Any) -> str:
    reconcile_restart(runtime); _legacy_surface_abort_if_needed(runtime)
    if active_turn(runtime): raise RuntimeError('active causal turn must reach terminal state before next turn')
    tid='CTR-'+secrets.token_hex(12); manifest=_capture_undo(runtime,tid)
    _append(runtime,'TURN_OPEN',tid,refs={'undo_manifest_sha256':manifest['sha256'],'undo_files':len(manifest['entries']),'undo_bytes':manifest['total_bytes']}); return tid

def _file_ref(path: str | Path | None) -> dict[str, Any] | None:
    if not path: return None
    p=Path(path)
    if not p.is_file(): return None
    return {'path':p.name,'sha256':_file_sha(p),'bytes':p.stat().st_size}

def prepare_turn(runtime: Any, turn_id: str, out: dict[str, Any]) -> dict[str, Any]:
    cycle=str((out.get('cycle') or {}).get('cycle_id') or '')
    if not cycle: raise RuntimeError('causal prepare requires cycle')
    central=out.get('central_oracle') or {}; reg=central.get('functional_psyche_regulation') or {}; workspace=out.get('workspace') or {}; projection=out.get('central_projection') or {}
    influence={'base_mode':reg.get('base_mode'),'result_mode':reg.get('result_mode'),'critique_delta':round(float(reg.get('result_critique',0))-float(reg.get('base_critique',0)),6),'unity_delta':round(float(reg.get('result_unity',0))-float(reg.get('base_unity',0)),6),'workspace_applied_count':len(workspace.get('applied',[]) or []),'interpretive_inhibition':workspace.get('interpretive_inhibition'),'assertable_count':len(projection.get('assertable_node_ids',[]) or []),'tentative_count':len(projection.get('tentative_node_ids',[]) or []),'material_action':projection.get('material_action'),'evidence_modified':False}
    refs={'intention_node_id':out.get('intention_node_id'),'cycle':_file_ref(Path(runtime.cycles_dir)/f'{cycle}.json'),'surface_b':_file_ref(out.get('surface_b_json')),'temporal_replay_sha256':((out.get('temporal_epistemics') or {}).get('replay') or {}).get('sha256'),'action_ledger_sha256':((out.get('practical_reason') or {}).get('action_ledger') or {}).get('sha256'),'plan_ledger_sha256':(((out.get('practical_reason') or {}).get('planning') or {}).get('plan_ledger') or {}).get('sha256'),'execution_ledger_sha256':((((out.get('practical_reason') or {}).get('execution_protocol') or {}).get('execution_ledger') or {}).get('sha256')),'cognitive_influence':influence,'cognitive_influence_sha256':_sha(influence)}
    row=_append(runtime,'COGNITIVE_PREPARED',turn_id,cycle_id=cycle,refs=refs); _remove_undo(runtime,turn_id); return row

def _current_for_cycle(runtime: Any, cycle_id: str) -> dict[str, Any]:
    current=active_turn(runtime)
    if not current or str(current.get('cycle_id') or '') != str(cycle_id): raise RuntimeError('active causal cycle mismatch')
    return current

def bind_user_chat(runtime: Any, cycle_id: str, row: dict[str, Any]) -> dict[str, Any]:
    current=_current_for_cycle(runtime,cycle_id); return _append(runtime,'USER_CHAT_BOUND',current['turn_id'],cycle_id=cycle_id,refs={'chat_user_seq':row.get('seq'),'chat_user_sha256':row.get('sha256'),'intention_node_id':row.get('intention_node_id')})

def bind_surface_a(runtime: Any, cycle_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
    current=_current_for_cycle(runtime,cycle_id); return _append(runtime,'SURFACE_A_VALIDATED',current['turn_id'],cycle_id=cycle_id,refs={'response_id':receipt.get('response_id'),'surface_a_validated':True,'speech_act_not_evidence':True})

def bind_visible_chat(runtime: Any, cycle_id: str, row: dict[str, Any]) -> dict[str, Any]:
    current=_current_for_cycle(runtime,cycle_id); return _append(runtime,'VISIBLE_CHAT_BOUND',current['turn_id'],cycle_id=cycle_id,refs={'chat_response_seq':row.get('seq'),'chat_response_sha256':row.get('sha256'),'response_id':row.get('response_id')})

def bind_frame(runtime: Any, prepared: dict[str, Any]) -> dict[str, Any] | None:
    receipt=dict(prepared.get('receipt') or {}); cycle=str(receipt.get('cycle_id') or '')
    if not cycle: return None
    current=active_turn(runtime)
    if not current or str(current.get('cycle_id') or '') != cycle: return None
    return _append(runtime,'FRAME_SEALED',current['turn_id'],cycle_id=cycle,refs={'frame_sha256':receipt.get('frame_sha256'),'frame_seq':receipt.get('frame_seq'),'egress_epoch':receipt.get('epoch'),'kind':receipt.get('kind')})

def _egress_ack(runtime: Any, cycle_id: str) -> dict[str, Any] | None:
    path=Path(runtime.state_dir)/'egress-events.jsonl'
    if not path.is_file(): return None
    rows=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    seals={}
    for row in rows:
        if row.get('event')=='SEAL_FRAME': seals[(row.get('epoch'),row.get('frame_seq'))]=row
        if row.get('event') in {'ACK_FRAME','ACK_RELEASE'}:
            seal=seals.get((row.get('epoch'),row.get('frame_seq')))
            if seal and str((seal.get('payload') or {}).get('cycle_id') or '')==cycle_id:
                return {'ack_event':row.get('event'),'ack_journal_sha256':row.get('sha256'),'frame_sha256':(row.get('payload') or {}).get('frame_sha256'),'sealed_kind':(seal.get('payload') or {}).get('kind'),'seal_journal_sha256':seal.get('sha256')}
    return None

def finalize_exact_ack(runtime: Any, prepared: dict[str, Any]) -> dict[str, Any] | None:
    receipt=dict(prepared.get('receipt') or {}); cycle=str(receipt.get('cycle_id') or '')
    if not cycle: return None
    current=active_turn(runtime)
    if not current or str(current.get('cycle_id') or '') != cycle: return None
    if current['event'] not in {'FRAME_SEALED'}:
        bind_frame(runtime,prepared); current=active_turn(runtime)
    ack=_egress_ack(runtime,cycle)
    if not ack: raise RuntimeError('causal terminal requires exact durable egress ACK')
    surface_seen=any(r['turn_id']==current['turn_id'] and r['event'] in {'SURFACE_A_VALIDATED','VISIBLE_CHAT_BOUND'} for r in _rows(runtime))
    recovered=str(receipt.get('kind') or '').upper()=='RECOVERY'
    event='TURN_COMMITTED' if (not recovered or surface_seen) else 'TURN_ABORTED'
    reason='RECOVERED_SURFACE_ACK' if event=='TURN_COMMITTED' and recovered else ('RECOVERY_INTERRUPTION_ACK' if event=='TURN_ABORTED' else 'EXACT_VISIBLE_ACK')
    return _append(runtime,event,current['turn_id'],cycle_id=cycle,refs={**ack,'terminal_reason':reason,'recovered_delivery':recovered,'committed':event=='TURN_COMMITTED'})

def abort_turn(runtime: Any, *, reason_code: str) -> dict[str, Any] | None:
    current=active_turn(runtime)
    if not current:return None
    if current['event']=='TURN_OPEN': restored=_restore_undo(runtime,current['turn_id'])
    else: restored={'restored_files':0,'restored_bytes':0}; _remove_undo(runtime,current['turn_id'])
    return _append(runtime,'TURN_ABORTED',current['turn_id'],cycle_id=current.get('cycle_id'),refs={'reason_code':str(reason_code),'rollback':restored,'committed':False})

def reconcile_restart(runtime: Any) -> dict[str, Any]:
    current=active_turn(runtime)
    if not current:return {'state':'CLEAN'}
    if current['event']=='TURN_OPEN':
        row=abort_turn(runtime,reason_code='PREPARE_CRASH_ROLLBACK'); return {'state':'ROLLED_BACK_PREPARE','turn_id':row['turn_id']}
    cycle=str(current.get('cycle_id') or '')
    ack=_egress_ack(runtime,cycle) if cycle else None
    if ack:
        # A recovery ACK commits only if a validated Surface A existed; otherwise it aborts.
        surface_seen=any(r['turn_id']==current['turn_id'] and r['event'] in {'SURFACE_A_VALIDATED','VISIBLE_CHAT_BOUND'} for r in _rows(runtime))
        event='TURN_COMMITTED' if surface_seen else 'TURN_ABORTED'
        row=_append(runtime,event,current['turn_id'],cycle_id=cycle,refs={**ack,'terminal_reason':'POST_ACK_RESTART_RECONCILE','recovered_delivery':ack.get('sealed_kind')=='RECOVERY','committed':event=='TURN_COMMITTED'})
        return {'state':'TERMINAL_RECONCILED','event':event,'turn_id':row['turn_id'],'cycle_id':cycle}
    return {'state':'FORWARD_RECOVERY_REQUIRED','turn_id':current['turn_id'],'cycle_id':cycle,'stage':current['event']}

def causal_projection(runtime: Any) -> dict[str, Any]:
    integrity=verify(runtime); current=active_turn(runtime); terminal=None
    for row in reversed(_rows(runtime)):
        if row['event'] in TERMINAL: terminal=row; break
    return {'schema':CAUSAL_LEDGER_SCHEMA,'integrity_ok':integrity['ok'],'event_count':integrity['events'],'active':{'turn_id':current.get('turn_id'),'cycle_id':current.get('cycle_id'),'stage':current.get('event')} if current else None,'last_terminal':{'turn_id':terminal.get('turn_id'),'cycle_id':terminal.get('cycle_id'),'event':terminal.get('event'),'sha256':terminal.get('sha256')} if terminal else None,'ledger_is_integrity_not_world_truth':True,'private_chain_of_thought_exposed':False,'epistemic_authority':0.0,'execution_authority':0.0}
