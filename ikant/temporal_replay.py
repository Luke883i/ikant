from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from .store import append_jsonl

TEMPORAL_REPLAY_SCHEMA='ikant-temporal-replay/v0.14-test'
TEMPORAL_EVENT_SCHEMA='ikant-temporal-event/v0.14-test'
OPS={'MEMORY_CLASSIFY','TEMPORAL_STATE','COMMITMENT_REGISTER','COMMITMENT_SUPERSEDE','COMMITMENT_RETRACT','SOURCE_REVOKE'}
ZERO='0'*64

def _canonical_hash(row:dict)->str:
    material={k:row[k] for k in ('schema','seq','op','subject','payload','prev_sha256')}
    return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def _raw_temporal_rows(runtime:Any)->list[dict]:
    rows=[];path=Path(runtime.state_dir)/'temporal-events.jsonl' if getattr(runtime,'durable',False) else None
    if path is not None and path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            try:rows.append(json.loads(line))
            except json.JSONDecodeError:raise RuntimeError('temporal journal malformed json')
    rows.extend(getattr(runtime,'_ikant_temporal_events_mem',[]) or [])
    return rows

def temporal_events(runtime:Any)->list[dict]:
    rows=_raw_temporal_rows(runtime);by={}
    for row in rows:
        seq=int(row.get('seq',0))
        if seq<1:raise RuntimeError('temporal journal invalid sequence')
        if seq in by and by[seq]!=row:raise RuntimeError('temporal journal duplicate sequence divergence')
        by[seq]=row
    ordered=[by[k] for k in sorted(by)]
    prev=ZERO
    for expected,row in enumerate(ordered,1):
        if int(row.get('seq',0))!=expected:raise RuntimeError('temporal journal non-contiguous')
        if row.get('schema')!=TEMPORAL_EVENT_SCHEMA or row.get('op') not in OPS:raise RuntimeError('temporal journal schema/op')
        if row.get('prev_sha256')!=prev:raise RuntimeError('temporal journal hash-chain predecessor')
        if row.get('sha256')!=_canonical_hash(row):raise RuntimeError('temporal journal event hash')
        prev=row['sha256']
    return ordered

def record_temporal_event(runtime:Any,op:str,subject:str,payload:dict)->int:
    if op not in OPS:raise ValueError('temporal event op')
    rows=temporal_events(runtime);seq=len(rows)+1;prev=rows[-1]['sha256'] if rows else ZERO
    row={'schema':TEMPORAL_EVENT_SCHEMA,'seq':seq,'op':op,'subject':str(subject),'payload':dict(payload),'prev_sha256':prev};row['sha256']=_canonical_hash(row)
    if getattr(runtime,'durable',False):append_jsonl(Path(runtime.state_dir)/'temporal-events.jsonl',row)
    mem=getattr(runtime,'_ikant_temporal_events_mem',None)
    if mem is None:mem=[];setattr(runtime,'_ikant_temporal_events_mem',mem)
    mem.append(row);return seq

def replay_temporal_events(events:list[dict])->dict:
    nodes={};revocations={}
    for e in events:
        op=e.get('op');subject=str(e.get('subject',''));p=e.get('payload') or {}
        if op=='MEMORY_CLASSIFY':nodes.setdefault(subject,{})['memory_class']=p.get('memory_class');nodes[subject]['temporal_state']=p.get('state','ACTIVE')
        elif op=='TEMPORAL_STATE':nodes.setdefault(subject,{})['temporal_state']=p.get('state');nodes[subject]['reason']=p.get('reason');nodes[subject]['memory_class']=p.get('memory_class') or nodes[subject].get('memory_class')
        elif op=='COMMITMENT_REGISTER':nodes.setdefault(subject,{})['commitment_status']=p.get('status','ACTIVE');nodes[subject]['commitment_id']=p.get('commitment_id');nodes[subject]['scope']=p.get('scope');nodes[subject]['memory_class']='commitment';nodes[subject].setdefault('temporal_state','ACTIVE')
        elif op=='COMMITMENT_SUPERSEDE':
            nodes.setdefault(subject,{})['commitment_status']='SUPERSEDED';nodes[subject]['temporal_state']='SUPERSEDED';new=str(p.get('new_id',''));nodes.setdefault(new,{})['commitment_status']='ACTIVE';nodes[new]['temporal_state']='ACTIVE';nodes[new]['memory_class']='commitment';nodes[new]['supersedes']=subject
        elif op=='COMMITMENT_RETRACT':nodes.setdefault(subject,{})['commitment_status']='RETRACTED';nodes[subject]['temporal_state']='RETRACTED';nodes[subject]['memory_class']='commitment'
        elif op=='SOURCE_REVOKE':
            for sid in p.get('source_ids',[]):revocations[str(sid)]={'reason':p.get('reason'),'active':True}
            states=p.get('suppressed_states') or {}
            for nid in p.get('suppressed_node_ids',[]):nodes.setdefault(str(nid),{})['temporal_state']=str(states.get(str(nid),'SOURCE_REVOKED'))
    canonical={'nodes':{k:nodes[k] for k in sorted(nodes)},'source_revocations':{k:revocations[k] for k in sorted(revocations)}}
    raw=json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()
    tail=events[-1]['sha256'] if events else ZERO
    return {'schema':TEMPORAL_REPLAY_SCHEMA,'state':canonical,'sha256':hashlib.sha256(raw).hexdigest(),'event_count':len(events),'journal_tail_sha256':tail,'deterministic':True,'epistemic_authority':0.0}

def validate_temporal_replay(runtime:Any)->dict:
    try:events=temporal_events(runtime)
    except RuntimeError as e:return {'schema':TEMPORAL_REPLAY_SCHEMA,'state':{'nodes':{},'source_revocations':{}},'sha256':None,'event_count':0,'journal_tail_sha256':None,'deterministic':False,'epistemic_authority':0.0,'ok':False,'mismatches':['journal:'+str(e)]}
    replay=replay_temporal_events(events);mismatches=[]
    for nid,row in replay['state']['nodes'].items():
        node=runtime.nodes.get(nid)
        if node is None:continue
        meta=dict(getattr(node,'metadata',{}) or {})
        for rk,mk in [('memory_class','memory_class'),('temporal_state','temporal_state'),('commitment_status','commitment_status')]:
            if row.get(rk) is not None and meta.get(mk)!=row.get(rk):mismatches.append(f'{nid}:{mk}')
    # Detect state written to the graph without a matching temporal journal commit.
    replay_nodes=replay['state']['nodes']
    for nid,node in runtime.nodes.items():
        meta=dict(getattr(node,'metadata',{}) or {});state=str(meta.get('temporal_state','ACTIVE'));commit=meta.get('commitment_status')
        if state!='ACTIVE' and (nid not in replay_nodes or replay_nodes[nid].get('temporal_state')!=state):mismatches.append(f'{nid}:unjournaled_temporal_state')
        if commit is not None and (nid not in replay_nodes or replay_nodes[nid].get('commitment_status')!=commit):mismatches.append(f'{nid}:unjournaled_commitment_status')
    stored=runtime.runtime.get('temporal_memory',{}).get('source_revocations',{})
    for sid,row in replay['state']['source_revocations'].items():
        if sid not in stored or stored[sid].get('active') is not True:mismatches.append(f'source:{sid}')
    return {**replay,'ok':not mismatches,'mismatches':mismatches}
