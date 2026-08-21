from __future__ import annotations
import threading
from typing import Any
from .bootstrap_observability import EVENTS_SCHEMA,BootstrapDiagnosticError,BootstrapJournal,classify_failure,exception_chain,new_attempt_id
from .local_service import LocalAppError
from .managed_runtime import ManagedRuntimeError
from .product_experience import ProductBootstrapCoordinator,ProductExperienceService
from .voice_input import LocalVoiceInputBroker
BOOTSTRAP_OBSERVABILITY_SCHEMA='ikant-bootstrap-observability/v0.29-test'
_STEPS=('WEB_APP','MANIFEST','ENGINE_COMPONENT','MODEL_COMPONENT','ENGINE_PROCESS','ENGINE_READINESS','PRODUCT_SERVICE');_COMPONENT_STEPS=frozenset({'ENGINE_COMPONENT','MODEL_COMPONENT'})
class ObservableProductBootstrapCoordinator(ProductBootstrapCoordinator):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.bootstrap_journal=BootstrapJournal(self.root);self._attempt_id=new_attempt_id();self._diagnostic_step='WEB_APP';self._diagnostic_degraded=None;self._error_detail=None;self._terminal_steps=set();self._started_steps=set()
 def _diag(self,step,outcome,code,target='',detail='',bytes_count=None,total_bytes=None,remediation=None,cause_chain=None):
  if step not in _STEPS:step='PRODUCT_SERVICE'
  self._diagnostic_step=step
  if outcome=='START':self._started_steps.add(step)
  if outcome in {'PASS','FAIL'}:self._terminal_steps.add(step)
  try:self.bootstrap_journal.append(attempt_id=self._attempt_id,attempt=max(1,self._attempt),step=step,outcome=outcome,code=code,target=target,detail=detail,bytes_count=bytes_count,total_bytes=total_bytes,remediation=remediation,cause_chain=cause_chain);self._diagnostic_degraded=None
  except BootstrapDiagnosticError as exc:self._diagnostic_degraded=type(exc).__name__
 def start_async(self):
  with self._lock:
   if self._stopping:raise LocalAppError('product runtime is stopping')
   if self._delegate is not None:return self.product_status()
   if self._thread is not None and self._thread.is_alive():return self.product_status()
   self._attempt+=1;self._attempt_id=new_attempt_id();self._stage='PREPARING';self._progress={'phase':'PREPARING','target':'verified local runtime','bytes':0};self._planned_bytes=0;self._error_code=None;self._error_detail=None;self._terminal_steps=set();self._started_steps=set();self._diag('WEB_APP','PASS','LOCAL_WEB_AVAILABLE','iKant local web application','loopback product surface is available while runtime preparation continues');self._diag('MANIFEST','START','RUNTIME_MANIFEST_LOAD','MODEL_RUNTIME.json','loading and validating pinned managed-runtime manifest');t=threading.Thread(target=self._prepare,name='ikant-product-bootstrap',daemon=True);self._thread=t;t.start()
  return self.product_status()
 def _component_step(self,target):
  low=str(target or '').lower()
  if low.endswith('.gguf') or 'qwen' in low:return 'MODEL_COMPONENT'
  if any(x in low for x in ('.tar.gz','.tgz','llama','engine')):return 'ENGINE_COMPONENT'
  return self._diagnostic_step
 def _start_if_missing(self,step,code,target,detail):
  if step not in self._started_steps and step not in self._terminal_steps:self._diag(step,'START',code,target,detail)
 def _component_from_event(self,src,target):
  explicit=str(src.get('component') or '');return explicit if explicit in _COMPONENT_STEPS else self._component_step(target)
 def _on_progress(self,event:Any):
  src=event if isinstance(event,dict) else {};phase=str(src.get('phase') or 'PREPARING').upper();target=str(src.get('target') or 'component');size=int(src.get('bytes') or 0) if isinstance(src.get('bytes'),int) and not isinstance(src.get('bytes'),bool) else 0;detail=str(src.get('detail') or '')
  if phase=='PLAN':
   if 'MANIFEST' not in self._terminal_steps:self._diag('MANIFEST','PASS','RUNTIME_MANIFEST_VERIFIED','MODEL_RUNTIME.json',detail or 'pinned managed-runtime manifest loaded and validated')
  elif phase=='CHECKING':step=self._component_from_event(src,target);self._start_if_missing(step,f'{step}_CHECK',target,detail or 'checking verified local component state')
  elif phase=='DOWNLOADING':step=self._component_from_event(src,target);self._start_if_missing(step,'COMPONENT_ACQUISITION_START',target,'acquiring pinned component');self._diag(step,'PROGRESS','COMPONENT_DOWNLOADING',target,detail or 'downloading pinned component',bytes_count=size,total_bytes=self._planned_bytes if step=='MODEL_COMPONENT' and self._planned_bytes else None)
  elif phase=='VERIFIED':step=self._component_from_event(src,target);self._start_if_missing(step,'COMPONENT_ACQUISITION_START',target,'acquiring pinned component');self._diag(step,'INFO','COMPONENT_ARTIFACT_VERIFIED',target,detail or 'download artifact digest verified',bytes_count=size,total_bytes=self._planned_bytes if step=='MODEL_COMPONENT' and self._planned_bytes else None)
  elif phase=='COMPONENT_READY':
   step=self._component_from_event(src,target);self._start_if_missing(step,f'{step}_CHECK',target,'checking verified local component state')
   if step not in self._terminal_steps:self._diag(step,'PASS',f'{step}_VERIFIED',target,detail or 'component verified and ready',bytes_count=size,total_bytes=self._planned_bytes if step=='MODEL_COMPONENT' and self._planned_bytes else None)
  elif phase=='ENGINE_STARTING':self._start_if_missing('ENGINE_PROCESS','ENGINE_PROCESS_START',target,detail or 'starting verified local engine process')
  elif phase=='ENGINE_PROBING':
   self._start_if_missing('ENGINE_PROCESS','ENGINE_PROCESS_START',target,'starting verified local engine process')
   if 'ENGINE_PROCESS' not in self._terminal_steps:self._diag('ENGINE_PROCESS','PASS','ENGINE_PROCESS_RUNNING',target,'local engine process started')
   self._start_if_missing('ENGINE_READINESS','ENGINE_READINESS_WAIT',target,detail or 'waiting for constrained readiness probe')
  elif phase=='ENGINE_READY':
   if 'ENGINE_PROCESS' not in self._terminal_steps:self._start_if_missing('ENGINE_PROCESS','ENGINE_PROCESS_START',target,'starting verified local engine process');self._diag('ENGINE_PROCESS','PASS','ENGINE_PROCESS_RUNNING',target,'local engine process started')
   self._start_if_missing('ENGINE_READINESS','ENGINE_READINESS_WAIT',target,'waiting for constrained readiness probe')
   if 'ENGINE_READINESS' not in self._terminal_steps:self._diag('ENGINE_READINESS','PASS','ENGINE_READINESS_READY',target,detail or 'constrained readiness probe passed')
  super()._on_progress(event)
 def _pass_missing_runtime_gates(self):
  for step,code,target,detail in (('MANIFEST','RUNTIME_MANIFEST_VERIFIED','MODEL_RUNTIME.json','manifest validated by S5'),('ENGINE_COMPONENT','ENGINE_COMPONENT_VERIFIED','llama.cpp','engine component verified by S5'),('MODEL_COMPONENT','MODEL_COMPONENT_VERIFIED','local LLM','model component verified by S5'),('ENGINE_PROCESS','ENGINE_PROCESS_RUNNING','llama-server','local engine process started by S5'),('ENGINE_READINESS','ENGINE_READINESS_READY','local LLM','constrained readiness probe passed')):
   if step not in self._terminal_steps:self._start_if_missing(step,code.replace('VERIFIED','CHECK').replace('RUNNING','START').replace('READY','WAIT'),target,detail);self._diag(step,'PASS',code,target,detail)
 def _failure_step(self,code):
  if code in {'ENGINE_READINESS_TIMEOUT','ENGINE_EXITED_EARLY','ENGINE_READINESS_FAILED'}:return 'ENGINE_READINESS'
  if code=='ENGINE_START_FAILED':return 'ENGINE_PROCESS'
  return self._diagnostic_step if self._diagnostic_step in _STEPS else 'PRODUCT_SERVICE'
 def _prepare(self):
  try:
   model=self.runtime.start(progress=self._on_progress,readiness_timeout=self.readiness_timeout);self._pass_missing_runtime_gates();self._diag('PRODUCT_SERVICE','START','PRODUCT_SERVICE_BIND','iKant cognitive service','binding verified managed model into S8/S9 service');voice=LocalVoiceInputBroker(self.voice_endpoint);delegate=ProductExperienceService(self.root,model=model,voice=voice)
   with self._lock:adapter=self._web_adapter
   if adapter is not None:delegate.bind_web_adapter(adapter)
   with self._lock:
    if self._stopping:raise ManagedRuntimeError('product runtime stopping')
    self._delegate=delegate;self._stage='READY';self._progress={'phase':'READY','target':'verified local runtime','bytes':max(self._planned_bytes,int(self._progress.get('bytes') or 0))};self._error_code=None;self._error_detail=None
   self._diag('PRODUCT_SERVICE','PASS','PRODUCT_SERVICE_READY','iKant cognitive service','verified local runtime is ready for admission')
  except Exception as exc:
   code,remediation=classify_failure(self._diagnostic_step,exc);step=self._failure_step(code);chain=exception_chain(exc);detail=chain[-1]['message'] if chain else str(exc);self._diag(step,'FAIL',code,self._progress.get('target') or 'verified local runtime',detail,remediation=remediation,cause_chain=chain)
   with self._lock:self._delegate=None;self._stage='BLOCKED';self._error_code=code;self._error_detail=detail[:768];self._progress={'phase':'BLOCKED','target':self._progress.get('target') or 'verified local runtime','bytes':int(self._progress.get('bytes') or 0)}
 def bootstrap_status(self):
  with self._lock:attempt=max(1,self._attempt);attempt_id=self._attempt_id;stage=self._stage;code=self._error_code;detail=self._error_detail;degraded=self._diagnostic_degraded
  out=self.bootstrap_journal.status(attempt_id=attempt_id,attempt=attempt);out['schema']=BOOTSTRAP_OBSERVABILITY_SCHEMA;out['runtime_stage']=stage;out['diagnostics_degraded']=degraded
  if stage=='BLOCKED' and out['summary']['failed']==0:out['overall']='BLOCKED';out['fallback_failure']={'code':code or 'BOOTSTRAP_FAILED','detail':detail or 'runtime blocked; structured journal unavailable','remediation':{'id':'OPEN_RAW_DIAGNOSTICS','label':'Controlla il log diagnostico e riprova','action':'retry'}}
  out['silent_failure']=bool(stage=='BLOCKED' and not (out['summary']['failed'] or out.get('fallback_failure')));return out
 def bootstrap_events(self,after_seq=0,limit=128):
  try:after=max(0,int(after_seq));size=max(1,min(256,int(limit)))
  except (TypeError,ValueError) as exc:raise LocalAppError('invalid bootstrap event cursor') from exc
  with self._lock:attempt=max(1,self._attempt);attempt_id=self._attempt_id
  return {'schema':EVENTS_SCHEMA,'attempt_id':attempt_id,'attempt':attempt,'events':self.bootstrap_journal.events(attempt_id=attempt_id,after_seq=after,limit=size),'epistemic_authority':0.0,'execution_authority':0.0}
 def bootstrap_raw(self):return self.bootstrap_journal.raw_bytes(),'application/x-ndjson; charset=utf-8'
 def product_status(self):
  out=super().product_status();diag=dict(out.get('diagnostics') or {});diag['error_code']=self._error_code;diag['error_detail']=self._error_detail;diag['bootstrap_observability']=self.bootstrap_status();out['diagnostics']=diag;return out
