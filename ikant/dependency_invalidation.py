from __future__ import annotations
from typing import Any
from .temporal_memory import set_temporal_state,temporal_available
from .temporal_replay import record_temporal_event

INVALIDATION_SCHEMA='ikant-dependency-invalidation/v0.14-test'
DERIVATION_KINDS={'supports','abstracts','associates','retroacts','activates'}

def _source_state(runtime:Any)->dict:
    state=runtime.runtime.setdefault('temporal_memory',{}).setdefault('source_revocations',{})
    if not state:
        from .temporal_replay import temporal_events,replay_temporal_events
        rebuilt=replay_temporal_events(temporal_events(runtime))['state']['source_revocations'];state.update(rebuilt)
    return state

def _unrevoked_external(graph:dict,claim:dict,revoked:set[str])->list[str]:
    # Independence belongs to observations, not source labels. A second source id is
    # not corroboration unless at least one bound observation explicitly says so.
    observations=graph.get('observations',{}) or {};sources=graph.get('sources',{}) or {};out=set()
    for oid in claim.get('observation_ids',[]):
        obs=observations.get(oid,{})
        sid=str(obs.get('source_id',''))
        src=sources.get(sid,{})
        if obs.get('independent') is True and src.get('external') is True and sid not in revoked:out.add(sid)
    return sorted(out)

def invalidate_source(runtime:Any,source_key:str,*,reason:str,provenance_graph:dict|None=None)->dict:
    if provenance_graph is None:
        from .provenance import materialize_provenance
        provenance_graph=materialize_provenance(runtime)['graph']
    before={nid:float(n.evidence) for nid,n in runtime.nodes.items()};sources=provenance_graph.get('sources',{})
    matched={sid for sid,s in sources.items() if sid==source_key or str(s.get('provenance_key'))==str(source_key)}
    if not matched:raise KeyError(source_key)
    rev=_source_state(runtime)
    for sid in matched:rev[sid]={'reason':str(reason),'active':True}
    revoked={sid for sid,row in rev.items() if row.get('active') is True};direct=[];preserved=[]
    for nid,claim in provenance_graph.get('claims',{}).items():
        if not matched.intersection(claim.get('source_ids',[])):continue
        node=runtime.nodes.get(nid)
        if node is None:continue
        remaining=_unrevoked_external(provenance_graph,claim,revoked)
        node.metadata=dict(getattr(node,'metadata',{}) or {});node.metadata['revoked_source_ids']=sorted(matched.intersection(claim.get('source_ids',[])))
        if remaining:
            node.metadata['source_revocation_partial']=True;preserved.append(nid)
            if hasattr(runtime,'_save'):runtime._save(node)
            if hasattr(runtime,'_persist'):runtime._persist()
        else:
            set_temporal_state(runtime,nid,'SOURCE_REVOKED',reason=reason,emit=False);direct.append(nid)
    affected=set(direct);state_by={nid:'SOURCE_REVOKED' for nid in direct};front=list(direct)
    rels=list(getattr(runtime,'relations',{}).values())
    while front:
        src=front.pop(0)
        for r in rels:
            kind=str(getattr(getattr(r,'kind',None),'value',getattr(r,'kind','')))
            if not getattr(r,'active',True) or str(getattr(r,'source',''))!=src or kind not in DERIVATION_KINDS:continue
            tid=str(getattr(r,'target',''));target=runtime.nodes.get(tid)
            if target is None or tid in affected or str(getattr(target,'source_mode','')) not in {'runtime_derived','inference','cache','demo'}:continue
            set_temporal_state(runtime,tid,'DEPENDENCY_INVALIDATED',reason=f'depends_on:{src}',emit=False);affected.add(tid);state_by[tid]='DEPENDENCY_INVALIDATED';front.append(tid)
    record_temporal_event(runtime,'SOURCE_REVOKE',str(source_key),{'source_ids':sorted(matched),'reason':reason,'suppressed_node_ids':sorted(affected),'suppressed_states':{k:state_by[k] for k in sorted(state_by)},'preserved_node_ids':sorted(preserved),'evidence_modified':False})
    if hasattr(runtime,'_write_runtime'):runtime._write_runtime()
    after={nid:float(n.evidence) for nid,n in runtime.nodes.items()}
    if before!=after:raise RuntimeError('dependency invalidation modified evidence')
    return {'schema':INVALIDATION_SCHEMA,'source_ids':sorted(matched),'suppressed_node_ids':sorted(affected),'preserved_node_ids':sorted(preserved),'evidence_modified':False,'authority':'AVAILABILITY_ONLY'}
