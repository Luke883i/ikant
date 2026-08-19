from __future__ import annotations
from typing import Any
from .commitments import commitment_projection,register_commitment,supersede_commitment,retract_commitment
from .temporal_memory import annotate_node,materialize_temporal_memory
from .temporal_replay import validate_temporal_replay

TEMPORAL_CORE_SCHEMA='ikant-temporal-epistemics/v0.14-test'

def assert_temporal_integrity(runtime:Any)->dict:
    replay=validate_temporal_replay(runtime)
    if not replay['ok']:raise RuntimeError('temporal replay divergence: '+'; '.join(replay['mismatches']))
    return replay

def ingest_temporal_turn(runtime:Any,intention:Any,mined:list[dict],atoms:list[dict]|None)->dict:
    annotate_node(runtime,intention.id,memory_class='episodic')
    transitions=[]
    for record,atom in zip(mined,atoms or []):
        nid=record['id'];annotate_node(runtime,nid)
        kind=str(atom.get('kind') or record.get('kind') or '')
        if kind in {'goal','constraint'}:
            transitions.append(register_commitment(runtime,nid,scope=str((atom.get('metadata') or {}).get('commitment_scope','default'))))
            meta=atom.get('metadata') or {};old=meta.get('supersedes_node_id')
            if old:transitions.append(supersede_commitment(runtime,str(old),nid,reason=str(meta.get('supersession_reason','explicit user revision'))))
            if meta.get('retract_commitment') is True:transitions.append(retract_commitment(runtime,nid,reason=str(meta.get('retraction_reason','explicit user retraction'))))
    return {'schema':TEMPORAL_CORE_SCHEMA,'transitions':transitions}

def finalize_temporal_core(runtime:Any)->dict:
    memory=materialize_temporal_memory(runtime);commitments=commitment_projection(runtime);replay=validate_temporal_replay(runtime)
    if not replay['ok']:raise RuntimeError('temporal replay divergence: '+'; '.join(replay['mismatches']))
    core={'schema':TEMPORAL_CORE_SCHEMA,'memory':memory['summary'],'commitments':commitments,'replay':{'schema':replay['schema'],'sha256':replay['sha256'],'event_count':replay['event_count'],'ok':replay['ok'],'mismatches':replay['mismatches'],'epistemic_authority':0.0},'boundaries':{'history_is_not_evidence':True,'superseded_commitments_are_not_current_directives':True,'source_revocation_preserves_independently_supported_claims':True,'replay_is_control_validation_not_world_evidence':True}}
    runtime.runtime.setdefault('temporal_memory',{})['last_core']={'schema':TEMPORAL_CORE_SCHEMA,'memory_sha256':memory['summary']['sha256'],'commitment_sha256':commitments['sha256'],'replay_sha256':replay['sha256'],'replay_ok':replay['ok']}
    if hasattr(runtime,'_write_runtime'):runtime._write_runtime()
    return core
