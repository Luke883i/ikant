from __future__ import annotations
import hashlib, json, secrets, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from .store import atomic_json_write, read_json
ACCEPT='I ACCEPT'
def now(): return datetime.now(timezone.utc).isoformat()
def digest(text): return hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()
def issue_receipt(contract_text,user_message,*,actor_type='human',evidence_type='explicit_user_message'):
    if user_message!=ACCEPT: raise PermissionError('exact acceptance phrase required')
    if actor_type!='human' or evidence_type!='explicit_user_message': raise PermissionError('human explicit acceptance required')
    nonce=secrets.token_hex(16); accepted=now(); csha=digest(contract_text); esha=hashlib.sha256(user_message.encode()).hexdigest(); rid='ADM-'+hashlib.sha256(f'{csha}|{esha}|{accepted}|{nonce}'.encode()).hexdigest()[:16]
    return {'schema':'ikant-admission-receipt/v0.1','receipt_id':rid,'contract_sha256':csha,'accepted_phrase':ACCEPT,'actor_type':actor_type,'evidence_type':evidence_type,'evidence_sha256':esha,'accepted_at':accepted,'nonce':nonce}
def validate_receipt(r,contract_text):
    errs=[]
    if not r: errs.append('missing receipt')
    else:
        if r.get('contract_sha256')!=digest(contract_text): errs.append('contract digest mismatch')
        if r.get('accepted_phrase')!=ACCEPT or r.get('actor_type')!='human' or r.get('evidence_type')!='explicit_user_message': errs.append('acceptance binding mismatch')
        if len(str(r.get('nonce','')))!=32: errs.append('nonce invalid')
    return not errs,errs
def state_dir(root):return Path(root)/'.ikant'
def save_receipt(sdir,r):atomic_json_write(Path(sdir)/'admission.json',r)
def load_receipt(sdir):return read_json(Path(sdir)/'admission.json')
def probe(root,sdir,contract_text):
    root=Path(root); sdir=Path(sdir); checks={}
    checks['PYTHON']={'status':'AVAILABLE' if sys.version_info>=(3,11) else 'UNAVAILABLE','detail':sys.version.split()[0]}
    checks['CONTRACT']={'status':'AVAILABLE' if (root/'IKANT_ACCESS_CONTRACT.md').exists() and digest((root/'IKANT_ACCESS_CONTRACT.md').read_text())==digest(contract_text) else 'UNAVAILABLE'}
    try:
        sdir.mkdir(parents=True,exist_ok=True); p=sdir/'probe-scratch'; p.write_text('ok'); ok=p.read_text()=='ok'; p.unlink(); checks['LOCAL_PERSISTENCE']={'status':'AVAILABLE' if ok else 'UNAVAILABLE'}
    except OSError as e: checks['LOCAL_PERSISTENCE']={'status':'UNAVAILABLE','detail':str(e)}
    checks['PACKAGE_LAYOUT']={'status':'AVAILABLE' if (root/'ikant'/'runtime.py').exists() else 'UNAVAILABLE'}
    overall='READY' if all(x['status']=='AVAILABLE' for x in checks.values()) else 'BLOCKED'; pid='PRB-'+secrets.token_hex(8)
    return {'schema':'ikant-probe/v0.1','probe_id':pid,'at':now(),'overall':overall,'checks':checks,'contract_sha256':digest(contract_text),'consumed':False}
def save_probe(sdir,p):atomic_json_write(Path(sdir)/'probe.json',p)
def load_probe(sdir):return read_json(Path(sdir)/'probe.json')
