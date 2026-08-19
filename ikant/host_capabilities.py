from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,re
from typing import Any

HOST_CAPABILITY_SCHEMA='ikant-host-capability-manifest/v0.18-test'
CAPABILITIES=frozenset({
'human.whole_message_write','human.partial_write_detection','human.flush_failure_detection',
'machine.file_only_output','machine.human_channel_separation','machine.stdout_alias_rejection',
'execution.exact_revalidation_binding','execution.zero_runtime_authority',
'compat.legacy_transport_attestation','control.receipt_integrity','control.config_binding'})
_CAP_RE=re.compile(r'^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$')

def digest(payload:dict[str,Any])->str:
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();return hashlib.sha256(raw).hexdigest()

def normalize_capability(value:str)->str:
    x=str(value or '').strip().lower()
    if '*' in x or not _CAP_RE.fullmatch(x) or x not in CAPABILITIES:raise ValueError('unsupported or wildcard host capability')
    return x

@dataclass(frozen=True)
class HostCapabilityManifest:
    schema:str;adapter_id:str;adapter_version:str;config_fingerprint:str;capabilities:tuple[str,...];declared_only:bool;epistemic_authority:float;execution_authority:float;actor_authenticated:bool;sha256:str

def build_manifest(*,adapter_id:str,adapter_version:str,config_fingerprint:str,capabilities)->HostCapabilityManifest:
    caps=tuple(sorted({normalize_capability(x) for x in capabilities}))
    p={'schema':HOST_CAPABILITY_SCHEMA,'adapter_id':str(adapter_id),'adapter_version':str(adapter_version),'config_fingerprint':str(config_fingerprint),'capabilities':caps,'declared_only':True,'epistemic_authority':0.0,'execution_authority':0.0,'actor_authenticated':False};p['sha256']=digest(p);return HostCapabilityManifest(**p)

def validate_manifest(value)->tuple[bool,list[str]]:
    raw=asdict(value) if isinstance(value,HostCapabilityManifest) else dict(value or {});e=[]
    if raw.get('schema')!=HOST_CAPABILITY_SCHEMA:e.append('manifest schema')
    if not str(raw.get('adapter_id') or ''):e.append('adapter id')
    if not str(raw.get('adapter_version') or ''):e.append('adapter version')
    if not str(raw.get('config_fingerprint') or ''):e.append('config fingerprint')
    try:caps=tuple(sorted({normalize_capability(x) for x in raw.get('capabilities',[]) or []}))
    except ValueError:e.append('capability');caps=()
    if tuple(raw.get('capabilities',()) or ())!=caps:e.append('capability canonicalization')
    if raw.get('declared_only') is not True:e.append('declaration boundary')
    if raw.get('epistemic_authority') not in {0,0.0}:e.append('epistemic authority')
    if raw.get('execution_authority') not in {0,0.0}:e.append('execution authority')
    if raw.get('actor_authenticated') is not False:e.append('actor authentication claim')
    copy=dict(raw);actual=copy.pop('sha256',None)
    if actual!=digest(copy):e.append('manifest digest')
    return not e,e
