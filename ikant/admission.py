from __future__ import annotations
import hashlib, json, re, secrets, sys
from datetime import datetime, timezone
from pathlib import Path
from .store import atomic_json_write, read_json
from .pre_admission import ACCEPT, TERMS_PATH, policy_manifest

_NONCE_RE=re.compile(r'^[a-f0-9]{32}$')
def now(): return datetime.now(timezone.utc).isoformat()
def digest(text): return hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()

def _contract_header(contract_text:str)->dict[str,str]:
    lines=contract_text.replace('\r\n','\n').splitlines()
    if not lines or lines[0].strip()!='---': return {}
    out={}
    for line in lines[1:]:
        if line.strip()=='---': break
        if ':' not in line: continue
        k,v=line.split(':',1);out[k.strip()]=v.strip()
    return out

def validate_repository_admission_policy(root, contract_text=None):
    root=Path(root); errs=[]
    try:b=json.loads((root/'BOOTSTRAP.json').read_text(encoding='utf-8'))
    except Exception: b={};errs.append('bootstrap manifest unreadable')
    try:a=json.loads((root/'ADMISSION.json').read_text(encoding='utf-8'))
    except Exception: a={};errs.append('admission manifest unreadable')
    if 'pre_admission_allowlist' in b or 'pre_admission_allowlist' in a: errs.append('legacy pre-admission allowlist forbidden')
    expected=policy_manifest(); forbidden=set(expected['forbidden_before_acceptance'])
    for name,m in [('bootstrap',b),('admission',a)]:
        f=m.get('pre_acceptance_firewall',{}) if isinstance(m,dict) else {}
        if f.get('schema')!=expected['schema']: errs.append(f'{name} firewall schema mismatch')
        if f.get('default')!='DENY': errs.append(f'{name} pre-acceptance default must be DENY')
        path=m.get('terms_envelope_path') if name=='bootstrap' else f.get('terms_envelope_path')
        if path!=TERMS_PATH: errs.append(f'{name} terms envelope path mismatch')
        if f.get('terms_envelope_only_repository_read_exception') is not True: errs.append(f'{name} terms envelope exception mismatch')
        if f.get('repository_materialization_requires_acceptance') is not True: errs.append(f'{name} materialization gate mismatch')
        if f.get('completed_pre_acceptance_breach_is_nonretroactive') is not True: errs.append(f'{name} breach semantics mismatch')
        if set(f.get('forbidden_operations',[]))!=forbidden: errs.append(f'{name} forbidden operation set mismatch')
    if a.get('acceptance_phrase')!=ACCEPT or a.get('current_session_required') is not True: errs.append('admission exact current-session acceptance mismatch')
    required_states=['DISCOVERED','TERMS_ENVELOPE','TERMS_PRESENTED','ACCEPTED','MATERIALIZED','PROBED','INITIALIZING','ACTIVE']
    if a.get('state_machine')!=required_states or a.get('breach_state')!='BREACHED': errs.append('admission state machine mismatch')
    text=contract_text
    if text is None and (root/TERMS_PATH).exists(): text=(root/TERMS_PATH).read_text(encoding='utf-8')
    h=_contract_header(text or '')
    required_header={
        'pre_acceptance_default':'DENY',
        'terms_envelope_path':TERMS_PATH,
        'terms_envelope_only_repository_read_exception':'true',
        'repository_materialization_requires_acceptance':'true',
        'completed_pre_acceptance_breach_is_nonretroactive':'true',
    }
    for k,v in required_header.items():
        if h.get(k)!=v: errs.append(f'contract header {k} mismatch')
    return not errs,list(dict.fromkeys(errs))

