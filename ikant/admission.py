from __future__ import annotations
import hashlib,json,re,secrets,sys
from datetime import datetime,timezone
from pathlib import Path
from .store import atomic_json_write,read_json
from .pre_admission import ACCEPT,TERMS_PATH,policy_manifest

_NONCE_RE=re.compile(r'^[a-f0-9]{32}$')
def now():return datetime.now(timezone.utc).isoformat()
def digest(text):return hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()

def _contract_header(contract_text:str)->dict[str,str]:
 lines=contract_text.replace('\r\n','\n').splitlines()
 if not lines or lines[0].strip()!='---':return {}
 out={}
 for line in lines[1:]:
  if line.strip()=='---':break
  if ':' not in line:continue
  k,v=line.split(':',1);out[k.strip()]=v.strip()
 return out

def _v09(contract_text:str)->bool:return _contract_header(contract_text).get('contract_version')=='0.9.0'

def validate_repository_admission_policy(root,contract_text=None):
 root=Path(root);errs=[]
 try:b=json.loads((root/'BOOTSTRAP.json').read_text(encoding='utf-8'))
 except Exception:b={};errs.append('bootstrap manifest unreadable')
 try:a=json.loads((root/'ADMISSION.json').read_text(encoding='utf-8'))
 except Exception:a={};errs.append('admission manifest unreadable')
 expected=policy_manifest();forbidden=set(expected['forbidden_before_acceptance']);caps=expected['orientation_capsule']
 text=contract_text
 if text is None and (root/TERMS_PATH).exists():text=(root/TERMS_PATH).read_text(encoding='utf-8')
 h=_contract_header(text or '');version=h.get('contract_version','')
 if h.get('schema')!='ikant-access-contract/v0.9':errs.append('contract schema mismatch')
 if version!='0.9.0':errs.append('contract version mismatch')
 if h.get('admission_policy_schema')!=expected['schema']:errs.append('contract admission policy schema mismatch')
 required_header={
  'pre_acceptance_default':'DENY','terms_envelope_path':TERMS_PATH,
  'orientation_capsule_enabled':'true','orientation_capsule_paths':'|'.join(caps['paths']),
  'orientation_max_file_reads':str(caps['max_file_reads']),'orientation_max_total_bytes':str(caps['max_total_bytes']),
  'orientation_max_metadata_reads':str(caps['max_metadata_reads']),'freeze_after_terms_presentation':'true',
  'completed_access_accounting_required':'true','presented_terms_digest_handoff_required':'true',
  'repository_materialization_requires_acceptance':'true','completed_forbidden_access_is_nonretroactive':'true',
  'incidental_unexposed_overfetch_is_quarantined':'true','active_dashboard_egress_lock_required':'true',
  'exit_command':'EXIT IKANT','resume_command':'RESUME IKANT'}
 for k,v in required_header.items():
  if h.get(k)!=v:errs.append(f'contract header {k} mismatch')
 for name,m in [('bootstrap',b),('admission',a)]:
  f=m.get('pre_acceptance_firewall',{}) if isinstance(m,dict) else {}
  if m.get('contract_version')!=version:errs.append(f'{name} contract version mismatch')
  if f.get('schema')!=expected['schema']:errs.append(f'{name} firewall schema mismatch')
  if f.get('default')!='DENY':errs.append(f'{name} pre-acceptance default must be DENY')
  c=f.get('orientation_capsule',{})
  if c.get('paths')!=caps['paths']:errs.append(f'{name} orientation paths mismatch')
  if c.get('metadata_fields')!=caps['metadata_fields']:errs.append(f'{name} orientation metadata fields mismatch')
  for k in ('max_file_reads','max_total_bytes','max_metadata_reads','single_fetch_per_path','tree_search_history_source_allowed'):
   if c.get(k)!=caps[k]:errs.append(f'{name} orientation {k} mismatch')
  if f.get('freeze_after_terms_presentation') is not True:errs.append(f'{name} freeze-after-terms mismatch')
  if f.get('completed_access_accounting_required') is not True:errs.append(f'{name} completed-access accounting mismatch')
  if f.get('presented_terms_digest_handoff_required') is not True:errs.append(f'{name} presented digest handoff mismatch')
  if sorted(f.get('cached_orientation_use_purposes',[]))!=expected['cached_orientation_use_purposes']:errs.append(f'{name} cached orientation purposes mismatch')
  if f.get('repository_materialization_requires_acceptance') is not True:errs.append(f'{name} materialization gate mismatch')
  if f.get('completed_forbidden_access_is_nonretroactive') is not True:errs.append(f'{name} breach semantics mismatch')
  if f.get('incidental_unexposed_overfetch_is_quarantined') is not True:errs.append(f'{name} overfetch quarantine mismatch')
  if set(f.get('forbidden_operations',[]))!=forbidden:errs.append(f'{name} forbidden operation set mismatch')
 if b.get('terms_envelope_path')!=TERMS_PATH:errs.append('bootstrap terms envelope path mismatch')
 if a.get('contract_path')!=TERMS_PATH:errs.append('admission contract path mismatch')
 if a.get('acceptance_phrase')!=ACCEPT or a.get('current_session_required') is not True:errs.append('admission exact current-session acceptance mismatch')
 required_states=['DISCOVERED','ORIENTING','AWAITING_ACCEPTANCE','ACCEPTED','MATERIALIZED','PROBED','INITIALIZING','ACTIVE']
 if a.get('state_machine')!=required_states:errs.append('admission state machine mismatch')
 if a.get('decline_state')!='DECLINED' or a.get('decline_recovery')!='re-present_cached_terms':errs.append('admission decline semantics mismatch')
 if a.get('breach_state')!='BREACHED' or a.get('breach_recovery')!='fresh_admission_context_only':errs.append('admission breach semantics mismatch')
 if a.get('denial_receipt_schema')!=expected['denial_receipt_schema']:errs.append('admission denial receipt schema mismatch')
 e=a.get('active_human_egress',{})
 expected_egress={'schema':'ikant-dashboard-session-egress/v0.9-test','initial_state':'DASHBOARD_LOCKED','exclusive_human_output':True,'canonical_frame_only':True,'candidate_exact_byte_match_required':True,'exit_command':'EXIT IKANT','resume_command':'RESUME IKANT','breach_state':'EGRESS_BREACHED','resume_requires_runtime_integrity':True}
 for k,v in expected_egress.items():
  if e.get(k)!=v:errs.append(f'admission egress {k} mismatch')
 if e.get('release_path')!=['DASHBOARD_LOCKED','RELEASE_PENDING','RELEASED']:errs.append('admission egress release path mismatch')
 be=b.get('active_human_egress',{})
 if be.get('schema')!='ikant-dashboard-session-egress/v0.9-test' or be.get('exclusive') is not True:errs.append('bootstrap egress policy mismatch')
 if be.get('exit_command')!='EXIT IKANT' or be.get('resume_command')!='RESUME IKANT' or be.get('state_path')!='.ikant/egress.json':errs.append('bootstrap egress command/path mismatch')
 return not errs,list(dict.fromkeys(errs))

