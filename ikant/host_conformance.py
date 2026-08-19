from __future__ import annotations
from dataclasses import asdict
import hashlib,json
from pathlib import Path
from typing import Any
from .host_capabilities import validate_manifest,digest

HOST_CONFORMANCE_SCHEMA='ikant-host-conformance-receipt/v0.18-test'
VECTOR_CAPABILITY={
'HUMAN_EXACT_WRITE':'human.whole_message_write','HUMAN_PARTIAL_REJECT':'human.partial_write_detection','HUMAN_FLUSH_REJECT':'human.flush_failure_detection',
'MACHINE_FILE_ONLY':'machine.file_only_output','MACHINE_CHANNEL_SEPARATE':'machine.human_channel_separation','MACHINE_STDOUT_REJECT':'machine.stdout_alias_rejection',
'EXEC_REVALIDATION_BIND':'execution.exact_revalidation_binding','EXEC_ZERO_AUTHORITY':'execution.zero_runtime_authority','LEGACY_ATTESTATION_VALID':'compat.legacy_transport_attestation',
'MANIFEST_INTEGRITY':'control.receipt_integrity','CONFIG_BOUND':'control.config_binding'}
REQUIRED_VECTORS={
'HUMAN_EGRESS':frozenset({'HUMAN_EXACT_WRITE','HUMAN_PARTIAL_REJECT','HUMAN_FLUSH_REJECT'}),
'MACHINE_OUTPUT':frozenset({'MACHINE_FILE_ONLY','MACHINE_CHANNEL_SEPARATE','MACHINE_STDOUT_REJECT'}),
'EXECUTION_HANDOFF':frozenset({'EXEC_REVALIDATION_BIND','EXEC_ZERO_AUTHORITY'}),
'BREACH_RESUME':frozenset({'HUMAN_EXACT_WRITE','HUMAN_PARTIAL_REJECT','HUMAN_FLUSH_REJECT','MACHINE_CHANNEL_SEPARATE','MACHINE_STDOUT_REJECT','LEGACY_ATTESTATION_VALID'}),
}

def _row(id,status,detail=''):return {'id':id,'status':status,'capability':VECTOR_CAPABILITY[id],'detail':detail,'epistemic_authority':0.0,'execution_authority':0.0}

def run_conformance(adapter)->dict[str,Any]:
    manifest=adapter.manifest();ok,errs=validate_manifest(manifest);rows=[]
    rows.append(_row('MANIFEST_INTEGRITY','PASS' if ok else 'FAIL',';'.join(errs)))
    rows.append(_row('CONFIG_BOUND','PASS' if bool(getattr(adapter,'config_fingerprint','')) else 'FAIL'))
    h=adapter.probe_human('normal');rows.append(_row('HUMAN_EXACT_WRITE','PASS' if h.get('accepted') and h.get('written')==len('frame-bytes') and h.get('value')=='frame-bytes' else 'FAIL'))
    p=adapter.probe_human('partial');rows.append(_row('HUMAN_PARTIAL_REJECT','PASS' if not p.get('accepted') else 'FAIL'))
    f=adapter.probe_human('flush_fail');rows.append(_row('HUMAN_FLUSH_REJECT','PASS' if not f.get('accepted') else 'FAIL'))
    mf=adapter.probe_machine('file');rows.append(_row('MACHINE_FILE_ONLY','PASS' if mf.get('accepted') and mf.get('exists') else 'FAIL'))
    aliases=[adapter.probe_machine(x) for x in ('stdout','stderr','-','/dev/stdout','/dev/stderr','')];alias_ok=all(not x.get('accepted') for x in aliases)
    rows.append(_row('MACHINE_STDOUT_REJECT','PASS' if alias_ok else 'FAIL'));rows.append(_row('MACHINE_CHANNEL_SEPARATE','PASS' if mf.get('accepted') and alias_ok else 'FAIL'))
    rv=adapter.probe_revalidation(False);dr=adapter.probe_revalidation(True);rows.append(_row('EXEC_REVALIDATION_BIND','PASS' if rv.get('accepted') and not dr.get('accepted') else 'FAIL'))
    receipt=rv.get('receipt') or {};zero=receipt.get('grants_runtime_execution_authority') is False and receipt.get('executes_action') is False;rows.append(_row('EXEC_ZERO_AUTHORITY','PASS' if zero else 'FAIL'))
    la=adapter.probe_legacy_attestation();rows.append(_row('LEGACY_ATTESTATION_VALID','PASS' if la.get('accepted') else 'FAIL'))
    vec={r['id']:r['status'] for r in rows};profiles={name:('PASS' if all(vec.get(v)=='PASS' for v in req) else 'FAIL') for name,req in REQUIRED_VECTORS.items()}
    raw_manifest=asdict(manifest);payload={'schema':HOST_CONFORMANCE_SCHEMA,'adapter_id':raw_manifest['adapter_id'],'adapter_version':raw_manifest['adapter_version'],'config_fingerprint':raw_manifest['config_fingerprint'],'manifest_sha256':raw_manifest['sha256'],'vectors':rows,'profiles':profiles,'overall_status':'PASS' if all(x=='PASS' for x in profiles.values()) else 'FAIL','epistemic_authority':0.0,'execution_authority':0.0,'actor_authenticated':False,'production_transport_attested':False,'digest_is_integrity_not_authentication':True,'tested_adapter_only':True};payload['sha256']=digest(payload);return payload

