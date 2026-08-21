from __future__ import annotations
import hashlib,json,math,re
from typing import Any
from .human_frame import normalize_entitlements,validate_human_frame

HSP_SCHEMA='ikant-human-surface-protocol/v0.25-test'
HSP_KINDS=frozenset({'INITIALIZE','DASHBOARD','TURN','NOTICE','APPROVAL_REQUEST','PROGRESS','ERROR','DEGRADED','RECOVERY','EXIT','RESUME'})
HSP_STATES=frozenset({'READY','WORKING','NEEDS_HUMAN','DEGRADED','BLOCKED','RELEASING','RECOVERING'})
MAX_MESSAGE_BYTES=8192
MAX_PROGRESS_LABEL_BYTES=512
_KIND_STATE={'INITIALIZE':'READY','DASHBOARD':'READY','TURN':'READY','NOTICE':'READY','APPROVAL_REQUEST':'NEEDS_HUMAN','PROGRESS':'WORKING','ERROR':'BLOCKED','DEGRADED':'DEGRADED','RECOVERY':'RECOVERING','EXIT':'RELEASING','RESUME':'READY'}
_PAYLOAD_KEYS=('surface_turn','notice','approval_request','progress','error','degraded','recovery','release')
_SHA256_RE=re.compile(r'^[0-9a-f]{64}$')

def _canonical(x:dict[str,Any])->bytes:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _digest(x:dict[str,Any])->str:return hashlib.sha256(_canonical(x)).hexdigest()
def _bounded_text(value:object,*,limit:int=MAX_MESSAGE_BYTES,required:bool=True)->str:
 text=' '.join(str(value or '').replace('\x00',' ').replace('\r',' ').split())
 if required and not text:raise ValueError('human surface text required')
 if len(text.encode('utf-8'))>limit:raise ValueError('human surface text outside bound')
 return text

def _valid_bounded_text(value:object,limit:int)->bool:
 if not isinstance(value,str):return False
 try:return bool(value) and value==_bounded_text(value,limit=limit) and len(value.encode('utf-8'))<=limit
 except (TypeError,ValueError):return False

def _approval_projection(frame:dict[str,Any],session_id:str)->dict[str,Any]:
 ok,errors=validate_human_frame(frame)
 if not ok:raise ValueError('invalid approval HumanFrame: '+'; '.join(errors))
 if frame.get('session_id')!=session_id:raise ValueError('approval HumanFrame session mismatch')
 purpose=str(frame.get('purpose') or '')
 if purpose not in {'CAPABILITY_GRANT','CAPABILITY_REVOKE','ACTION_CONFIRMATION'}:raise ValueError('HumanFrame is not a decision request')
 if frame.get('authority_effect')!='NONE' or frame.get('epistemic_authority') not in {0,0.0} or frame.get('execution_authority') not in {0,0.0}:raise ValueError('approval projection authority drift')
 return {'human_frame_schema':frame.get('schema'),'frame_sha256':frame.get('sha256'),'session_id':frame.get('session_id'),'actor_binding_id':frame.get('actor_binding_id'),'purpose':purpose,'title':_bounded_text(frame.get('title'),limit=1024),'body':_bounded_text(frame.get('body')),'subject_id':frame.get('subject_id'),'cycle_id':frame.get('cycle_id'),'action_fingerprint':frame.get('action_fingerprint'),'handoff_id':frame.get('handoff_id'),'requested_entitlements':list(frame.get('requested_entitlements') or []),'requires_explicit_decision':True,'presentation_is_not_authorization':True,'decision_recorded':False,'grant_issued':False,'epistemic_authority':0.0,'execution_authority':0.0}

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
 eg=dashboard.get('session_egress') or {};epoch=eg.get('epoch')
 if eg.get('state')!='DASHBOARD_LOCKED' or not isinstance(epoch,int) or isinstance(epoch,bool) or epoch<1:raise ValueError('human surface requires locked positive egress epoch')
 payload={x:None for x in _PAYLOAD_KEYS}
 if k=='TURN':payload['surface_turn']=_turn_projection(dashboard,cycle_id)
 elif k in {'NOTICE','INITIALIZE','RESUME'}:payload['notice']={'message':_bounded_text(notice or ({'INITIALIZE':'iKant ACTIVE.','RESUME':'iKant riattivato.'}.get(k) or 'iKant notice')),'authority_effect':'NONE'}
 elif k=='APPROVAL_REQUEST':
  if not isinstance(approval_frame,dict):raise ValueError('approval frame required')
  payload['approval_request']=_approval_projection(approval_frame,session_id)
 elif k=='PROGRESS':
  p=dict(progress or {});label=_bounded_text(p.get('label'),limit=MAX_PROGRESS_LABEL_BYTES);fraction=p.get('fraction')
  if fraction is not None:
   if not isinstance(fraction,(int,float)) or isinstance(fraction,bool):raise ValueError('progress fraction must be numeric')
   f=float(fraction)
   if not math.isfinite(f) or f<0 or f>1:raise ValueError('progress fraction outside bound')
  payload['progress']={'phase':_bounded_text(p.get('phase') or 'WORKING',limit=128),'label':label,'fraction':None if fraction is None else round(float(fraction),6),'cancellable':bool(p.get('cancellable',False)),'authority_effect':'NONE'}
 elif k=='ERROR':
  e=dict(error or {});payload['error']={'code':_bounded_text(e.get('code') or 'RUNTIME_ERROR',limit=128),'message':_bounded_text(e.get('message')),'retryable':bool(e.get('retryable',False)),'authority_effect':'NONE'}
 elif k=='DEGRADED':
  d=dict(degraded or {});payload['degraded']={'code':_bounded_text(d.get('code') or 'DEGRADED',limit=128),'message':_bounded_text(d.get('message')),'capability_loss':sorted({_bounded_text(x,limit=256) for x in (d.get('capability_loss') or [])}),'authority_effect':'NONE'}
 elif k=='RECOVERY':payload['recovery']={'reason':_bounded_text((recovery or {}).get('reason') or 'sealed frame recovery'),'replay_only':True,'authority_effect':'NONE'}
 elif k=='EXIT':
  if not release_after_frame:raise ValueError('EXIT must release after frame')
  payload['release']={'command':'EXIT IKANT','message':_bounded_text(notice or 'Uscita da iKant confermata.'),'release_after_frame':True,'authority_effect':'NONE'}
 elif k=='DASHBOARD':
  if release_after_frame:raise ValueError('DASHBOARD cannot release')
 if k!='EXIT' and release_after_frame:raise ValueError('release allowed only for EXIT')
 active=[name for name,value in payload.items() if value is not None]
 expected={'TURN':'surface_turn','NOTICE':'notice','INITIALIZE':'notice','RESUME':'notice','APPROVAL_REQUEST':'approval_request','PROGRESS':'progress','ERROR':'error','DEGRADED':'degraded','RECOVERY':'recovery','EXIT':'release'}.get(k)
 if expected and active!=[expected]:raise ValueError('human surface payload exclusivity')
 if not expected and active:raise ValueError('unexpected human surface payload')
 env={'schema':HSP_SCHEMA,'runtime_session_id':session_id,'egress_epoch':epoch,'egress_state':eg.get('state'),'kind':k,'state':_KIND_STATE[k],'cycle_id':None if cycle_id is None else str(cycle_id),'payload':payload,'single_human_egress':True,'semantic_payload_inside_dashboard_only':True,'raw_model_tokens_visible':False,'parallel_human_message_allowed':False,'presentation_is_not_authorization':True,'epistemic_authority':0.0,'execution_authority':0.0}
 env['sha256']=_digest(env);dashboard['human_surface_protocol']=env;return dashboard

