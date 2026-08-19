from __future__ import annotations
from pathlib import Path
from .central import converge_kant_oracle,project_surface_content
from .cognitive import apply_intention_atoms,_apply_workspace,_persist_cognitive_snapshot,_recent_events
from .crc import EpistemicHorizon,evaluate_reticulum
from .epistemic_core import prepare_epistemic_core,calibrate_cycle,finalize_epistemic_core
from .model import Layer,NodeKind,RelationKind
from .practical_reason import finalize_practical_reason
from .provenance import bind_node_source
from .proto_self import derive_proto_self,workspace_plan
from .psyche import derive_functional_psyche,enrich_surface_a_contract,enrich_surface_b_snapshot,validate_functional_psyche
from .self_regulation import finalize_psyche,regulate_central_with_psyche
from .store import atomic_json_write
from .surfaces import build_surface_a_contract,build_surface_b_snapshot,export_surface_b_docx
from .temporal_core import assert_temporal_integrity,ingest_temporal_turn,finalize_temporal_core

def _persist_psyche(runtime,psyche):
    if not getattr(runtime,'durable',False): return None
    path=Path(runtime.state_dir)/'psyche.json'; atomic_json_write(path,psyche); return str(path)

def _bind_turn_provenance(runtime,intention,mined,atoms):
    bind_node_source(runtime,intention.id,source_mode='user',provenance_key='user:current-session',acquisition='human_intention',independent=False)
    for idx,(record,atom) in enumerate(zip(mined,atoms or [])):
        metadata=dict(atom.get('metadata') or {}); source=str(atom.get('source_mode') or record.get('source_mode') or 'runtime_derived')
        key=metadata.get('provenance_key') or metadata.get('source_id') or metadata.get('url') or metadata.get('path') or f'{source}:current-session'
        locator=metadata.get('url') or metadata.get('path') or metadata.get('source_locator')
        bind_node_source(runtime,record['id'],source_mode=source,provenance_key=str(key),locator=str(locator) if locator else None,acquisition='intention_atom',independent=source not in {'user','runtime_derived','inference','cache','demo'})

def _action_projection(practical):
    out=[]
    for row in (practical.get('action_ledger') or {}).get('candidates',[])[:8]:
        decision=row.get('decision') or {}; authority=decision.get('authority') or {}
        out.append({'node_id':row.get('node_id'),'text':row.get('text'),'status':decision.get('status'),'execution_eligible':bool(decision.get('execution_eligible')),'human_execution_required':bool(decision.get('human_execution_required')),'required_capabilities':row.get('required_capabilities',[]),'missing_capabilities':authority.get('missing_capabilities',[]),'reversibility':row.get('reversibility'),'impact_level':row.get('impact_level'),'approval_valid':bool(decision.get('approval_valid'))})
    return out

