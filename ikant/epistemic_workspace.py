from __future__ import annotations
from copy import deepcopy
import hashlib,json
from pathlib import Path
from typing import Any
from .epistemic_projection import *

class EpistemicWorkspaceReader:
 def __init__(self,root:str|Path):
  self.root=Path(root).resolve();self.state_dir=self.root/'.ikant';self.cognitive_dir=self.state_dir/'cognitive';self.artifacts_dir=self.state_dir/'artifacts'
 def _runtime(self)->dict[str,Any]:
  path=self.state_dir/'runtime.json'
  if not path.is_file():raise EpistemicWorkspaceError('runtime state unavailable')
  try:value=json.loads(path.read_text(encoding='utf-8'))
  except (OSError,json.JSONDecodeError) as exc:raise EpistemicWorkspaceError('runtime state unreadable') from exc
  if not isinstance(value,dict) or value.get('status')!='ACTIVE' or not str(value.get('session_id') or ''):raise EpistemicWorkspaceError('ACTIVE runtime required')
  return value
 def _cycle_files(self,session_id:str):
  if not self.cognitive_dir.is_dir():return []
  rows=[]
  for path in sorted(self.cognitive_dir.glob('*.json'),key=lambda p:p.stat().st_mtime_ns if p.exists() else 0,reverse=True):
   if len(rows)>=MAX_HISTORY:break
   if not CYCLE_RE.fullmatch(path.stem):continue
   try:snap=load_json(path)
   except EpistemicWorkspaceError:continue
   if str(snap.get('session_id') or '')==session_id and str(snap.get('cycle_id') or '')==path.stem:rows.append((path.stem,path,snap))
  return rows
 def index(self,*,frame_binding):
  frame=frame_identity(frame_binding);runtime=self._runtime();session=str(runtime['session_id'])
  if frame['runtime_session_id']!=session:raise EpistemicWorkspaceError('frame/runtime session mismatch')
  current=str((runtime.get('cognitive') or {}).get('last_surface_a_cycle_id') or '') or None;cycles=[]
  for cid,path,snap in self._cycle_files(session):
   dyn=snap.get('dynamic_state') if isinstance(snap.get('dynamic_state'),dict) else {};central=dyn.get('central_oracle') if isinstance(dyn.get('central_oracle'),dict) else {};projection=dyn.get('central_projection') if isinstance(dyn.get('central_projection'),dict) else {};conflicts=projection.get('must_surface_conflicts',[]);objects=object_projection(snap);docx=self.artifacts_dir/f'CRC_SNAPSHOT_{cid}.docx'
   cycles.append({'cycle_id':cid,'current':cid==current,'intent_sha256':snap.get('intent_sha256'),'regulative_mode':central.get('regulative_mode'),'object_count':len(objects),'conflict_count':len(conflicts) if isinstance(conflicts,list) else 0,'backlog_count':sum(1 for x in objects if x['kind']=='backlog'),'json':artifact_descriptor(path,kind='SURFACE_B_JSON'),'docx':artifact_descriptor(docx,kind='SURFACE_B_DOCX')})
  return {'schema':EPISTEMIC_INDEX_SCHEMA,'runtime_session_id':session,'frame_binding':frame,'current_cycle_id':current,'cycles':cycles,'history_limit':MAX_HISTORY,'read_only':True,'presentation_is_not_evidence':True,'presentation_is_not_authorization':True,'epistemic_authority':0.0,'execution_authority':0.0}
 def cycle(self,cid,*,frame_binding):
  frame=frame_identity(frame_binding);runtime=self._runtime();session=str(runtime['session_id'])
  if frame['runtime_session_id']!=session:raise EpistemicWorkspaceError('frame/runtime session mismatch')
  cid=cycle_id(cid);path=(self.cognitive_dir/f'{cid}.json').resolve()
  if path.parent!=self.cognitive_dir.resolve():raise EpistemicWorkspaceError('cycle path escape')
  snap=load_json(path)
  if str(snap.get('cycle_id') or '')!=cid or str(snap.get('session_id') or '')!=session:raise EpistemicWorkspaceError('Surface B cycle/session mismatch')
  dyn=snap.get('dynamic_state') if isinstance(snap.get('dynamic_state'),dict) else {};ret=snap.get('reticulum') if isinstance(snap.get('reticulum'),dict) else {};central=dyn.get('central_oracle') if isinstance(dyn.get('central_oracle'),dict) else {};proto=dyn.get('proto_self') if isinstance(dyn.get('proto_self'),dict) else {};diag=ret.get('diagnostics') if isinstance(ret.get('diagnostics'),dict) else {};docx=self.artifacts_dir/f'CRC_SNAPSHOT_{cid}.docx'
  return {'schema':EPISTEMIC_WORKSPACE_SCHEMA,'runtime_session_id':session,'cycle_id':cid,'current':cid==str((runtime.get('cognitive') or {}).get('last_surface_a_cycle_id') or ''),'frame_binding':frame,'snapshot_sha256':sha256_file(path),'intent_sha256':snap.get('intent_sha256'),'summary':{'regulative_mode':central.get('regulative_mode'),'proto_self_index':safe_scalar(proto.get('proto_self_index')),'epistemic_debt_open_count':safe_scalar(diag.get('epistemic_debt_open_count')),'mean_collapse':safe_scalar(diag.get('mean_coefficient_of_collapse')),'irreducibility_proxy':safe_scalar(diag.get('reticular_irreducibility_proxy'))},'objects':object_projection(snap),'graph':ring_graph(snap),'events':event_projection((snap.get('audit') or {}).get('recent_events'),cid),'artifacts':{'json':artifact_descriptor(path,kind='SURFACE_B_JSON'),'docx':artifact_descriptor(docx,kind='SURFACE_B_DOCX')},'read_only':True,'projection_is_not_source_snapshot':True,'presentation_is_not_evidence':True,'presentation_is_not_authorization':True,'epistemic_authority':0.0,'execution_authority':0.0}
 def artifact(self,cid,kind,*,frame_binding):
  frame=frame_identity(frame_binding);runtime=self._runtime();session=str(runtime['session_id'])
  if frame['runtime_session_id']!=session:raise EpistemicWorkspaceError('frame/runtime session mismatch')
  cid=cycle_id(cid);key=str(kind or '').upper()
  if key=='JSON':path=(self.cognitive_dir/f'{cid}.json').resolve();ctype='application/json; charset=utf-8';parent=self.cognitive_dir.resolve()
  elif key=='DOCX':path=(self.artifacts_dir/f'CRC_SNAPSHOT_{cid}.docx').resolve();ctype='application/vnd.openxmlformats-officedocument.wordprocessingml.document';parent=self.artifacts_dir.resolve()
  else:raise EpistemicWorkspaceError('unsupported artifact kind')
  if path.parent!=parent or not path.is_file():raise EpistemicWorkspaceError('artifact unavailable')
  if key=='JSON':
   snap=load_json(path)
   if str(snap.get('session_id') or '')!=session or str(snap.get('cycle_id') or '')!=cid:raise EpistemicWorkspaceError('artifact session/cycle mismatch')
  raw=path.read_bytes()
  if len(raw)>16*1024*1024:raise EpistemicWorkspaceError('artifact outside download bound')
  meta={'schema':EPISTEMIC_ARTIFACT_SCHEMA,'runtime_session_id':session,'cycle_id':cid,'kind':key,'frame_binding':frame,'name':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'read_only':True,'epistemic_authority':0.0,'execution_authority':0.0}
  return meta,raw,ctype

