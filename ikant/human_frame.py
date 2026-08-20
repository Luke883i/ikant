from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib,hmac,json,re,secrets
from typing import Any,Iterable

HUMAN_FRAME_SCHEMA='ikant-human-frame/v0.19-test'
ACTOR_BINDING_SCHEMA='ikant-actor-session-binding/v0.19-test'
INTERACTION_RECEIPT_SCHEMA='ikant-human-interaction-receipt/v0.19-test'
_ALLOWED_PURPOSES=frozenset({'NOTICE','CAPABILITY_GRANT','CAPABILITY_REVOKE','ACTION_CONFIRMATION'})
_ALLOWED_DECISIONS=frozenset({'ACK','APPROVE','DENY','REVOKE'})
_CAP_RE=re.compile(r'^[a-z][a-z0-9_.:-]{0,79}$')
_RES_RE=re.compile(r'^[a-z][a-z0-9+.-]{0,31}:[^\x00-\x20\x7f*]{1,512}$')

def _canonical(payload:dict[str,Any])->bytes:
    return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def digest(payload:dict[str,Any])->str:return hashlib.sha256(_canonical(payload)).hexdigest()
def _mac(secret:bytes,payload:dict[str,Any])->str:return hmac.new(secret,_canonical(payload),hashlib.sha256).hexdigest()

def normalize_capability(value:object)->str:
    cap=str(value or '').strip().casefold()
    if '*' in cap or not _CAP_RE.fullmatch(cap):raise ValueError('invalid or wildcard capability')
    return cap

def normalize_resource(value:object)->str:
    raw=str(value or '').strip()
    if '*' in raw or not _RES_RE.fullmatch(raw):raise ValueError('invalid or wildcard resource')
    scheme,rest=raw.split(':',1)
    if '/..' in rest or rest.endswith('/..') or '/../' in rest:raise ValueError('resource traversal segment forbidden')
    return scheme.casefold()+':'+rest

def normalize_entitlements(values:Iterable[tuple[object,object]|list[object]|dict[str,object]])->tuple[tuple[str,str],...]:
    out=set()
    for item in values:
        if isinstance(item,dict): cap,res=item.get('capability'),item.get('resource')
        else:
            if len(item)!=2:raise ValueError('entitlement requires capability and resource')
            cap,res=item[0],item[1]
        out.add((normalize_capability(cap),normalize_resource(res)))
    return tuple(sorted(out))

@dataclass(frozen=True)
class ActorSessionBinding:
    schema:str;session_id:str;channel_id:str;binding_id:str;channel_authenticated:bool;human_identity_proven:bool;epistemic_authority:float;execution_authority:float

def build_actor_binding(*,session_id:str,channel_id:str,secret:bytes)->ActorSessionBinding:
    if not str(session_id).strip() or not str(channel_id).strip():raise ValueError('session_id and channel_id required')
    if not isinstance(secret,(bytes,bytearray)) or len(secret)<32:raise ValueError('interaction secret must be at least 32 bytes')
    material={'schema':ACTOR_BINDING_SCHEMA,'session_id':str(session_id),'channel_id':str(channel_id)}
    binding_id='ab-'+hmac.new(bytes(secret),_canonical(material),hashlib.sha256).hexdigest()[:32]
    return ActorSessionBinding(ACTOR_BINDING_SCHEMA,str(session_id),str(channel_id),binding_id,True,False,0.0,0.0)

def build_human_frame(*,session_id:str,actor_binding_id:str,frame_seq:int,purpose:str,title:str,body:str,entitlements=(),cycle_id:str|None=None,action_fingerprint:str|None=None,handoff_id:str|None=None,subject_id:str|None=None,max_uses:int=1,expires_at:float|None=None,nonce:str|None=None)->dict[str,Any]:
    p=str(purpose or '').upper()
    if p not in _ALLOWED_PURPOSES:raise ValueError('unsupported human frame purpose')
    if int(frame_seq)<1:raise ValueError('frame_seq must be positive')
    if not str(session_id) or not str(actor_binding_id):raise ValueError('frame session/binding required')
    ents=normalize_entitlements(entitlements)
    if p=='CAPABILITY_GRANT' and not ents:raise ValueError('capability grant frame requires entitlements')
    if p!='CAPABILITY_GRANT' and ents:raise ValueError('entitlements only allowed on capability grant frame')
    if int(max_uses)<1 or int(max_uses)>1000:raise ValueError('max_uses out of range')
    payload={'schema':HUMAN_FRAME_SCHEMA,'session_id':str(session_id),'actor_binding_id':str(actor_binding_id),'frame_seq':int(frame_seq),'frame_nonce':str(nonce or secrets.token_hex(16)),'purpose':p,'title':str(title),'body':str(body),'cycle_id':None if cycle_id is None else str(cycle_id),'action_fingerprint':None if action_fingerprint is None else str(action_fingerprint),'handoff_id':None if handoff_id is None else str(handoff_id),'subject_id':None if subject_id is None else str(subject_id),'requested_entitlements':[{'capability':c,'resource':r} for c,r in ents],'max_uses':int(max_uses),'expires_at':None if expires_at is None else float(expires_at),'authority_effect':'NONE','presentation_is_not_authorization':True,'requires_explicit_decision':p in {'CAPABILITY_GRANT','CAPABILITY_REVOKE','ACTION_CONFIRMATION'},'epistemic_authority':0.0,'execution_authority':0.0}
    payload['sha256']=digest(payload);return payload