def compile_cognitive_turn(runtime,intent:str,*,limit:int=12,horizon:EpistemicHorizon|None=None,atoms:list[dict]|None=None,export_docx:bool=False,docx_path=None):
    runtime.require_active(); assert_temporal_integrity(runtime); prior=runtime.runtime.get('cognitive',{}).get('last_surface_a_response_id')
    intention=runtime.ingest(kind=NodeKind.INTENTION,layer=Layer.SIGNAL,text=intent,confidence=1,evidence=1,source_mode='user',metadata={'raw_user_intention':True,'not_factual_claim':True})
    if prior in runtime.nodes: runtime.relate(prior,intention.id,RelationKind.PRECEDES,1)
    mined=apply_intention_atoms(runtime,atoms); _bind_turn_provenance(runtime,intention,mined,atoms)
    temporal_pre=ingest_temporal_turn(runtime,intention,mined,atoms)
    prepared_core=prepare_epistemic_core(runtime,intent,limit=limit); cycle=runtime.concentric_cycle(intent,limit=limit); calibration=calibrate_cycle(runtime,cycle); cog=runtime.runtime.setdefault('cognitive',{}); previous_neuro=cog.get('neurofunctional_state',{})
    crc=evaluate_reticulum(cycle['semantic_slice'],horizon=horizon,previous_neurofunctional_state=previous_neuro); epistemic_core=finalize_epistemic_core(runtime,cycle,crc,horizon=horizon,previous_neurofunctional_state=previous_neuro,prepared=prepared_core,calibration=calibration)
    temporal_core=finalize_temporal_core(runtime)
    proto=derive_proto_self(crc,cycle,cog.get('proto_self',{})); psyche=derive_functional_psyche(crc,cycle,proto,previous=cog.get('psyche',{}),runtime_state=runtime.runtime)
    central=regulate_central_with_psyche(converge_kant_oracle(cycle.get('kant_oracle',{}),crc,proto),psyche); psyche=finalize_psyche(psyche,central); ok,errs=validate_functional_psyche(psyche)
    if not ok: raise RuntimeError('functional psyche validation failed: '+'; '.join(errs))
    practical=finalize_practical_reason(runtime,cycle,temporal_core=temporal_core,central=central,mined=mined,atoms=atoms,intention_node_id=intention.id)
    projection=project_surface_content(cycle,crc,central); projection['material_action']=practical.get('material_action',projection.get('material_action')); projection['action_governance']=_action_projection(practical)
    plan=workspace_plan(crc,cycle,proto,gain=getattr(runtime.params,'oracle_retroaction_gain',.06),central=central); plan['regulative_mode']=central['regulative_mode']; plan['functional_psyche_route']=central.get('functional_psyche_regulation',{}); workspace=_apply_workspace(runtime,plan)
    cog['proto_self']=proto; cog['psyche']=psyche; cog['neurofunctional_state']=crc.get('neurofunctional_state',{}); psyche_json=_persist_psyche(runtime,psyche)
    if psyche_json: cog['last_psyche']=psyche_json
    causal=epistemic_core.get('causal_crc',{}); replay=temporal_core.get('replay',{}); ledger=practical.get('action_ledger',{}); cog['last_crc']={'cycle_id':cycle.get('cycle_id'),'crc_basic':crc.get('roa_alignment',{}).get('crc_basic'),'collapse':crc.get('diagnostics',{}).get('mean_coefficient_of_collapse'),'rir_proxy':crc.get('diagnostics',{}).get('reticular_irreducibility_proxy'),'causal_dependency':causal.get('max_counterfactual_dependency'),'single_point_dependency':causal.get('single_point_dependency'),'calibration_risk':calibration.get('risk_adjustment'),'temporal_replay_sha256':replay.get('sha256'),'action_ledger_sha256':ledger.get('sha256'),'material_action':practical.get('material_action'),'central_mode':central.get('regulative_mode'),'proto_self_index':proto.get('proto_self_index'),'affective_label':psyche['affective_field']['label'],'maturity_mode':psyche['epistemic_accumulation']['maturity_mode'],'psyche_digest':psyche['self_knowledge']['state_digest']}; runtime._write_runtime()
    runtime._event('COGNITIVE_COMPILE',cycle.get('cycle_id'),{'crc_basic':crc.get('roa_alignment',{}).get('crc_basic'),'central_mode':central.get('regulative_mode'),'proto_self_index':proto.get('proto_self_index'),'workspace_applied':len(workspace.get('applied',[])),'mean_collapse':crc.get('diagnostics',{}).get('mean_coefficient_of_collapse'),'calibration_risk':calibration.get('risk_adjustment'),'max_counterfactual_dependency':causal.get('max_counterfactual_dependency'),'single_point_dependency':causal.get('single_point_dependency'),'provenance_sha256':epistemic_core.get('provenance',{}).get('sha256'),'temporal_memory_sha256':temporal_core.get('memory',{}).get('sha256'),'temporal_replay_sha256':replay.get('sha256'),'action_ledger_sha256':ledger.get('sha256'),'host_execution_eligible_count':ledger.get('host_execution_eligible_count',0),'material_action':practical.get('material_action'),'affective_label':psyche['affective_field']['label'],'maturity_mode':psyche['epistemic_accumulation']['maturity_mode'],'collapse_events':psyche['collapse_emergence']['summary']['collapse_event_count'],'emergence_events':psyche['collapse_emergence']['summary']['emergence_event_count']})
    out={'schema':'ikant-cognitive-turn/v0.15-test','session_id':runtime.runtime.get('session_id'),'cycle':cycle,'crc':crc,'epistemic_core':epistemic_core,'temporal_epistemics':temporal_core,'temporal_transitions':temporal_pre,'practical_reason':practical,'proto_self':proto,'functional_psyche':psyche,'psyche_json':psyche_json,'central_oracle':central,'central_projection':projection,'workspace':workspace,'intention_node_id':intention.id,'mined_atoms':mined,'compression':runtime.runtime.get('compression',{}),'recent_events':_recent_events(runtime)}
    out['surface_a_contract']=enrich_surface_a_contract(build_surface_a_contract(out),psyche); snap=enrich_surface_b_snapshot(build_surface_b_snapshot(out),psyche); snap.setdefault('dynamic_state',{})['epistemic_core']=epistemic_core; snap['dynamic_state']['temporal_epistemics']=temporal_core; snap['dynamic_state']['practical_reason']=practical; out['surface_b_snapshot']=snap; json_path=_persist_cognitive_snapshot(runtime,snap)
    if json_path: out['surface_b_json']=json_path; cog['last_snapshot']=json_path; runtime._write_runtime()
    if export_docx:
        docx_path=docx_path or Path(runtime.state_dir)/'artifacts'/f"CRC_SNAPSHOT_{cycle.get('cycle_id')}.docx"; out['surface_b_docx']=str(export_surface_b_docx(snap,docx_path)); cog['last_surface_b_docx']=out['surface_b_docx']; runtime._write_runtime(); runtime._event('SURFACE_B_SNAPSHOT',cycle.get('cycle_id'),{'path':out['surface_b_docx'],'json_path':json_path})
    return out