def validate_human_surface(dashboard:dict[str,Any])->tuple[bool,list[str]]:
 raw=dashboard.get('human_surface_protocol');env=dict(raw) if isinstance(raw,dict) else {};errors=[]
 if env.get('schema')!=HSP_SCHEMA:errors.append('schema')
 kind=env.get('kind')
 if kind not in HSP_KINDS:errors.append('kind')
 if env.get('state') not in HSP_STATES or env.get('state')!=_KIND_STATE.get(kind):errors.append('state')
 session_id=env.get('runtime_session_id')
 if not isinstance(session_id,str) or not session_id:errors.append('session')
 if env.get('egress_state')!='DASHBOARD_LOCKED' or not isinstance(env.get('egress_epoch'),int) or isinstance(env.get('egress_epoch'),bool) or env.get('egress_epoch',0)<1:errors.append('egress_binding')
 for key in ('single_human_egress','semantic_payload_inside_dashboard_only'):
  if env.get(key) is not True:errors.append(key)
 for key in ('raw_model_tokens_visible','parallel_human_message_allowed'):
  if env.get(key) is not False:errors.append(key)
 if env.get('presentation_is_not_authorization') is not True:errors.append('presentation_authority')
 if env.get('epistemic_authority') not in {0,0.0} or env.get('execution_authority') not in {0,0.0}:errors.append('authority')
 p=env.get('payload')
 if not isinstance(p,dict) or set(p)!=set(_PAYLOAD_KEYS):errors.append('payload_shape');p=p if isinstance(p,dict) else {}
 active=[k for k in _PAYLOAD_KEYS if p.get(k) is not None]
 expected={'TURN':'surface_turn','NOTICE':'notice','INITIALIZE':'notice','RESUME':'notice','APPROVAL_REQUEST':'approval_request','PROGRESS':'progress','ERROR':'error','DEGRADED':'degraded','RECOVERY':'recovery','EXIT':'release'}.get(kind)
 if expected:
  if active!=[expected]:errors.append('payload_exclusivity')
 elif active:errors.append('unexpected_payload')
 if kind=='TURN':
  t=p.get('surface_turn') if isinstance(p.get('surface_turn'),dict) else {}
  if t.get('surface_a_inside_dashboard') is not True or t.get('surface_b_bound') is not True:errors.append('turn_binding')
  if not isinstance(t.get('cycle_id'),str) or not t.get('cycle_id') or env.get('cycle_id')!=t.get('cycle_id'):errors.append('turn_cycle')
  for key in ('surface_a_sha256','surface_b_json_sha256','surface_b_docx_sha256'):
   if not isinstance(t.get(key),str) or not _SHA256_RE.fullmatch(t.get(key)):errors.append('turn_'+key)
 elif kind in {'NOTICE','INITIALIZE','RESUME'}:
  n=p.get('notice') if isinstance(p.get('notice'),dict) else {}
  if not _valid_bounded_text(n.get('message'),MAX_MESSAGE_BYTES):errors.append('notice_message')
  if n.get('authority_effect')!='NONE':errors.append('notice_authority')
 elif kind=='APPROVAL_REQUEST':
  a=p.get('approval_request') if isinstance(p.get('approval_request'),dict) else {}
  if a.get('human_frame_schema')!='ikant-human-frame/v0.19-test' or not isinstance(a.get('frame_sha256'),str) or not _SHA256_RE.fullmatch(a.get('frame_sha256')):errors.append('approval_frame')
  if a.get('session_id')!=session_id or not isinstance(a.get('actor_binding_id'),str) or not a.get('actor_binding_id'):errors.append('approval_session_binding')
  if a.get('purpose') not in {'CAPABILITY_GRANT','CAPABILITY_REVOKE','ACTION_CONFIRMATION'}:errors.append('approval_purpose')
  if not _valid_bounded_text(a.get('title'),1024) or not _valid_bounded_text(a.get('body'),MAX_MESSAGE_BYTES):errors.append('approval_text')
  ents=a.get('requested_entitlements')
  try:
   canonical=[{'capability':c,'resource':r} for c,r in normalize_entitlements(ents or [])]
   if not isinstance(ents,list) or ents!=canonical:errors.append('approval_entitlements')
  except (TypeError,ValueError):errors.append('approval_entitlements')
  if a.get('requires_explicit_decision') is not True or a.get('presentation_is_not_authorization') is not True or a.get('decision_recorded') is not False or a.get('grant_issued') is not False:errors.append('approval_boundary')
  if a.get('epistemic_authority') not in {0,0.0} or a.get('execution_authority') not in {0,0.0}:errors.append('approval_authority')
 elif kind=='PROGRESS':
  x=p.get('progress') if isinstance(p.get('progress'),dict) else {};fraction=x.get('fraction')
  if not _valid_bounded_text(x.get('phase'),128) or not _valid_bounded_text(x.get('label'),MAX_PROGRESS_LABEL_BYTES):errors.append('progress_text')
  if fraction is not None and (not isinstance(fraction,(int,float)) or isinstance(fraction,bool) or not math.isfinite(float(fraction)) or float(fraction)<0 or float(fraction)>1):errors.append('progress_fraction')
  if not isinstance(x.get('cancellable'),bool):errors.append('progress_cancellable')
  if x.get('authority_effect')!='NONE':errors.append('progress_authority')
 elif kind=='ERROR':
  x=p.get('error') if isinstance(p.get('error'),dict) else {}
  if not _valid_bounded_text(x.get('code'),128) or not _valid_bounded_text(x.get('message'),MAX_MESSAGE_BYTES):errors.append('error_text')
  if not isinstance(x.get('retryable'),bool):errors.append('error_retryable')
  if x.get('authority_effect')!='NONE':errors.append('error_authority')
 elif kind=='DEGRADED':
  x=p.get('degraded') if isinstance(p.get('degraded'),dict) else {};loss=x.get('capability_loss')
  malformed=not isinstance(loss,list) or any(not isinstance(v,str) for v in (loss if isinstance(loss,list) else []))
  if malformed:errors.append('degraded_capability_loss')
  else:
   if loss!=sorted(set(loss)) or any(not _valid_bounded_text(v,256) for v in loss):errors.append('degraded_capability_loss')
  if not _valid_bounded_text(x.get('code'),128) or not _valid_bounded_text(x.get('message'),MAX_MESSAGE_BYTES):errors.append('degraded_text')
  if x.get('authority_effect')!='NONE':errors.append('degraded_authority')
 elif kind=='RECOVERY':
  x=p.get('recovery') if isinstance(p.get('recovery'),dict) else {}
  if not _valid_bounded_text(x.get('reason'),MAX_MESSAGE_BYTES) or x.get('replay_only') is not True or x.get('authority_effect')!='NONE':errors.append('recovery_boundary')
 elif kind=='EXIT':
  x=p.get('release') if isinstance(p.get('release'),dict) else {}
  if x.get('command')!='EXIT IKANT' or x.get('release_after_frame') is not True or x.get('authority_effect')!='NONE' or not _valid_bounded_text(x.get('message'),MAX_MESSAGE_BYTES):errors.append('exit_release')
 try:
  supplied=env.pop('sha256',None)
  if supplied!=_digest(env):errors.append('digest')
 except (TypeError,ValueError):errors.append('canonical_json')
 return not errors,list(dict.fromkeys(errors))
