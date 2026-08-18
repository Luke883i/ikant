from __future__ import annotations
from pathlib import Path
from .central import converge_kant_oracle,project_surface_content
from .cognitive import apply_intention_atoms,_apply_workspace,_persist_cognitive_snapshot,_recent_events
from .crc import EpistemicHorizon,evaluate_reticulum
from .model import Layer,NodeKind,RelationKind
from .proto_self import derive_proto_self,workspace_plan
from .psyche import derive_functional_psyche,enrich_surface_a_contract,enrich_surface_b_snapshot,validate_functional_psyche
from .self_regulation import finalize_psyche,regulate_central_with_psyche
from .store import atomic_json_write
from .surfaces import build_surface_a_contract,build_surface_b_snapshot,export_surface_b_docx

def _persist_psyche(runtime,psyche):
    if not getattr(runtime,'durable',False):return None
    path=Path(runtime.state_dir)/'psyche.json';atomic_json_write(path,psyche);return str(path)

def compile_cognitive_turn(runtime,intent:str,*,limit:int=12,horizon:EpistemicHorizon|None=None,atoms:list[dict]|None=None,export_docx:bool=False,docx_path=None):
    runtime.require_active();prior=runtime.runtime.get('cognitive',{}).get('last_surface_a_response_id')
    intention=runtime.ingest(kind=NodeKind.INTENTION,layer=Layer.SIGNAL,text=intent,confidence=1,evidence=1,source_mode='user',metadata={'raw_user_intention':True,'not_factual_claim':True})
    if prior in runtime.nodes:runtime.relate(prior,intention.id,RelationKind.PRECEDES,1)
    mined=apply_intention_atoms(runtime,atoms);cycle=runtime.concentric_cycle(intent,limit=limit);cog=runtime.runtime.setdefault('cognitive',{})
    crc=evaluate_reticulum(cycle['semantic_slice'],horizon=horizon,previous_neurofunctional_state=cog.get('neurofunctional_state',{}));proto=derive_proto_self(crc,cycle,cog.get('proto_self',{}))
    psyche=derive_functional_psyche(crc,cycle,proto,previous=cog.get('psyche',{}),runtime_state=runtime.runtime)
    central=regulate_central_with_psyche(converge_kant_oracle(cycle.get('kant_oracle',{}),crc,proto),psyche);psyche=finalize_psyche(psyche,central);ok,errs=validate_functional_psyche(psyche)
    if not ok:raise RuntimeError('functional psyche validation failed: '+'; '.join(errs))
    projection=project_surface_content(cycle,crc,central);plan=workspace_plan(crc,cycle,proto,gain=getattr(runtime.params,'oracle_retroaction_gain',.06),central=central);plan['regulative_mode']=central['regulative_mode'];plan['functional_psyche_route']=central.get('functional_psyche_regulation',{});workspace=_apply_workspace(runtime,plan)
    cog['proto_self']=proto;cog['psyche']=psyche;cog['neurofunctional_state']=crc.get('neurofunctional_state',{});psyche_json=_persist_psyche(runtime,psyche)
    if psyche_json:cog['last_psyche']=psyche_json
    cog['last_crc']={'cycle_id':cycle.get('cycle_id'),'crc_basic':crc.get('roa_alignment',{}).get('crc_basic'),'collapse':crc.get('diagnostics',{}).get('mean_coefficient_of_collapse'),'rir_proxy':crc.get('diagnostics',{}).get('reticular_irreducibility_proxy'),'central_mode':central.get('regulative_mode'),'proto_self_index':proto.get('proto_self_index'),'affective_label':psyche['affective_field']['label'],'maturity_mode':psyche['epistemic_accumulation']['maturity_mode'],'psyche_digest':psyche['self_knowledge']['state_digest']};runtime._write_runtime()
    runtime._event('COGNITIVE_COMPILE',cycle.get('cycle_id'),{'crc_basic':crc.get('roa_alignment',{}).get('crc_basic'),'central_mode':central.get('regulative_mode'),'proto_self_index':proto.get('proto_self_index'),'workspace_applied':len(workspace.get('applied',[])),'mean_collapse':crc.get('diagnostics',{}).get('mean_coefficient_of_collapse'),'affective_label':psyche['affective_field']['label'],'maturity_mode':psyche['epistemic_accumulation']['maturity_mode'],'collapse_events':psyche['collapse_emergence']['summary']['collapse_event_count'],'emergence_events':psyche['collapse_emergence']['summary']['emergence_event_count']})
    out={'schema':'ikant-cognitive-turn/v0.5-test','session_id':runtime.runtime.get('session_id'),'cycle':cycle,'crc':crc,'proto_self':proto,'functional_psyche':psyche,'psyche_json':psyche_json,'central_oracle':central,'central_projection':projection,'workspace':workspace,'intention_node_id':intention.id,'mined_atoms':mined,'compression':runtime.runtime.get('compression',{}),'recent_events':_recent_events(runtime)}
    out['surface_a_contract']=enrich_surface_a_contract(build_surface_a_contract(out),psyche);snap=enrich_surface_b_snapshot(build_surface_b_snapshot(out),psyche);out['surface_b_snapshot']=snap;json_path=_persist_cognitive_snapshot(runtime,snap)
    if json_path:out['surface_b_json']=json_path;cog['last_snapshot']=json_path;runtime._write_runtime()
    if export_docx:
        docx_path=docx_path or Path(runtime.state_dir)/'artifacts'/f"CRC_SNAPSHOT_{cycle.get('cycle_id')}.docx";out['surface_b_docx']=str(export_surface_b_docx(snap,docx_path));cog['last_surface_b_docx']=out['surface_b_docx'];runtime._write_runtime();runtime._event('SURFACE_B_SNAPSHOT',cycle.get('cycle_id'),{'path':out['surface_b_docx'],'json_path':json_path})
    return out