def issue_receipt(contract_text,user_message,*,presented_terms_sha256=None,actor_type='human',evidence_type='explicit_user_message'):
 if user_message!=ACCEPT:raise PermissionError('exact acceptance phrase required')
 if actor_type!='human' or evidence_type!='explicit_user_message':raise PermissionError('human explicit acceptance required')
 csha=digest(contract_text)
 if _v09(contract_text):
  if presented_terms_sha256 is None:raise PermissionError('presented terms digest handoff required')
  if presented_terms_sha256!=csha:raise PermissionError('presented/checkout contract digest mismatch')
 nonce=secrets.token_hex(16);accepted=now();esha=hashlib.sha256(user_message.encode()).hexdigest();schema='ikant-admission-receipt/v0.2' if presented_terms_sha256 else 'ikant-admission-receipt/v0.1';rid='ADM-'+hashlib.sha256(f'{csha}|{presented_terms_sha256 or ""}|{esha}|{accepted}|{nonce}'.encode()).hexdigest()[:16]
 out={'schema':schema,'receipt_id':rid,'contract_sha256':csha,'accepted_phrase':ACCEPT,'actor_type':actor_type,'evidence_type':evidence_type,'evidence_sha256':esha,'accepted_at':accepted,'nonce':nonce}
 if presented_terms_sha256:out['presented_terms_sha256']=presented_terms_sha256;out['binding']='presented_contract_digest'
 return out

