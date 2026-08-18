from __future__ import annotations
from pathlib import Path
from .cognitive_v05 import compile_cognitive_turn
from .host import _bind_engine,emit_conforming_surface_a
from .interaction import build_interaction_contract
from .store import atomic_json_write
from .surfaces import export_surface_b_docx

def conforming_turn(runtime,intent:str,*,engine_label=None,limit=12,horizon=None,atoms=None,docx_path=None):
 runtime.require_active();engine=_bind_engine(runtime,engine_label);cog=runtime.runtime.setdefault('cognitive',{});pending=cog.get('pending_surface_a_cycle_id')
 if pending:raise RuntimeError(f'pending Surface A emission must close before next conforming turn: {pending}')
 out=compile_cognitive_turn(runtime,intent,limit=limit,horizon=horizon,atoms=atoms,export_docx=True,docx_path=docx_path);contract=build_interaction_contract(intent,engine_label=engine);out['interaction_contract']=contract;snap=out['surface_b_snapshot'];snap.setdefault('dynamic_state',{})['interaction_contract']=contract;snap['dynamic_state']['host_binding']=dict(runtime.runtime.get('host',{}))
 if out.get('surface_b_json'):
  atomic_json_write(Path(out['surface_b_json']),snap)
  if out.get('surface_b_docx'):export_surface_b_docx(snap,out['surface_b_docx'])
 cog['pending_surface_a_cycle_id']=out['cycle']['cycle_id'];cog['pending_interaction_contract']=contract;runtime._write_runtime();runtime._event('INTERACTION_CONTRACT',out['cycle']['cycle_id'],{'profile':contract['profile']['kind'],'engine_label':engine});return out
