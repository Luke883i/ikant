from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Callable
from .component_manifest import load_manifest
from .component_store import atomic_json
from .engine_supervisor import EngineSupervisor
from .foundation import ExperimentModelProxy
from .local_service import LocalAppError,LocalEmbodimentService
from .model_broker import LocalModelBroker
from .model_manager import ModelManager
MANAGED_RUNTIME_SCHEMA="ikant-managed-local-runtime/v0.23-test"
class ManagedRuntimeError(RuntimeError):pass
def _binding_digest(binding:dict[str,Any])->str:
 material={"manifest_sha256":binding["manifest_sha256"],"engine":{"id":binding["engine"]["id"],"version":binding["engine"]["version"],"platform":binding["engine"]["platform"],"artifact_sha256":binding["engine"]["artifact_sha256"]},"model":{"id":binding["model"]["id"],"revision":binding["model"]["revision"],"sha256":binding["model"]["sha256"]}};return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class ManagedLocalRuntime:
 def __init__(self,root:str|Path,*,manifest_path:str|Path|None=None,component_root:str|Path|None=None,manager_factory:Callable[...,ModelManager]=ModelManager,supervisor_factory:Callable[...,EngineSupervisor]=EngineSupervisor):self.root=Path(root).resolve();self.state_dir=self.root/'.ikant';self.manifest_path=Path(manifest_path).resolve() if manifest_path else self.root/'MODEL_RUNTIME.json';self.component_root=Path(component_root).resolve() if component_root else None;self.manager_factory=manager_factory;self.supervisor_factory=supervisor_factory;self.supervisor=None;self.binding=None;self.binding_digest=None
 @property
 def projection_path(self)->Path:return self.state_dir/'model-runtime.json'
 def _persist(self,status:str,**extra):
  payload={'schema':MANAGED_RUNTIME_SCHEMA,'status':status,'managed':True,'browser_model_transport':False,'api_key_persisted':False,'model_output_is_authority':False,'component_presence_is_authority':False,'runtime_readiness_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0};payload.update(extra);atomic_json(self.projection_path,payload)
 def start(self,*,progress=None,readiness_timeout:float=45.0)->LocalModelBroker:
  if self.supervisor is not None:raise ManagedRuntimeError('managed runtime already started')
  try:
   manifest=load_manifest(self.manifest_path);self._persist('PREPARING',manifest_sha256=hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())
   if progress:
    model=manifest['model'];progress({'phase':'PLAN','component':'MANIFEST','bytes':int(model['display_size_mb'])*1_000_000,'target':str(model['id']),'detail':'pinned managed-runtime manifest validated'})
   manager=self.manager_factory(manifest,component_root=self.component_root);binding=manager.ensure(progress=progress);digest=_binding_digest(binding);supervisor=self.supervisor_factory(self.state_dir)
   if hasattr(supervisor,'progress'):supervisor.progress=progress
   session=supervisor.start(binding,timeout=readiness_timeout)
   if session.get('status')!='READY' or session.get('browser_model_transport') is not False:supervisor.stop();raise ManagedRuntimeError('managed engine did not reach constrained readiness')
   self.supervisor=supervisor;self.binding=binding;self.binding_digest=digest;self._persist('READY',manifest_sha256=binding['manifest_sha256'],binding_sha256=digest,engine={'id':binding['engine']['id'],'version':binding['engine']['version'],'platform':binding['engine']['platform'],'artifact_sha256':binding['engine']['artifact_sha256']},model={'id':binding['model']['id'],'revision':binding['model']['revision'],'sha256':binding['model']['sha256']});broker=LocalModelBroker(str(session['endpoint']),model=str(session['model_id']),api_key=str(session['api_key']),runtime_binding_digest=digest,managed_runtime=True);return ExperimentModelProxy(self.root,broker)
  except Exception as exc:
   self._persist('BLOCKED',error=type(exc).__name__);self.stop(persist=False)
   if isinstance(exc,ManagedRuntimeError):raise
   raise ManagedRuntimeError('managed local runtime failed closed') from exc
 def stop(self,*,persist=True):
  supervisor,self.supervisor=self.supervisor,None
  if supervisor is not None:supervisor.stop()
  if persist and self.projection_path.exists():
   extra={}
   if self.binding_digest:extra['binding_sha256']=self.binding_digest
   self._persist('STOPPED',**extra)
class ManagedLocalEmbodimentService(LocalEmbodimentService):
 def _managed_model_check(self):
  managed=bool(getattr(self.model,'managed_runtime',False));healthy=managed and self.model.health();binding=str(getattr(self.model,'runtime_binding_digest','') or '');return {'status':'AVAILABLE' if healthy and len(binding)==64 else 'UNAVAILABLE','detail':'verified managed engine reachable' if healthy and len(binding)==64 else 'managed engine unavailable or unbound','binding_sha256':binding if len(binding)==64 else None,'model_output_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
 def _bind_runtime_epoch(self):
  from .runtime import Runtime
  from .runtime_epoch import compact_epoch,materialize_runtime_epoch
  rt=Runtime(self.state_dir)
  try:
   rt.require_active();epoch=materialize_runtime_epoch(self.root,require_managed_binding=True);rt.runtime['runtime_epoch']=compact_epoch(epoch);rt._write_runtime();return epoch
  finally:rt.close()
 def probe(self):
  with self._lock:
   out=super().probe();out['checks']['MODEL_RUNTIME']=self._managed_model_check();out['overall']='READY' if all(x.get('status')=='AVAILABLE' for x in out['checks'].values()) else 'BLOCKED';from .admission import save_probe;save_probe(self.state_dir,out);return out
 def initialize(self):
  if self._managed_model_check()['status']!='AVAILABLE':raise LocalAppError('INITIALIZE requires the verified managed language engine to remain READY')
  out=super().initialize();self._bind_runtime_epoch();return out
 def lifecycle(self):
  out=super().lifecycle()
  if out.get('state')!='ACTIVE':out['surface_phase']='PRE_ACTIVE_BOOTSTRAP';return out
  from .runtime import Runtime
  from .runtime_recovery import verified_recovery
  try:
   rt=Runtime(self.state_dir)
   try:recovery=verified_recovery(rt)
   finally:rt.close()
   state=str(recovery.get('state') or '');needs=state in {'INTERRUPTED_UNSEALED','SURFACE_A_UNSEALED','RECOVERY_ACKED_PENDING_RECONCILE','INTEGRITY_BLOCKED'};out['surface_phase']='RECOVERY_REQUIRED' if needs else 'ACTIVE_CANONICAL';out['runtime_recovery']={k:recovery.get(k) for k in ('schema','state','recovery_required','cycle_id','model_reexecuted','planner_reexecuted','material_driver_reexecuted','epistemic_authority','execution_authority')}
  except Exception:
   out['surface_phase']='INTEGRITY_CHECK_REQUIRED';out['runtime_recovery']={'schema':'ikant-runtime-recovery/v1-test','state':'INTEGRITY_BLOCKED','recovery_required':True,'epistemic_authority':0.0,'execution_authority':0.0}
  return out
 def frame(self):
  from .runtime import Runtime
  from .runtime_recovery import materialize_recovery_frame
  with self._lock:
   rt=Runtime(self.state_dir)
   try:
    rt.require_active();recovered=materialize_recovery_frame(rt)
    if recovered is not None:return recovered
   finally:rt.close()
   return super().frame()
 def acknowledge(self,ack):
  from .runtime_recovery import finalize_recovery_after_ack,recovery_ack_target
  target=recovery_ack_target(self.root);out=super().acknowledge(ack);finalize_recovery_after_ack(self.root,target);return out
 def turn(self,user_text):
  self._bind_runtime_epoch();return super().turn(user_text)