def issue_receipt(contract_text,user_message,*,actor_type='human',evidence_type='explicit_user_message'):
    if user_message!=ACCEPT: raise PermissionError('exact acceptance phrase required')
    if actor_type!='human' or evidence_type!='explicit_user_message': raise PermissionError('human explicit acceptance required')
    nonce=secrets.token_hex(16); accepted=now(); csha=digest(contract_text); esha=hashlib.sha256(user_message.encode()).hexdigest(); rid='ADM-'+hashlib.sha256(f'{csha}|{esha}|{accepted}|{nonce}'.encode()).hexdigest()[:16]
    return {'schema':'ikant-admission-receipt/v0.1','receipt_id':rid,'contract_sha256':csha,'accepted_phrase':ACCEPT,'actor_type':actor_type,'evidence_type':evidence_type,'evidence_sha256':esha,'accepted_at':accepted,'nonce':nonce}

def validate_receipt(r,contract_text):
    errs=[]
    if not r: errs.append('missing receipt')
    else:
        if r.get('schema')!='ikant-admission-receipt/v0.1': errs.append('receipt schema mismatch')
        csha=digest(contract_text)
        if r.get('contract_sha256')!=csha: errs.append('contract digest mismatch')
        if r.get('accepted_phrase')!=ACCEPT or r.get('actor_type')!='human' or r.get('evidence_type')!='explicit_user_message': errs.append('acceptance binding mismatch')
        nonce=str(r.get('nonce',''))
        if not _NONCE_RE.fullmatch(nonce): errs.append('nonce invalid')
        expected_evidence=hashlib.sha256(ACCEPT.encode()).hexdigest()
        if r.get('evidence_sha256')!=expected_evidence: errs.append('acceptance evidence digest mismatch')
        accepted=str(r.get('accepted_at',''))
        if not accepted: errs.append('accepted_at missing')
        if not errs:
            expected_id='ADM-'+hashlib.sha256(f'{csha}|{expected_evidence}|{accepted}|{nonce}'.encode()).hexdigest()[:16]
            if r.get('receipt_id')!=expected_id: errs.append('receipt id mismatch')
    return not errs,list(dict.fromkeys(errs))
def state_dir(root):return Path(root)/'.ikant'
def save_receipt(sdir,r):atomic_json_write(Path(sdir)/'admission.json',r)
def load_receipt(sdir):return read_json(Path(sdir)/'admission.json')
def probe(root,sdir,contract_text):
    root=Path(root); sdir=Path(sdir); checks={}
    checks['PYTHON']={'status':'AVAILABLE' if sys.version_info>=(3,11) else 'UNAVAILABLE','detail':sys.version.split()[0]}
    checks['CONTRACT']={'status':'AVAILABLE' if (root/TERMS_PATH).exists() and digest((root/TERMS_PATH).read_text())==digest(contract_text) else 'UNAVAILABLE'}
    policy_ok,policy_errors=validate_repository_admission_policy(root,contract_text)
    checks['ADMISSION_POLICY']={'status':'AVAILABLE' if policy_ok else 'UNAVAILABLE','detail':'; '.join(policy_errors)}
    try:
        sdir.mkdir(parents=True,exist_ok=True); p=sdir/'probe-scratch'; p.write_text('ok'); ok=p.read_text()=='ok'; p.unlink(); checks['LOCAL_PERSISTENCE']={'status':'AVAILABLE' if ok else 'UNAVAILABLE'}
    except OSError as e: checks['LOCAL_PERSISTENCE']={'status':'UNAVAILABLE','detail':str(e)}
    checks['PACKAGE_LAYOUT']={'status':'AVAILABLE' if (root/'ikant'/'runtime.py').exists() else 'UNAVAILABLE'}
    overall='READY' if all(x['status']=='AVAILABLE' for x in checks.values()) else 'BLOCKED'; pid='PRB-'+secrets.token_hex(8)
    return {'schema':'ikant-probe/v0.1','probe_id':pid,'at':now(),'overall':overall,'checks':checks,'contract_sha256':digest(contract_text),'consumed':False}
def save_probe(sdir,p):atomic_json_write(Path(sdir)/'probe.json',p)
def load_probe(sdir):return read_json(Path(sdir)/'probe.json')
