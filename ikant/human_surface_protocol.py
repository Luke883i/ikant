from __future__ import annotations
import hashlib,json
from typing import Any
from .human_frame import validate_human_frame

HSP_SCHEMA='ikant-human-surface-protocol/v0.25-test'
HSP_KINDS=frozenset({'INITIALIZE','DASHBOARD','TURN','NOTICE','APPROVAL_REQUEST','PROGRESS','ERROR','DEGRADED','RECOVERY','EXIT','RESUME'})
HSP_STATES=frozenset({'READY','WORKING','NEEDS_HUMAN','DEGRADED','BLOCKED','RELEASING','RECOVERING'})
MAX_MESSAGE_BYTES=8192
MAX_PROGRESS_LABEL_BYTES=512
_KIND_STATE={
 'INITIALIZE':'READY','DASHBOARD':'READY','TURN':'READY','NOTICE':'READY','APPROVAL_REQUEST':'NEEDS_HUMAN',
 'PROGRESS':'WORKING','ERROR':'BLOCKED','DEGRADED':'DEGRADED','RECOVERY':'RECOVERING','EXIT':'RELEASING','RESUME':'READY'}
_PAYLOAD_KEYS=('surface_turn','notice','approval_request','progress','error','degraded','recovery','release')

def _canonical(x:dict[str,Any])->bytes:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def _digest(x:dict[str,Any])->str:return hashlib.sha256(_canonical(x)).hexdigest()
def _bounded_text(value:object,*,limit:int=MAX_MESSAGE_BYTES,required:bool=True)->str:
 text=' '.join(str(value or '').replace('\x00',' ').replace('\r',' ').split())
 if required and not text:raise ValueError('human surface text required')
 if len(text.encode('utf-8'))>limit:raise ValueError('human surface text outside bound')
 return text

def _approval_projection(frame:dict[str,Any],session_id:str)->dict[str,Any]:
 ok,errors=validate_human_frame(frame)
 if not ok:raise ValueError('invalid approval HumanFrame: '+'; '.join(errors))
 if frame.get('session_id')!=session_id:raise ValueError('approval HumanFrame session mismatch')
 purpose=str(frame.get('purpose') or '')
 if purpose not in {'CAPABILITY_GRANT','CAPABILITY_REVOKE','ACTION_CONFIRMATION'}:raise ValueError('HumanFrame is not a decision request')
 if frame.get('authority_effect')!='NONE' or frame.get('epistemic_authority') not in {0,0.0} or frame.get('execution_authority') not in {0,0.0}:raise ValueError('approval projection authority drift')
 return {'human_frame_schema':frame.get('schema'),'frame_sha256':frame.get('sha256'),'purpose':purpose,'title':_bounded_text(frame.get('title'),limit=1024),'body':_bounded_text(frame.get('body')),'subject_id':frame.get('subject_id'),'cycle_id':frame.get('cycle_id'),'action_fingerprint':frame.get('action_fingerprint'),'handoff_id':frame.get('handoff_id'),'requested_entitlements':list(frame.get('requested_entitlements') or []),'requires_explicit_decision':True,'presentation_is_not_authorization':True,'decision_recorded':False,'grant_issued':False,'epistemic_authority':0.0,'execution_authority':0.0}

def _turn_projection(dashboard:dict[str,Any],cycle_id:str|None)->dict[str,Any]:
 inc=dashboard.get('incarnate') or {};a=inc.get('surface_a') or {};b=inc.get('surface_b') or {};expected=str(cycle_id or inc.get('cycle_id') or '') or None
 if inc.get('state')!='READY':raise ValueError('TURN requires READY incarnate surface')
 if a.get('status')!='VALIDATED' or not str(a.get('text') or '').strip():raise ValueError('TURN requires validated Surface A')
 if b.get('bound') is not True:raise ValueError('TURN requires bound Surface B')
 if a.get('cycle_id')!=expected or b.get('cycle_id')!=expected:raise ValueError('TURN cycle binding mismatch')
 return {'cycle_id':expected,'surface_a_sha256':hashlib.sha256(str(a.get('text')).encode('utf-8')).hexdigest(),'surface_b_json_sha256':(b.get('json') or {}).get('sha256'),'surface_b_docx_sha256':(b.get('docx') or {}).get('sha256'),'surface_a_inside_dashboard':True,'surface_b_bound':True}

