from __future__ import annotations
import os
from .cognitive import compile_cognitive_turn, record_surface_a
from .interaction import build_interaction_contract, validate_interaction_surface


def _bind_engine(runtime, engine_label: str | None) -> str:
    supplied=(engine_label or os.environ.get('IKANT_HOST_ENGINE') or '').strip()
    host=runtime.runtime.setdefault('host',{})
    bound=str(host.get('engine_label') or '').strip()
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
    runtime.require_active();engine=_bind_engine(runtime,engine_label)
    cognitive=runtime.runtime.setdefault('cognitive',{})
    pending=cognitive.get('pending_surface_a_cycle_id')
    if pending:
        raise RuntimeError(f'pending Surface A emission must close before next conforming turn: {pending}')
    out=compile_cognitive_turn(runtime,intent,limit=limit,horizon=horizon,atoms=atoms,export_docx=True,docx_path=docx_path)
    contract=build_interaction_contract(intent,engine_label=engine)
    out['interaction_contract']=contract
    out['surface_b_snapshot'].setdefault('dynamic_state',{})['interaction_contract']=contract
    out['surface_b_snapshot']['dynamic_state']['host_binding']=dict(runtime.runtime.get('host',{}))
    if out.get('surface_b_json'):
        from pathlib import Path
        from .store import atomic_json_write
        atomic_json_write(Path(out['surface_b_json']),out['surface_b_snapshot'])
        if out.get('surface_b_docx'):
            from .surfaces import export_surface_b_docx
            export_surface_b_docx(out['surface_b_snapshot'],out['surface_b_docx'])
    cognitive['pending_surface_a_cycle_id']=out['cycle']['cycle_id']
    cognitive['pending_interaction_contract']=contract
    runtime._write_runtime();runtime._event('INTERACTION_CONTRACT',out['cycle']['cycle_id'],{'profile':contract['profile']['kind'],'engine_label':engine})
    return out


def emit_conforming_surface_a(runtime, cycle_id: str, text: str, *, intention_node_id: str | None = None) -> dict:
    runtime.require_active();cognitive=runtime.runtime.setdefault('cognitive',{})
    pending=cognitive.get('pending_surface_a_cycle_id')
    if pending!=cycle_id:
        raise PermissionError('Surface A cycle is not the single pending conforming turn')
    contract=cognitive.get('pending_interaction_contract')
    if not contract:
        raise PermissionError('missing interaction contract for pending turn')
    ok,errors=validate_interaction_surface(text,contract)
    if not ok:
        raise ValueError('Interaction Surface A validation failed: '+'; '.join(errors))
    rec=record_surface_a(runtime,cycle_id,text,intention_node_id=intention_node_id)
    cognitive.pop('pending_surface_a_cycle_id',None);cognitive.pop('pending_interaction_contract',None);runtime._write_runtime();runtime._event('INTERACTION_CLOSE',cycle_id,{'response_id':rec['response_id'],'interaction_validated':True})
    rec['interaction_validated']=True;rec['interaction_contract_schema']=contract['schema']
    return rec
