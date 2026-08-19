from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json
from pathlib import Path
from typing import Any
from .model import NodeKind
from .store import atomic_json_write
from .temporal_replay import record_temporal_event

TEMPORAL_MEMORY_SCHEMA = 'ikant-temporal-memory/v0.14-test'
MEMORY_CLASSES = {'episodic','semantic','commitment','interpretive','kernel'}
TEMPORAL_STATES = {'ACTIVE','SUPERSEDED','RETRACTED','FORGOTTEN','SOURCE_REVOKED','DEPENDENCY_INVALIDATED'}
UNAVAILABLE_STATES = TEMPORAL_STATES - {'ACTIVE'}

@dataclass(frozen=True)
class TemporalRecord:
    node_id:str
    memory_class:str
    state:str
    updated_seq:int
    reason:str|None=None
    authority:str='AVAILABILITY_ONLY'
    evidence_modified:bool=False

def classify_node(node:Any)->str:
    explicit=str((getattr(node,'metadata',{}) or {}).get('memory_class',''))
    if explicit in MEMORY_CLASSES:return explicit
    kind=getattr(getattr(node,'kind',None),'value',getattr(node,'kind',''))
    mode=str(getattr(node,'source_mode','runtime_derived'))
    if kind in {'goal','constraint'}:return 'commitment'
    if kind=='principle':return 'kernel'
    if mode in {'runtime_derived','inference','cache','demo'} or kind in {'hypothesis','self_model','summary','pattern'}:return 'interpretive'
    if kind in {'intention','response','observation','action'}:return 'episodic'
    return 'semantic'

def temporal_state(node:Any)->str:
    state=str((getattr(node,'metadata',{}) or {}).get('temporal_state','ACTIVE'))
    return state if state in TEMPORAL_STATES else 'ACTIVE'

def temporal_available(node:Any)->bool:
    return bool(getattr(node,'active',True)) and temporal_state(node)=='ACTIVE' and str((getattr(node,'metadata',{}) or {}).get('commitment_status','ACTIVE')) not in {'SUPERSEDED','RETRACTED'}

def temporal_vigency(node:Any)->float:
    return 1.0 if temporal_available(node) else 0.0

def _persist_graph(runtime:Any)->None:
    if hasattr(runtime,'_persist'):runtime._persist()

def annotate_node(runtime:Any,node_id:str,*,memory_class:str|None=None,emit:bool=True)->TemporalRecord:
    node=runtime.nodes[node_id]; before=float(getattr(node,'evidence',0.0)); cls=memory_class or classify_node(node)
    if cls not in MEMORY_CLASSES:raise ValueError('memory class')
    node.metadata=dict(getattr(node,'metadata',{}) or {}); node.metadata['memory_class']=cls; node.metadata.setdefault('temporal_state','ACTIVE')
    if hasattr(runtime,'_save'):runtime._save(node)
    _persist_graph(runtime)
    seq=int(getattr(runtime,'graph',{}).get('seq',0))
    if emit:seq=record_temporal_event(runtime,'MEMORY_CLASSIFY',node_id,{'memory_class':cls,'state':node.metadata['temporal_state'],'evidence_modified':False})
    if float(getattr(node,'evidence',0.0))!=before:raise RuntimeError('memory classification modified evidence')
    return TemporalRecord(node_id,cls,node.metadata['temporal_state'],seq)

def set_temporal_state(runtime:Any,node_id:str,state:str,*,reason:str,emit:bool=True)->TemporalRecord:
    if state not in TEMPORAL_STATES:raise ValueError('temporal state')
    node=runtime.nodes[node_id]; before=float(getattr(node,'evidence',0.0)); annotate_node(runtime,node_id,emit=False)
    node.metadata['temporal_state']=state; node.metadata['temporal_reason']=str(reason)
    if state == 'ACTIVE':
        if not getattr(node,'active',True) and not node.metadata.get('temporal_managed_inactive'):
            raise ValueError('temporal state cannot reactivate a non-temporal inactive node')
        node.active=True; node.metadata.pop('temporal_managed_inactive',None)
    else:
        node.metadata['temporal_managed_inactive']=True; node.active=False
        if hasattr(node,'activation'): node.activation = 0.0
    if hasattr(runtime,'_save'):runtime._save(node)
    _persist_graph(runtime)
    seq=int(getattr(runtime,'graph',{}).get('seq',0))
    if emit:seq=record_temporal_event(runtime,'TEMPORAL_STATE',node_id,{'state':state,'reason':str(reason),'memory_class':node.metadata['memory_class'],'evidence_modified':False})
    if float(getattr(node,'evidence',0.0))!=before:raise RuntimeError('temporal transition modified evidence')
    return TemporalRecord(node_id,node.metadata['memory_class'],state,seq,str(reason))

def forget_memory(runtime:Any,node_id:str,*,reason:str)->TemporalRecord:
    return set_temporal_state(runtime,node_id,'FORGOTTEN',reason=reason)

def materialize_temporal_memory(runtime:Any)->dict[str,Any]:
    records={}
    for nid,node in sorted(runtime.nodes.items()):
        cls=classify_node(node); state=temporal_state(node); records[nid]={'node_id':nid,'memory_class':cls,'state':state,'available':temporal_available(node),'commitment_status':str((getattr(node,'metadata',{}) or {}).get('commitment_status','')) or None}
    raw=json.dumps(records,sort_keys=True,separators=(',',':')).encode(); digest=hashlib.sha256(raw).hexdigest()
    summary={'schema':TEMPORAL_MEMORY_SCHEMA,'sha256':digest,'node_count':len(records),'available_count':sum(x['available'] for x in records.values()),'by_class':{c:sum(x['memory_class']==c for x in records.values()) for c in sorted(MEMORY_CLASSES)},'authority':'AVAILABILITY_ONLY','epistemic_authority':0.0,'evidence_modified':False}
    runtime.runtime.setdefault('temporal_memory',{})['last_summary']=summary
    if getattr(runtime,'durable',False):
        path=Path(runtime.state_dir)/'temporal-memory.json'; payload={'schema':TEMPORAL_MEMORY_SCHEMA,'records':records,'summary':summary}
        atomic_json_write(path,payload); summary['path']=str(path)
    if hasattr(runtime,'_write_runtime'):runtime._write_runtime()
    return {'records':records,'summary':summary}
