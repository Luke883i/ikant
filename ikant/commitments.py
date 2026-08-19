from __future__ import annotations
import hashlib, json
from typing import Any
from .temporal_memory import annotate_node,set_temporal_state,temporal_available
from .temporal_replay import record_temporal_event

COMMITMENT_SCHEMA='ikant-commitment-graph/v0.14-test'

def _kind(node):return str(getattr(getattr(node,'kind',None),'value',getattr(node,'kind','')))

def register_commitment(runtime:Any,node_id:str,*,scope:str='default',actor:str='user')->dict:
    node=runtime.nodes[node_id]
    if _kind(node) not in {'goal','constraint'}:raise ValueError('commitment requires goal or constraint')
    before=float(node.evidence);annotate_node(runtime,node_id,memory_class='commitment',emit=False);meta=node.metadata
    meta.setdefault('commitment_id','COM-'+hashlib.sha256(f'{scope}|{node_id}'.encode()).hexdigest()[:20]);meta['commitment_scope']=str(scope);meta.setdefault('commitment_status','ACTIVE');meta.setdefault('commitment_actor',str(actor))
    if hasattr(runtime,'_save'):runtime._save(node)
    if hasattr(runtime,'_persist'):runtime._persist()
    record_temporal_event(runtime,'COMMITMENT_REGISTER',node_id,{'commitment_id':meta['commitment_id'],'scope':scope,'status':meta['commitment_status'],'actor':actor,'evidence_modified':False})
    if float(node.evidence)!=before:raise RuntimeError('commitment registration modified evidence')
    return {'schema':COMMITMENT_SCHEMA,'node_id':node_id,'commitment_id':meta['commitment_id'],'scope':scope,'status':meta['commitment_status'],'authority':'DIRECTIVE_LIFECYCLE_ONLY','evidence_modified':False}

def supersede_commitment(runtime:Any,old_id:str,new_id:str,*,reason:str,actor:str='user')->dict:
    if old_id==new_id:raise ValueError('commitment cannot supersede itself')
    old,new=runtime.nodes[old_id],runtime.nodes[new_id]
    if _kind(old) not in {'goal','constraint'} or _kind(new) not in {'goal','constraint'}:raise ValueError('commitment endpoint')
    existing=str((getattr(old,'metadata',{}) or {}).get('commitment_status','ACTIVE'))
    if existing!='ACTIVE':raise ValueError('only active commitment can be superseded')
    if not getattr(new,'active',True):raise ValueError('successor commitment must be active')
    if str((getattr(new,'metadata',{}) or {}).get('commitment_status','ACTIVE'))!='ACTIVE':raise ValueError('successor commitment must be current')
    register_commitment(runtime,old_id,actor=actor)
    if old.metadata.get('commitment_status')!='ACTIVE':raise ValueError('only active commitment can be superseded')
    register_commitment(runtime,new_id,scope=str(old.metadata.get('commitment_scope','default')),actor=actor)
    before=(float(old.evidence),float(new.evidence));old.metadata['commitment_status']='SUPERSEDED';old.metadata['superseded_by']=new_id;new.metadata['commitment_status']='ACTIVE';new.metadata['supersedes']=old_id
    set_temporal_state(runtime,old_id,'SUPERSEDED',reason=reason,emit=False);set_temporal_state(runtime,new_id,'ACTIVE',reason='successor:'+reason,emit=False)
    if hasattr(runtime,'_save'):runtime._save(old);runtime._save(new)
    if hasattr(runtime,'_persist'):runtime._persist()
    record_temporal_event(runtime,'COMMITMENT_SUPERSEDE',old_id,{'new_id':new_id,'reason':reason,'actor':actor,'old_status':'SUPERSEDED','new_status':'ACTIVE','evidence_modified':False})
    if (float(old.evidence),float(new.evidence))!=before:raise RuntimeError('commitment supersession modified evidence')
    return {'schema':COMMITMENT_SCHEMA,'old_id':old_id,'new_id':new_id,'status':'SUPERSEDED','successor_status':'ACTIVE','evidence_modified':False}

def retract_commitment(runtime:Any,node_id:str,*,reason:str,actor:str='user')->dict:
    node=runtime.nodes[node_id]
    existing=str((getattr(node,'metadata',{}) or {}).get('commitment_status','ACTIVE'))
    if existing!='ACTIVE':raise ValueError('only active commitment can be retracted')
    register_commitment(runtime,node_id,actor=actor)
    if node.metadata.get('commitment_status')!='ACTIVE':raise ValueError('only active commitment can be retracted')
    node.metadata['commitment_status']='RETRACTED';set_temporal_state(runtime,node_id,'RETRACTED',reason=reason,emit=False)
    if hasattr(runtime,'_save'):runtime._save(node)
    if hasattr(runtime,'_persist'):runtime._persist()
    record_temporal_event(runtime,'COMMITMENT_RETRACT',node_id,{'reason':reason,'actor':actor,'status':'RETRACTED','evidence_modified':False})
    return {'schema':COMMITMENT_SCHEMA,'node_id':node_id,'status':'RETRACTED','evidence_modified':False}

def commitment_projection(runtime:Any)->dict:
    rows=[]
    for nid,node in sorted(runtime.nodes.items()):
        if _kind(node) not in {'goal','constraint'}:continue
        meta=dict(getattr(node,'metadata',{}) or {});rows.append({'node_id':nid,'commitment_id':meta.get('commitment_id'),'scope':meta.get('commitment_scope','default'),'status':meta.get('commitment_status','UNREGISTERED'),'supersedes':meta.get('supersedes'),'superseded_by':meta.get('superseded_by'),'available':temporal_available(node)})
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return {'schema':COMMITMENT_SCHEMA,'sha256':hashlib.sha256(raw).hexdigest(),'commitments':rows,'active_node_ids':[x['node_id'] for x in rows if x['status']=='ACTIVE' and x['available']],'epistemic_authority':0.0}