def validate_conformance_receipt(receipt,manifest)->tuple[bool,list[str]]:
    raw=dict(receipt or {});m=asdict(manifest) if hasattr(manifest,'__dataclass_fields__') else dict(manifest or {});e=[]
    if raw.get('schema')!=HOST_CONFORMANCE_SCHEMA:e.append('conformance schema')
    if raw.get('adapter_id')!=m.get('adapter_id'):e.append('adapter binding')
    if raw.get('adapter_version')!=m.get('adapter_version'):e.append('version binding')
    if raw.get('config_fingerprint')!=m.get('config_fingerprint'):e.append('config binding')
    if raw.get('manifest_sha256')!=m.get('sha256'):e.append('manifest binding')
    if raw.get('epistemic_authority') not in {0,0.0}:e.append('epistemic authority')
    if raw.get('execution_authority') not in {0,0.0}:e.append('execution authority')
    if raw.get('actor_authenticated') is not False:e.append('actor authentication claim')
    if raw.get('production_transport_attested') is not False:e.append('production transport claim')
    if raw.get('digest_is_integrity_not_authentication') is not True:e.append('digest boundary')
    if raw.get('tested_adapter_only') is not True:e.append('scope boundary')
    copy=dict(raw);actual=copy.pop('sha256',None)
    if actual!=digest(copy):e.append('conformance digest')
    ids=[x.get('id') for x in raw.get('vectors',[]) or []]
    if len(ids)!=len(set(ids)) or set(ids)!=set(VECTOR_CAPABILITY):e.append('vector set')
    for row in raw.get('vectors',[]) or []:
        if row.get('status') not in {'PASS','FAIL'}:e.append('vector status')
        if row.get('capability')!=VECTOR_CAPABILITY.get(row.get('id')):e.append('vector capability')
        if row.get('epistemic_authority') not in {0,0.0} or row.get('execution_authority') not in {0,0.0}:e.append('vector authority')
    expected={name:('PASS' if all(next((r.get('status') for r in raw.get('vectors',[]) if r.get('id')==v),None)=='PASS' for v in req) else 'FAIL') for name,req in REQUIRED_VECTORS.items()}
    if raw.get('profiles')!=expected:e.append('profile derivation')
    if raw.get('overall_status')!=('PASS' if all(x=='PASS' for x in expected.values()) else 'FAIL'):e.append('overall derivation')
    return not e,e
