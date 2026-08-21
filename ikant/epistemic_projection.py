from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any

EPISTEMIC_WORKSPACE_SCHEMA='ikant-epistemic-workspace/v0.28-test'
EPISTEMIC_INDEX_SCHEMA='ikant-epistemic-index/v0.28-test'
EPISTEMIC_ARTIFACT_SCHEMA='ikant-epistemic-artifact/v0.28-test'
MAX_HISTORY=64;MAX_SNAPSHOT_BYTES=4*1024*1024;MAX_TEXT_BYTES=2048;MAX_OBJECTS=96
CYCLE_RE=re.compile(r'^[A-Za-z0-9._~-]{1,160}$');SHA_RE=re.compile(r'^[0-9a-f]{64}$')

class EpistemicWorkspaceError(PermissionError):pass

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def bounded_text(value:object,limit:int=MAX_TEXT_BYTES)->str:
 text=' '.join(str(value or '').replace('\x00',' ').split());raw=text.encode()
 if len(raw)<=limit:return text
 return raw[:limit].decode('utf-8',errors='ignore').rstrip()+'…'

def safe_scalar(value:object)->object:
 if value is None or isinstance(value,(bool,int,float,str)):return value
 return bounded_text(json.dumps(value,ensure_ascii=False,sort_keys=True,default=str),1024)

def frame_identity(value:object)->dict[str,Any]:
 if not isinstance(value,dict) or set(value)!={'runtime_session_id','epoch','frame_seq','frame_sha256'}:raise EpistemicWorkspaceError('exact acknowledged frame binding required')
 session=str(value.get('runtime_session_id') or '');epoch=value.get('epoch');seq=value.get('frame_seq');sha=str(value.get('frame_sha256') or '')
 if not session or not isinstance(epoch,int) or isinstance(epoch,bool) or epoch<1 or not isinstance(seq,int) or isinstance(seq,bool) or seq<1 or not SHA_RE.fullmatch(sha):raise EpistemicWorkspaceError('invalid acknowledged frame binding')
 return {'runtime_session_id':session,'epoch':epoch,'frame_seq':seq,'frame_sha256':sha}

def cycle_id(value:object)->str:
 cycle=str(value or '')
 if not CYCLE_RE.fullmatch(cycle):raise EpistemicWorkspaceError('invalid cycle id')
 return cycle

def load_json(path:Path)->dict[str,Any]:
 try:stat=path.stat()
 except OSError as exc:raise EpistemicWorkspaceError('Surface B snapshot unavailable') from exc
 if not path.is_file() or stat.st_size<=0 or stat.st_size>MAX_SNAPSHOT_BYTES:raise EpistemicWorkspaceError('Surface B snapshot outside bound')
 try:value=json.loads(path.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:raise EpistemicWorkspaceError('Surface B snapshot unreadable') from exc
 if not isinstance(value,dict):raise EpistemicWorkspaceError('Surface B snapshot must be object')
 return value

def artifact_descriptor(path:Path|None,*,kind:str)->dict[str,Any]:
 if path is None:return {'kind':kind,'available':False,'name':None,'bytes':None,'sha256':None}
 try:stat=path.stat()
 except OSError:return {'kind':kind,'available':False,'name':path.name,'bytes':None,'sha256':None}
 if not path.is_file():return {'kind':kind,'available':False,'name':path.name,'bytes':None,'sha256':None}
 return {'kind':kind,'available':True,'name':path.name,'bytes':int(stat.st_size),'sha256':sha256_file(path)}

def event_projection(rows:object,cycle:str)->list[dict[str,Any]]:
 out=[]
 if not isinstance(rows,list):return out
 for event in rows[-40:]:
  if not isinstance(event,dict):continue
  payload=event.get('payload') if isinstance(event.get('payload'),dict) else {};event_cycle=str(event.get('cycle_id') or payload.get('cycle_id') or '') or None
  out.append({'seq':event.get('seq') if isinstance(event.get('seq'),int) else None,'type':bounded_text(event.get('type') or 'EVENT',128),'cycle_id':event_cycle,'same_cycle':event_cycle in {None,cycle},'keys':[k for k in ('phase','reason','status','kind','count','validated') if k in payload]})
 return out

def object_projection(snapshot:dict[str,Any])->list[dict[str,Any]]:
 dyn=snapshot.get('dynamic_state') if isinstance(snapshot.get('dynamic_state'),dict) else {};objects=[];seen=set()
 def add(kind,label,source=None,confidence=None,evidence=None,node_id=None):
  if len(objects)>=MAX_OBJECTS:return
  text=bounded_text(label)
  if not text:return
  key=f'{kind}\0{text}\0{node_id or ""}'
  if key in seen:return
  seen.add(key);objects.append({'id':bounded_text(node_id or f'obj-{len(objects)+1}',192),'kind':bounded_text(kind,96),'label':text,'source':None if source is None else bounded_text(source,128),'confidence':safe_scalar(confidence),'evidence':safe_scalar(evidence)})
 for atom in dyn.get('mined_atoms',[]) if isinstance(dyn.get('mined_atoms'),list) else []:
  if isinstance(atom,dict):add(str(atom.get('kind') or 'atom'),atom.get('text'),atom.get('source_mode'),atom.get('confidence'),atom.get('evidence'),atom.get('id'))
 central=dyn.get('central_projection') if isinstance(dyn.get('central_projection'),dict) else {}
 for key,kind in (('must_surface_conflicts','conflict'),('interpretive_macro_candidates','hypothesis'),('authorized_directives','directive'),('downgrades','downgrade')):
  vals=central.get(key)
  if not isinstance(vals,list):continue
  for item in vals[:24]:
   if isinstance(item,dict):add(kind,item.get('text') or item.get('label') or item,item.get('source_mode'),item.get('confidence'),item.get('evidence'),item.get('id') or item.get('node_id'))
   else:add(kind,item)
 for item in dyn.get('runtime_backlog',[]) if isinstance(dyn.get('runtime_backlog'),list) else []:add('backlog',item)
 return objects

def ring_graph(snapshot:dict[str,Any])->dict[str,Any]:
 ret=snapshot.get('reticulum') if isinstance(snapshot.get('reticulum'),dict) else {};rings=ret.get('rings') if isinstance(ret.get('rings'),list) else [];states=ret.get('ring_states') if isinstance(ret.get('ring_states'),dict) else {};nodes=[]
 for idx,ring in enumerate(rings[:16]):
  name=bounded_text(ring,128);state=states.get(ring) if isinstance(states.get(ring),dict) else {};nodes.append({'id':f'ring-{idx}','label':name.replace('_',' '),'ring':name,'index':idx,'activation':safe_scalar(state.get('activation')),'confidence':safe_scalar(state.get('confidence')),'evidence':safe_scalar(state.get('evidence'))})
 return {'nodes':nodes,'edges':[{'source':f'ring-{i}','target':f'ring-{i+1}','kind':'concentric'} for i in range(max(0,len(nodes)-1))],'transmission_count':len(ret.get('transmissions') if isinstance(ret.get('transmissions'),list) else []),'layout':'CONCENTRIC_ORDERED'}
