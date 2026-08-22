from __future__ import annotations
from pathlib import Path
import threading
from .cognitive_runtime import compile_cognitive_turn
from .host import _bind_engine,emit_conforming_surface_a as _emit_conforming_surface_a
from .interaction import build_interaction_contract
from .store import atomic_json_write

_EGRESS_LOCK_CREATION=threading.Lock()
def runtime_egress_lock(runtime):
    with _EGRESS_LOCK_CREATION:
        lock=getattr(runtime,'_incarnate_egress_lock',None)
        if lock is None: lock=threading.RLock(); setattr(runtime,'_incarnate_egress_lock',lock)
        return lock

def conforming_turn(runtime,intent:str,*,engine_label=None,limit=12,horizon=None,atoms=None,docx_path=None,timing_origin=None):
    with runtime_egress_lock(runtime):
        runtime.require_active(); engine=_bind_engine(runtime,engine_label); cog=runtime.runtime.setdefault('cognitive',{}); pending=cog.get('pending_surface_a_cycle_id')
        if pending: raise RuntimeError(f'pending Surface A emission must close before next conforming turn: {pending}')
        out=compile_cognitive_turn(runtime,intent,limit=limit,horizon=horizon,atoms=atoms,export_docx=False,docx_path=docx_path,timing_origin=timing_origin); contract=build_interaction_contract(intent,engine_label=engine); out['interaction_contract']=contract; snap=out['surface_b_snapshot']; snap.setdefault('dynamic_state',{})['interaction_contract']=contract; snap['dynamic_state']['host_binding']=dict(runtime.runtime.get('host',{}))
        if out.get('surface_b_json'): atomic_json_write(Path(out['surface_b_json']),snap)
        cog['pending_surface_a_cycle_id']=out['cycle']['cycle_id']; cog['pending_interaction_contract']=contract; runtime._write_runtime(); runtime._event('INTERACTION_CONTRACT',out['cycle']['cycle_id'],{'profile':contract['profile']['kind'],'engine_label':engine}); return out

def emit_incarnate_surface_a(runtime,cycle_id:str,text:str,*,intention_node_id=None):
    with runtime_egress_lock(runtime): return _emit_conforming_surface_a(runtime,cycle_id,text,intention_node_id=intention_node_id)