class EpistemicWorkspaceCoordinator:
 def __init__(self,base:Any):self.base=base;self.root=Path(base.root).resolve();self.reader=EpistemicWorkspaceReader(self.root)
 def __getattr__(self,name:str)->Any:return getattr(self.base,name)
 def _validated_binding(self,shell_id,client_id,frame_binding):
  frame=frame_identity(frame_binding);delegate=self.base._delegate_or_raise();session=delegate._active_session_id()
  with delegate.web_shell._lock:
   delegate.web_shell._require_bound(session,shell_id,client_id)
   if delegate.web_shell._pending is not None:raise EpistemicWorkspaceError('epistemic read unavailable while a sealed frame awaits exact ACK')
   last=deepcopy(delegate.web_shell._last_acked_frame)
  if last is None or last!=frame:raise EpistemicWorkspaceError('epistemic read must bind the exact last acknowledged frame')
  return frame
 def epistemic_index(self,shell_id,client_id,frame_binding):return self.reader.index(frame_binding=self._validated_binding(shell_id,client_id,frame_binding))
 def epistemic_cycle(self,cid,shell_id,client_id,frame_binding):return self.reader.cycle(cid,frame_binding=self._validated_binding(shell_id,client_id,frame_binding))
 def epistemic_artifact(self,cid,kind,shell_id,client_id,frame_binding):return self.reader.artifact(cid,kind,frame_binding=self._validated_binding(shell_id,client_id,frame_binding))