def validate_receipt(r,contract_text):
 errs=[]
 if not r:errs.append('missing receipt')
 else:
  required_schema='ikant-admission-receipt/v0.2' if _v09(contract_text) else r.get('schema')
  if r.get('schema')!=required_schema:errs.append('receipt schema mismatch')
  csha=digest(contract_text)
  if r.get('contract_sha256')!=csha:errs.append('contract digest mismatch')
  presented=r.get('presented_terms_sha256')
  if _v09(contract_text) and presented!=csha:errs.append('presented terms digest binding mismatch')
  if r.get('accepted_phrase')!=ACCEPT or r.get('actor_type')!='human' or r.get('evidence_type')!='explicit_user_message':errs.append('acceptance binding mismatch')
  nonce=str(r.get('nonce',''))
  if not _NONCE_RE.fullmatch(nonce):errs.append('nonce invalid')
  expected_evidence=hashlib.sha256(ACCEPT.encode()).hexdigest()
  if r.get('evidence_sha256')!=expected_evidence:errs.append('acceptance evidence digest mismatch')
  accepted=str(r.get('accepted_at',''))
  if not accepted:errs.append('accepted_at missing')
  if not errs:
   expected_id='ADM-'+hashlib.sha256(f'{csha}|{presented or ""}|{expected_evidence}|{accepted}|{nonce}'.encode()).hexdigest()[:16]
   if r.get('receipt_id')!=expected_id:errs.append('receipt id mismatch')
 return not errs,list(dict.fromkeys(errs))
def state_dir(root):return Path(root)/'.ikant'
def save_receipt(sdir,r):atomic_json_write(Path(sdir)/'admission.json',r)
def load_receipt(sdir):return read_json(Path(sdir)/'admission.json')
def probe(root,sdir,contract_text):
 root=Path(root);sdir=Path(sdir);checks={}
 checks['PYTHON']={'status':'AVAILABLE' if sys.version_info>=(3,11) else 'UNAVAILABLE','detail':sys.version.split()[0]}
 checks['CONTRACT']={'status':'AVAILABLE' if (root/TERMS_PATH).exists() and digest((root/TERMS_PATH).read_text())==digest(contract_text) else 'UNAVAILABLE'}
 receipt_ok,receipt_errors=validate_receipt(load_receipt(sdir),contract_text)
 checks['ACCEPTANCE_BINDING']={'status':'AVAILABLE' if receipt_ok else 'UNAVAILABLE','detail':'; '.join(receipt_errors)}
 policy_ok,policy_errors=validate_repository_admission_policy(root,contract_text)
 checks['ADMISSION_POLICY']={'status':'AVAILABLE' if policy_ok else 'UNAVAILABLE','detail':'; '.join(policy_errors)}
 try:
  sdir.mkdir(parents=True,exist_ok=True);p=sdir/'probe-scratch';p.write_text('ok');ok=p.read_text()=='ok';p.unlink();checks['LOCAL_PERSISTENCE']={'status':'AVAILABLE' if ok else 'UNAVAILABLE'}
 except OSError as e:checks['LOCAL_PERSISTENCE']={'status':'UNAVAILABLE','detail':str(e)}
 checks['PACKAGE_LAYOUT']={'status':'AVAILABLE' if (root/'ikant'/'runtime.py').exists() else 'UNAVAILABLE'}
 overall='READY' if all(x['status']=='AVAILABLE' for x in checks.values()) else 'BLOCKED';pid='PRB-'+secrets.token_hex(8)
 return {'schema':'ikant-probe/v0.2','probe_id':pid,'at':now(),'overall':overall,'checks':checks,'contract_sha256':digest(contract_text),'consumed':False}
def save_probe(sdir,p):atomic_json_write(Path(sdir)/'probe.json',p)
def load_probe(sdir):return read_json(Path(sdir)/'probe.json')
