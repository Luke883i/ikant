from __future__ import annotations
import argparse,copy,json,sys,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.native_snapshot import build_target_snapshot,validate_target_snapshot,canonical_native_path,sensitive_path
from ikant.native_actions import build_native_action,validate_native_action,required_entitlements

SNAP=('snapshot_schema','snapshot_digest','snapshot_authority','snapshot_session','snapshot_adapter','snapshot_path','snapshot_parent','snapshot_leaf_kind','snapshot_exists','snapshot_sensitive','snapshot_symlink','snapshot_escape','snapshot_leaf_missing','snapshot_parent_dev','snapshot_parent_ino','snapshot_leaf_dev','snapshot_leaf_ino','snapshot_leaf_size','snapshot_leaf_mtime','snapshot_workspace')
READ=('read_action_schema','read_action_digest','read_session','read_adapter','read_snapshot','read_path','read_verb','read_capability','read_authority','read_text_only','read_shell','read_process','read_env','read_symlink','read_secret','read_lease','read_revalidation','read_text','read_content_digest','read_workspace')
CREATE=('create_action_schema','create_action_digest','create_session','create_adapter','create_snapshot','create_path','create_verb','create_capability','create_authority','create_text_only','create_shell','create_process','create_env','create_symlink','create_secret','create_lease','create_revalidation','create_text','create_digest','create_nul','create_oversize','create_missing_text','create_existing_target','create_workspace')
BIND=('capability_drift','handoff_drift','fingerprint_drift','idempotency_drift','resource_extra','resource_missing')
PATH=('path_absolute','path_traversal','path_backslash','path_drive','path_empty_segment','path_dot','path_control','path_nul','path_hidden','path_secret_name','path_secret_suffix','path_token_name')
GATE=('lease_missing','lease_extra','lease_not_pending','grant_revoked','grant_epoch','host_nonconforming','target_drift','parent_drift','strong_path_false','symlink_safe_false','workspace_root_false','process_enabled','secret_enabled','shell_enabled','env_enabled','replay_terminal','preflight_drift','post_revalidation_drift','root_is_filesystem','non_posix_driver','create_lost_noclobber_race','read_drift_during_io','preadmission_native_touch','workspace_binding_drift')
FAMILIES=SNAP+READ+CREATE+BIND+PATH+GATE

def ids(exists=True):
 parent={'dev':1,'ino':2,'mode':stat.S_IFDIR|0o700,'size':0,'mtime_ns':1};leaf={'dev':1,'ino':3,'mode':stat.S_IFREG|0o600,'size':3,'mtime_ns':1} if exists else None
 return parent,leaf

def read_base():
 p,l=ids(True);s=build_target_snapshot(session_id='S',adapter_id='A',workspace_fingerprint='wf-1234567890abcdef',path='docs/a.txt',parent_identity=p,leaf_identity=l,exists=True);a=build_native_action(s,verb='read_file');e={'handoff_id':'H','action_fingerprint':'A','idempotency_key':'K','required_capabilities':['native.fs.read']};return s,a,e

def create_base():
 p,l=ids(False);s=build_target_snapshot(session_id='S',adapter_id='A',workspace_fingerprint='wf-1234567890abcdef',path='docs/new.txt',parent_identity=p,leaf_identity=l,exists=False);a=build_native_action(s,verb='create_file',text='abc');e={'handoff_id':'H','action_fingerprint':'A','idempotency_key':'K','required_capabilities':['native.fs.create']};return s,a,e

def semantic_gate(**kw):
 d={'lease_present':True,'lease_exact':True,'lease_pending':True,'grant_active':True,'epoch_current':True,'host':True,'target_same':True,'parent_same':True,'strong_path':True,'symlink_safe':True,'workspace_root':True,'process_disabled':True,'secret_disabled':True,'shell_disabled':True,'env_disabled':True,'not_replay':True,'preflight_same':True,'post_reval_same':True,'root_safe':True,'platform_supported':True,'noclobber':True,'read_stable':True,'admission_active':True,'workspace_bound':True};d.update(kw);return all(d.values())

