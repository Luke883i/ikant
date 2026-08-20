from __future__ import annotations
import hashlib,json
from typing import Any
from .human_frame import normalize_capability,normalize_resource
from .native_snapshot import validate_target_snapshot

NATIVE_ACTION_SCHEMA='ikant-native-action/v0.22-test'
_ALLOWED={'READ_FILE':'native.fs.read','CREATE_FILE':'native.fs.create'}
_MAX_CREATE_BYTES=16*1024

def _canonical(p):return json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def _digest(p):return hashlib.sha256(_canonical(p)).hexdigest()
def _sha(s:str):return hashlib.sha256(s.encode('utf-8')).hexdigest()

def build_native_action(snapshot:dict[str,Any],*,verb:str,text:str|None=None)->dict[str,Any]:
    ok,e=validate_target_snapshot(snapshot)
    if not ok: raise ValueError('invalid native target snapshot: '+'; '.join(e))
    v=str(verb or '').upper();cap=_ALLOWED.get(v)
    if not cap: raise ValueError('unsupported native action verb')
    plaintext=None;content_sha=None
    if v=='READ_FILE':
        if text is not None: raise ValueError('read file does not accept content')
        if snapshot.get('exists') is not True: raise ValueError('read file target must exist')
    else:
        if snapshot.get('exists') is True: raise ValueError('S4 create target must be absent')
        plaintext=str(text if text is not None else '')
        if '\x00' in plaintext: raise ValueError('native text create forbids NUL')
        if len(plaintext.encode('utf-8'))>_MAX_CREATE_BYTES: raise ValueError('native create exceeds human-reviewable S4 bound')
        content_sha=_sha(plaintext)
    payload={'schema':NATIVE_ACTION_SCHEMA,'session_id':snapshot['session_id'],'adapter_id':snapshot['adapter_id'],'workspace_fingerprint':snapshot['workspace_fingerprint'],'target_snapshot_sha256':snapshot['sha256'],'verb':v,'capability':normalize_capability(cap),'path':snapshot['path'],'content_sha256':content_sha,'text_only':True,'shell_allowed':False,'process_execution_allowed':False,'environment_inherited':False,'follows_symlinks':False,'secret_access':False,'requires_s1_lease':True,'requires_fresh_host_revalidation':True,'epistemic_authority':0.0,'execution_authority':0.0}
    payload['sha256']=_digest(payload)
    if plaintext is not None:payload['text']=plaintext
    return payload

def bound_native_resource(action:dict[str,Any],envelope:dict[str,Any])->str:
    a=str(action.get('sha256') or '');h=str(envelope.get('handoff_id') or '');f=str(envelope.get('action_fingerprint') or '');i=str(envelope.get('idempotency_key') or '')
    if len(a)!=64 or not h or not f or not i:raise ValueError('native execution binding incomplete')
    return normalize_resource('native-action:'+a+'/'+h+'/af-'+_sha(f)+'/ik-'+_sha(i))

def required_entitlements(action:dict[str,Any],envelope:dict[str,Any])->tuple[tuple[str,str],...]:
    cap=normalize_capability(action.get('capability'))
    required=tuple(sorted({normalize_capability(x) for x in envelope.get('required_capabilities',[]) or []}))
    if required!=(cap,):raise ValueError('handoff required capabilities do not exactly bind native action')
    return ((cap,bound_native_resource(action,envelope)),)

def validate_native_action(action:dict[str,Any],snapshot:dict[str,Any])->tuple[bool,list[str]]:
    raw=dict(action or {});e=[];ok,se=validate_target_snapshot(snapshot)
    if not ok:e.extend('snapshot:'+x for x in se)
    if raw.get('schema')!=NATIVE_ACTION_SCHEMA:e.append('action schema')
    v=str(raw.get('verb') or '')
    if _ALLOWED.get(v)!=raw.get('capability'):e.append('action capability')
    for k in ('session_id','adapter_id','workspace_fingerprint'):
        if raw.get(k)!=snapshot.get(k):e.append('action '+k)
    if raw.get('target_snapshot_sha256')!=snapshot.get('sha256') or raw.get('path')!=snapshot.get('path'):e.append('action target binding')
    if raw.get('text_only') is not True or raw.get('shell_allowed') is not False or raw.get('process_execution_allowed') is not False or raw.get('environment_inherited') is not False or raw.get('follows_symlinks') is not False or raw.get('secret_access') is not False:e.append('action native security boundary')
    if raw.get('requires_s1_lease') is not True or raw.get('requires_fresh_host_revalidation') is not True:e.append('action governance')
    if raw.get('epistemic_authority') not in {0,0.0} or raw.get('execution_authority') not in {0,0.0}:e.append('action authority')
    if v=='READ_FILE':
        if snapshot.get('exists') is not True:e.append('action read missing target')
        if raw.get('content_sha256') is not None or 'text' in raw:e.append('action read shape')
    elif v=='CREATE_FILE':
        if snapshot.get('exists') is True:e.append('action create existing target')
        text=raw.get('text')
        if not isinstance(text,str) or '\x00' in text or len(text.encode('utf-8'))>_MAX_CREATE_BYTES:e.append('action create text')
        expected=_sha(text) if isinstance(text,str) else None
        if raw.get('content_sha256')!=expected:e.append('action create digest')
    material={k:v for k,v in raw.items() if k not in {'sha256','text'}}
    if raw.get('sha256')!=_digest(material):e.append('action digest')
    return not e,e