def validate_human_frame(frame:dict[str,Any])->tuple[bool,list[str]]:
    raw=dict(frame or {});e=[]
    if raw.get('schema')!=HUMAN_FRAME_SCHEMA:e.append('frame schema')
    if raw.get('purpose') not in _ALLOWED_PURPOSES:e.append('frame purpose')
    if not str(raw.get('session_id') or ''):e.append('frame session')
    if not str(raw.get('actor_binding_id') or ''):e.append('frame binding')
    if not isinstance(raw.get('frame_seq'),int) or raw.get('frame_seq',0)<1:e.append('frame seq')
    try:ents=normalize_entitlements(raw.get('requested_entitlements',[]) or [])
    except (ValueError,TypeError):e.append('frame entitlements');ents=()
    canonical=[{'capability':c,'resource':r} for c,r in ents]
    if raw.get('requested_entitlements',[])!=canonical:e.append('frame entitlement canonicalization')
    if raw.get('purpose')=='CAPABILITY_GRANT' and not ents:e.append('frame grant entitlements')
    if raw.get('purpose')!='CAPABILITY_GRANT' and ents:e.append('frame non-grant entitlements')
    if raw.get('authority_effect')!='NONE' or raw.get('presentation_is_not_authorization') is not True:e.append('frame authority claim')
    if raw.get('epistemic_authority') not in {0,0.0} or raw.get('execution_authority') not in {0,0.0}:e.append('frame authority')
    copy=dict(raw);actual=copy.pop('sha256',None)
    if actual!=digest(copy):e.append('frame digest')
    return not e,e

def issue_interaction_receipt(frame:dict[str,Any],*,binding:ActorSessionBinding,decision:str,secret:bytes,interaction_nonce:str|None=None)->dict[str,Any]:
    ok,errs=validate_human_frame(frame)
    if not ok:raise ValueError('invalid frame: '+'; '.join(errs))
    d=str(decision or '').upper()
    if d not in _ALLOWED_DECISIONS:raise ValueError('unsupported interaction decision')
    purpose=frame['purpose']
    allowed={'NOTICE':{'ACK'},'CAPABILITY_GRANT':{'APPROVE','DENY'},'CAPABILITY_REVOKE':{'REVOKE','DENY'},'ACTION_CONFIRMATION':{'APPROVE','DENY'}}[purpose]
    if d not in allowed:raise ValueError('decision incompatible with frame purpose')
    if binding.session_id!=frame['session_id'] or binding.binding_id!=frame['actor_binding_id']:raise ValueError('actor binding/frame mismatch')
    payload={'schema':INTERACTION_RECEIPT_SCHEMA,'session_id':frame['session_id'],'actor_binding_id':binding.binding_id,'frame_sha256':frame['sha256'],'frame_nonce':frame['frame_nonce'],'interaction_nonce':str(interaction_nonce or secrets.token_hex(16)),'decision':d,'channel_authenticated':True,'human_identity_proven':False,'grants_authority_by_itself':False,'epistemic_authority':0.0,'execution_authority':0.0}
    payload['mac_sha256']=_mac(bytes(secret),payload);return payload

def validate_interaction_receipt(frame:dict[str,Any],receipt:dict[str,Any],*,binding:ActorSessionBinding,secret:bytes)->tuple[bool,list[str]]:
    e=[];raw=dict(receipt or {})
    ok,fe=validate_human_frame(frame)
    if not ok:e.extend('frame:'+x for x in fe)
    if raw.get('schema')!=INTERACTION_RECEIPT_SCHEMA:e.append('receipt schema')
    if raw.get('session_id')!=frame.get('session_id') or raw.get('session_id')!=binding.session_id:e.append('receipt session')
    if raw.get('actor_binding_id')!=frame.get('actor_binding_id') or raw.get('actor_binding_id')!=binding.binding_id:e.append('receipt binding')
    if raw.get('frame_sha256')!=frame.get('sha256') or raw.get('frame_nonce')!=frame.get('frame_nonce'):e.append('receipt frame')
    if raw.get('channel_authenticated') is not True or raw.get('human_identity_proven') is not False:e.append('receipt actor claim')
    if raw.get('grants_authority_by_itself') is not False:e.append('receipt authority claim')
    if raw.get('epistemic_authority') not in {0,0.0} or raw.get('execution_authority') not in {0,0.0}:e.append('receipt authority')
    copy=dict(raw);actual=copy.pop('mac_sha256',None)
    if actual!=_mac(bytes(secret),copy):e.append('receipt mac')
    purpose=frame.get('purpose');allowed={'NOTICE':{'ACK'},'CAPABILITY_GRANT':{'APPROVE','DENY'},'CAPABILITY_REVOKE':{'REVOKE','DENY'},'ACTION_CONFIRMATION':{'APPROVE','DENY'}}.get(purpose,set())
    if raw.get('decision') not in allowed:e.append('receipt decision')
    return not e,e