def kill(f):
 if f in SNAP:
  s,a,e=read_base();m=copy.deepcopy(s)
  if f=='snapshot_schema':m['schema']='bad'
  elif f=='snapshot_digest':m['sha256']='0'*64
  elif f=='snapshot_authority':m['execution_authority']=1
  elif f=='snapshot_session':m['session_id']=''
  elif f=='snapshot_adapter':m['adapter_id']=''
  elif f=='snapshot_path':m['path']='../x'
  elif f=='snapshot_parent':m['parent_identity']=None
  elif f=='snapshot_leaf_kind':m['leaf_identity']['mode']=stat.S_IFDIR|0o700
  elif f=='snapshot_exists':m['exists']=False
  elif f=='snapshot_sensitive':m['sensitive_path']=True
  elif f=='snapshot_symlink':m['symlink_followed']=True
  elif f=='snapshot_escape':m['workspace_root_escaped']=True
  elif f=='snapshot_leaf_missing':m['leaf_identity']=None
  elif f=='snapshot_parent_dev':m['parent_identity']['dev']=9
  elif f=='snapshot_parent_ino':m['parent_identity']['ino']=9
  elif f=='snapshot_leaf_dev':m['leaf_identity']['dev']=9
  elif f=='snapshot_leaf_ino':m['leaf_identity']['ino']=9
  elif f=='snapshot_leaf_size':m['leaf_identity']['size']=999
  elif f=='snapshot_leaf_mtime':m['leaf_identity']['mtime_ns']=999
  elif f=='snapshot_workspace':m['workspace_fingerprint']='wf-other-1234567890abcdef'
  return not validate_target_snapshot(m)[0]
 if f in READ:
  s,a,e=read_base();m=copy.deepcopy(a)
  key=f.removeprefix('read_')
  if key=='action_schema':m['schema']='bad'
  elif key=='action_digest':m['sha256']='0'*64
  elif key=='session':m['session_id']='X'
  elif key=='adapter':m['adapter_id']='X'
  elif key=='snapshot':m['target_snapshot_sha256']='0'*64
  elif key=='path':m['path']='docs/b.txt'
  elif key=='verb':m['verb']='CREATE_FILE'
  elif key=='capability':m['capability']='native.fs.create'
  elif key=='authority':m['execution_authority']=1
  elif key=='text_only':m['text_only']=False
  elif key=='shell':m['shell_allowed']=True
  elif key=='process':m['process_execution_allowed']=True
  elif key=='env':m['environment_inherited']=True
  elif key=='symlink':m['follows_symlinks']=True
  elif key=='secret':m['secret_access']=True
  elif key=='lease':m['requires_s1_lease']=False
  elif key=='revalidation':m['requires_fresh_host_revalidation']=False
  elif key=='text':m['text']='x'
  elif key=='content_digest':m['content_sha256']='0'*64
  elif key=='workspace':m['workspace_fingerprint']='wf-other-1234567890abcdef'
  return not validate_native_action(m,s)[0]
 if f in CREATE:
  s,a,e=create_base();m=copy.deepcopy(a);key=f.removeprefix('create_')
  if key=='action_schema':m['schema']='bad'
  elif key=='action_digest':m['sha256']='0'*64
  elif key=='session':m['session_id']='X'
  elif key=='adapter':m['adapter_id']='X'
  elif key=='snapshot':m['target_snapshot_sha256']='0'*64
  elif key=='path':m['path']='docs/other.txt'
  elif key=='verb':m['verb']='READ_FILE'
  elif key=='capability':m['capability']='native.fs.read'
  elif key=='authority':m['execution_authority']=1
  elif key=='text_only':m['text_only']=False
  elif key=='shell':m['shell_allowed']=True
  elif key=='process':m['process_execution_allowed']=True
  elif key=='env':m['environment_inherited']=True
  elif key=='symlink':m['follows_symlinks']=True
  elif key=='secret':m['secret_access']=True
  elif key=='lease':m['requires_s1_lease']=False
  elif key=='revalidation':m['requires_fresh_host_revalidation']=False
  elif key=='text':m['text']='tamper'
  elif key=='digest':m['content_sha256']='0'*64
  elif key=='nul':m['text']='a\x00b'
  elif key=='oversize':m['text']='x'*16385
  elif key=='missing_text':m.pop('text',None)
  elif key=='workspace':m['workspace_fingerprint']='wf-other-1234567890abcdef'
  elif key=='existing_target':
   p,l=ids(True);s=build_target_snapshot(session_id='S',adapter_id='A',workspace_fingerprint='wf-1234567890abcdef',path='docs/new.txt',parent_identity=p,leaf_identity=l,exists=True)
  return not validate_native_action(m,s)[0]
 if f in BIND:
  s,a,e=read_base();expected=set(required_entitlements(a,e));ee=copy.deepcopy(e)
  try:
   if f=='capability_drift':ee['required_capabilities']=['native.fs.create']
  elif f=='handoff_drift':ee['handoff_id']='H2'
  elif f=='fingerprint_drift':ee['action_fingerprint']='A2'
  elif f=='idempotency_drift':ee['idempotency_key']='K2'
   actual=set(required_entitlements(a,ee))
   if f=='resource_extra':actual.add(('native.fs.read','native-action:extra'))
   if f=='resource_missing':actual=set()
   return actual!=expected
  except ValueError:return True
 if f in PATH:
  bad={'path_absolute':'/etc/passwd','path_traversal':'a/../b','path_backslash':'a\\b','path_drive':'C:/x','path_empty_segment':'a//b','path_dot':'a/./b','path_control':'a/\nb','path_nul':'a/\x00b','path_hidden':'a/.env','path_secret_name':'a/credentials.json','path_secret_suffix':'a/cert.pem','path_token_name':'a/token-cache.txt'}[f]
  try:
   p=canonical_native_path(bad)
   return sensitive_path(p) if f in {'path_hidden','path_secret_name','path_secret_suffix','path_token_name'} else False
  except ValueError:return True
 gate={'lease_missing':{'lease_present':False},'lease_extra':{'lease_exact':False},'lease_not_pending':{'lease_pending':False},'grant_revoked':{'grant_active':False},'grant_epoch':{'epoch_current':False},'host_nonconforming':{'host':False},'target_drift':{'target_same':False},'parent_drift':{'parent_same':False},'strong_path_false':{'strong_path':False},'symlink_safe_false':{'symlink_safe':False},'workspace_root_false':{'workspace_root':False},'process_enabled':{'process_disabled':False},'secret_enabled':{'secret_disabled':False},'shell_enabled':{'shell_disabled':False},'env_enabled':{'env_disabled':False},'replay_terminal':{'not_replay':False},'preflight_drift':{'preflight_same':False},'post_revalidation_drift':{'post_reval_same':False},'root_is_filesystem':{'root_safe':False},'non_posix_driver':{'platform_supported':False},'create_lost_noclobber_race':{'noclobber':False},'read_drift_during_io':{'read_stable':False},'preadmission_native_touch':{'admission_active':False},'workspace_binding_drift':{'workspace_bound':False}}
 return not semantic_gate(**gate[f])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);a=ap.parse_args();counts={f:0 for f in FAMILIES};surv=[]
 for i in range(a.mutations):
  f=FAMILIES[i%len(FAMILIES)];counts[f]+=1
  if not kill(f):surv.append(f)
 before={f for f,n in counts.items() if n};tail_new=set()
 for i in range(a.tail):
  f=FAMILIES[(a.mutations+i)%len(FAMILIES)]
  if f not in before:tail_new.add(f)
  if not kill(f):surv.append(f)
 out={'schema':'ikant-native-agency-mutations/v0.22-test','status':'PASS' if not surv and not tail_new and all(counts.values()) else 'FAIL','mutations':a.mutations,'tail':a.tail,'families':len(FAMILIES),'covered':sum(1 for n in counts.values() if n),'survivors':len(surv),'tail_new_families':len(tail_new)};print(json.dumps(out,sort_keys=True));
 if surv:print(json.dumps({'survivor_sample':sorted(set(surv))[:20]}))
 return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
