from __future__ import annotations
import hashlib, json, os, stat, unicodedata
from typing import Any

NATIVE_TARGET_SCHEMA='ikant-native-target-snapshot/v0.22-test'
_MAX_PATH_BYTES=4096
_SENSITIVE_NAMES=frozenset({'.env','credentials','credentials.json','id_rsa','id_ed25519','known_hosts','authorized_keys'})
_SENSITIVE_SUFFIXES=('.pem','.key','.p12','.pfx','.kdbx')

def _canonical(payload:dict[str,Any])->bytes:
    return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def digest(payload:dict[str,Any])->str:return hashlib.sha256(_canonical(payload)).hexdigest()

def canonical_native_path(value:object)->str:
    raw=unicodedata.normalize('NFC',str(value or '').strip())
    if not raw or len(raw.encode('utf-8'))>_MAX_PATH_BYTES: raise ValueError('native path missing or too long')
    if raw.startswith('/') or raw.startswith('\\') or '\\' in raw or ':' in raw or '\x00' in raw: raise ValueError('native path must be canonical workspace-relative POSIX form')
    parts=raw.split('/')
    if any(not p or p in {'.','..'} for p in parts): raise ValueError('native path has empty/dot/traversal segment')
    if any(any(ord(ch)<32 or ord(ch)==127 for ch in p) for p in parts): raise ValueError('native path contains control bytes')
    return '/'.join(parts)

def sensitive_path(path:object)->bool:
    p=canonical_native_path(path); parts=[x.casefold() for x in p.split('/')]
    if any(x.startswith('.') for x in parts): return True
    leaf=parts[-1]
    if leaf in _SENSITIVE_NAMES or leaf.endswith(_SENSITIVE_SUFFIXES): return True
    return any(token in leaf for token in ('credential','secret','token'))

def stat_identity(st:os.stat_result|None)->dict[str,int]|None:
    if st is None:return None
    return {'dev':int(st.st_dev),'ino':int(st.st_ino),'mode':int(st.st_mode),'size':int(st.st_size),'mtime_ns':int(st.st_mtime_ns)}

def build_target_snapshot(*,session_id:str,adapter_id:str,workspace_fingerprint:str,path:str,parent_identity:dict[str,int],leaf_identity:dict[str,int]|None,exists:bool)->dict[str,Any]:
    p=canonical_native_path(path)
    if sensitive_path(p): raise ValueError('sensitive native path requires a future dedicated secret capability')
    if not str(session_id) or not str(adapter_id) or len(str(workspace_fingerprint))<16: raise ValueError('native snapshot identifiers required')
    if not isinstance(parent_identity,dict) or not parent_identity: raise ValueError('native parent identity required')
    if bool(exists)!=(leaf_identity is not None): raise ValueError('native leaf existence/identity mismatch')
    if leaf_identity is not None and not stat.S_ISREG(int(leaf_identity.get('mode',0))): raise ValueError('native target must be a regular file')
    payload={'schema':NATIVE_TARGET_SCHEMA,'session_id':str(session_id),'adapter_id':str(adapter_id),'workspace_fingerprint':str(workspace_fingerprint),'path':p,'exists':bool(exists),'parent_identity':dict(parent_identity),'leaf_identity':None if leaf_identity is None else dict(leaf_identity),'sensitive_path':False,'symlink_followed':False,'workspace_root_escaped':False,'epistemic_authority':0.0,'execution_authority':0.0}
    payload['sha256']=digest(payload);return payload

def validate_target_snapshot(snapshot:dict[str,Any])->tuple[bool,list[str]]:
    raw=dict(snapshot or {});e=[]
    if raw.get('schema')!=NATIVE_TARGET_SCHEMA:e.append('snapshot schema')
    try:p=canonical_native_path(raw.get('path'))
    except ValueError:e.append('snapshot path');p=''
    if p and raw.get('path')!=p:e.append('snapshot path canonicalization')
    if p:
        try:
            if sensitive_path(p):e.append('snapshot sensitive path')
        except ValueError:e.append('snapshot sensitive path')
    if not str(raw.get('session_id') or '') or not str(raw.get('adapter_id') or '') or len(str(raw.get('workspace_fingerprint') or ''))<16:e.append('snapshot identity')
    if raw.get('sensitive_path') is not False or raw.get('symlink_followed') is not False or raw.get('workspace_root_escaped') is not False:e.append('snapshot security boundary')
    exists=raw.get('exists') is True;leaf=raw.get('leaf_identity')
    if exists!=(leaf is not None):e.append('snapshot existence')
    if leaf is not None and (not isinstance(leaf,dict) or not stat.S_ISREG(int(leaf.get('mode',0)))):e.append('snapshot leaf kind')
    if not isinstance(raw.get('parent_identity'),dict) or not raw.get('parent_identity'):e.append('snapshot parent identity')
    if raw.get('epistemic_authority') not in {0,0.0} or raw.get('execution_authority') not in {0,0.0}:e.append('snapshot authority')
    material=dict(raw);actual=material.pop('sha256',None)
    if actual!=digest(material):e.append('snapshot digest')
    return not e,e
