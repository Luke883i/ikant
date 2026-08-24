from __future__ import annotations
import json,os
from .cognitive import record_surface_a
from .interaction import build_interaction_contract, validate_interaction_surface


def _bind_engine(runtime, engine_label: str | None) -> str:
    supplied=(engine_label or os.environ.get('IKANT_HOST_ENGINE') or '').strip()
    host=runtime.runtime.setdefault('host',{})
    if host and host.get('interface_identity') not in {None,'iKant'}:
        raise RuntimeError('host interface identity binding mismatch')
    bound=str(host.get('engine_label') or '').strip()
    receipts=[]
    path=getattr(runtime,'events_path',None)
    if path is not None and path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            try:e=json.loads(line)
            except json.JSONDecodeError:continue
            if e.get('op')=='HOST_BIND':receipts.append(str(e.get('payload',{}).get('engine_label') or '').strip())
    receipts.extend(str(e.get('payload',{}).get('engine_label') or '').strip() for e in getattr(runtime,'events_mem',[]) if e.get('op')=='HOST_BIND')
    receipts=[x for x in receipts if x]
    if receipts and (len(set(receipts))!=1 or (bound and receipts[0]!=bound)):
        raise RuntimeError('host engine binding receipt mismatch')
    if not bound and receipts:bound=receipts[0];host.update({'interface_identity':'iKant','engine_label':bound,'identity_order':'interface_then_engine','accepted_hierarchy_required':True})
    if not bound and not supplied:
        raise PermissionError('host engine disclosure required for conforming iKant mode')
    if bound and supplied and bound!=supplied:
        raise PermissionError('host engine binding mismatch')
    if not bound:
        host.update({'interface_identity':'iKant','engine_label':supplied,'identity_order':'interface_then_engine','accepted_hierarchy_required':True})
        runtime._write_runtime();runtime._event('HOST_BIND',runtime.runtime.get('session_id'),{'interface_identity':'iKant','engine_label':supplied})
        bound=supplied
    return bound


def conforming_turn(runtime, intent: str, *, engine_label: str | None = None, limit: int = 12, horizon=None, atoms=None, docx_path=None) -> dict:
    from .runtime_host import conforming_turn as _canonical_conforming_turn
    return _canonical_conforming_turn(runtime,intent,engine_label=engine_label,limit=limit,horizon=horizon,atoms=atoms,docx_path=docx_path)


def emit_conforming_surface_a(runtime, cycle_id: str, text: str, *, intention_node_id: str | None = None) -> dict:
    runtime.require_active();cognitive=runtime.runtime.setdefault('cognitive',{})
    pending=cognitive.get('pending_surface_a_cycle_id')
    if pending!=cycle_id: raise PermissionError('Surface A cycle is not the single pending conforming turn')
    contract=cognitive.get('pending_interaction_contract')
    if not contract: raise PermissionError('missing interaction contract for pending turn')
    ok,errors=validate_interaction_surface(text,contract)
    if not ok: raise ValueError('Interaction Surface A validation failed: '+'; '.join(errors))
    rec=record_surface_a(runtime,cycle_id,text,intention_node_id=intention_node_id)
    from .causal_ledger import bind_surface_a
    bind_surface_a(runtime,cycle_id,rec)
    cognitive.pop('pending_surface_a_cycle_id',None);cognitive.pop('pending_interaction_contract',None);runtime._write_runtime();runtime._event('INTERACTION_CLOSE',cycle_id,{'response_id':rec['response_id'],'interaction_validated':True})
    rec['interaction_validated']=True;rec['interaction_contract_schema']=contract['schema']
    return rec