def project_human_surface(runtime:Any,dashboard:dict[str,Any],*,kind:str,cycle_id:str|None=None,notice:str|None=None,approval_frame:dict[str,Any]|None=None,progress:dict[str,Any]|None=None,error:dict[str,Any]|None=None,degraded:dict[str,Any]|None=None,recovery:dict[str,Any]|None=None,release_after_frame:bool=False)->dict[str,Any]:
 k=str(kind or '').upper()
 if k not in HSP_KINDS:raise ValueError('unsupported human surface kind')
 state=getattr(runtime,'runtime',{}) if isinstance(getattr(runtime,'runtime',None),dict) else {};session_id=str(state.get('session_id') or '')
 if not session_id:raise ValueError('runtime session required')
 eg=dashboard.get('session_egress') or {}
 if not eg:raise ValueError('human surface requires egress projection')
 payload={x:None for x in _PAYLOAD_KEYS}
 if k=='TURN':payload['surface_turn']=_turn_projection(dashboard,cycle_id)
 elif k=='NOTICE':payload['notice']={'message':_bounded_text(notice),'authority_effect':'NONE'}
 elif k=='APPROVAL_REQUEST':
  if not isinstance(approval_frame,dict):raise ValueError('approval frame required')
  payload['approval_request']=_approval_projection(approval_frame,session_id)
 elif k=='PROGRESS':
  p=dict(progress or {});label=_bounded_text(p.get('label'),limit=MAX_PROGRESS_LABEL_BYTES);fraction=p.get('fraction')
  if fraction is not None and (not isinstance(fraction,(int,float)) or isinstance(fraction,bool) or float(fraction)<0 or float(fraction)>1):raise ValueError('progress fraction outside bound')
  payload['progress']={'phase':_bounded_text(p.get('phase') or 'WORKING',limit=128),'label':label,'fraction':None if fraction is None else round(float(fraction),6),'cancellable':bool(p.get('cancellable',False)),'authority_effect':'NONE'}
 elif k=='ERROR':
  e=dict(error or {});payload['error']={'code':_bounded_text(e.get('code') or 'RUNTIME_ERROR',limit=128),'message':_bounded_text(e.get('message')),'retryable':bool(e.get('retryable',False)),'authority_effect':'NONE'}
 elif k=='DEGRADED':
  d=dict(degraded or {});payload['degraded']={'code':_bounded_text(d.get('code') or 'DEGRADED',limit=128),'message':_bounded_text(d.get('message')),'capability_loss':sorted({_bounded_text(x,limit=256) for x in (d.get('capability_loss') or [])}),'authority_effect':'NONE'}
 elif k=='RECOVERY':payload['recovery']={'reason':_bounded_text((recovery or {}).get('reason') or 'sealed frame recovery'),'replay_only':True,'authority_effect':'NONE'}
 elif k=='EXIT':
  if not release_after_frame:raise ValueError('EXIT must release after frame')
  payload['release']={'command':'EXIT IKANT','release_after_frame':True,'authority_effect':'NONE'}
 elif k=='RESUME':
  if release_after_frame:raise ValueError('RESUME cannot release')
 elif k in {'INITIALIZE','DASHBOARD'}:
  if release_after_frame:raise ValueError(k+' cannot release')
 if k!='EXIT' and release_after_frame:raise ValueError('release allowed only for EXIT')
 active=[name for name,value in payload.items() if value is not None]
 expected={'TURN':'surface_turn','NOTICE':'notice','APPROVAL_REQUEST':'approval_request','PROGRESS':'progress','ERROR':'error','DEGRADED':'degraded','RECOVERY':'recovery','EXIT':'release'}.get(k)
 if expected and active!=[expected]:raise ValueError('human surface payload exclusivity')
 if not expected and active:raise ValueError('unexpected human surface payload')
 env={'schema':HSP_SCHEMA,'runtime_session_id':session_id,'egress_epoch':eg.get('epoch'),'egress_state':eg.get('state'),'kind':k,'state':_KIND_STATE[k],'cycle_id':None if cycle_id is None else str(cycle_id),'payload':payload,'single_human_egress':True,'semantic_payload_inside_dashboard_only':True,'raw_model_tokens_visible':False,'parallel_human_message_allowed':False,'presentation_is_not_authorization':True,'epistemic_authority':0.0,'execution_authority':0.0}
 env['sha256']=_digest(env);dashboard['human_surface_protocol']=env;return dashboard

def validate_human_surface(dashboard:dict[str,Any])->tuple[bool,list[str]]:
 env=dict(dashboard.get('human_surface_protocol') or {});errors=[]
 if env.get('schema')!=HSP_SCHEMA:errors.append('schema')
 if env.get('kind') not in HSP_KINDS:errors.append('kind')
 if env.get('state') not in HSP_STATES or env.get('state')!=_KIND_STATE.get(env.get('kind')):errors.append('state')
 for key in ('single_human_egress','semantic_payload_inside_dashboard_only'):
  if env.get(key) is not True:errors.append(key)
 for key in ('raw_model_tokens_visible','parallel_human_message_allowed'):
  if env.get(key) is not False:errors.append(key)
 if env.get('presentation_is_not_authorization') is not True:errors.append('presentation_authority')
 if env.get('epistemic_authority') not in {0,0.0} or env.get('execution_authority') not in {0,0.0}:errors.append('authority')
 p=env.get('payload')
 if not isinstance(p,dict) or set(p)!=set(_PAYLOAD_KEYS):errors.append('payload_shape');p=p if isinstance(p,dict) else {}
 active=[k for k in _PAYLOAD_KEYS if p.get(k) is not None]
 expected={'TURN':'surface_turn','NOTICE':'notice','APPROVAL_REQUEST':'approval_request','PROGRESS':'progress','ERROR':'error','DEGRADED':'degraded','RECOVERY':'recovery','EXIT':'release'}.get(env.get('kind'))
 if expected:
  if active!=[expected]:errors.append('payload_exclusivity')
 elif active:errors.append('unexpected_payload')
 if env.get('kind')=='APPROVAL_REQUEST':
  a=p.get('approval_request') or {}
  if a.get('requires_explicit_decision') is not True or a.get('presentation_is_not_authorization') is not True or a.get('decision_recorded') is not False or a.get('grant_issued') is not False:errors.append('approval_boundary')
 if env.get('kind')=='TURN':
  t=p.get('surface_turn') or {}
  if t.get('surface_a_inside_dashboard') is not True or t.get('surface_b_bound') is not True:errors.append('turn_binding')
 if env.get('kind')=='EXIT' and (p.get('release') or {}).get('release_after_frame') is not True:errors.append('exit_release')
 supplied=env.pop('sha256',None)
 if supplied!=_digest(env):errors.append('digest')
 return not errors,list(dict.fromkeys(errors))
