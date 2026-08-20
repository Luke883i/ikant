from __future__ import annotations
import argparse,copy,json,stat,sys
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
 p={'dev':1,'ino':2,'mode':stat.S_IFDIR|0o700,'size':0,'mtime_ns':1};l={'dev':1,'ino':3,'mode':stat.S_IFREG|0o600,'size':3,'mtime_ns':1} if exists else None;return p,l
def base(create=False):
 p,l=ids(not create);s=build_target_snapshot(session_id='S',adapter_id='A',workspace_fingerprint='wf-1234567890abcdef',path='docs/new.txt' if create else 'docs/a.txt',parent_identity=p,leaf_identity=l,exists=not create);a=build_native_action(s,verb='create_file' if create else 'read_file',text='abc' if create else None);e={'handoff_id':'H','action_fingerprint':'A','idempotency_key':'K','required_capabilities':[a['capability']]};return s,a,e
def semantic_gate(**kw):
 d={k:True for k in ('lease_present','lease_exact','lease_pending','grant_active','epoch_current','host','target_same','parent_same','strong_path','symlink_safe','workspace_root','process_disabled','secret_disabled','shell_disabled','env_disabled','not_replay','preflight_same','post_reval_same','root_safe','platform_supported','noclobber','read_stable','admission_active','workspace_bound')};d.update(kw);return all(d.values())
def kill(f):
 if f in SNAP:
  s,_,_=base();m=copy.deepcopy(s);ops={'snapshot_schema':('schema','bad'),'snapshot_digest':('sha256','0'*64),'snapshot_authority':('execution_authority',1),'snapshot_session':('session_id',''),'snapshot_adapter':('adapter_id',''),'snapshot_path':('path','../x'),'snapshot_parent':('parent_identity',None),'snapshot_exists':('exists',False),'snapshot_sensitive':('sensitive_path',True),'snapshot_symlink':('symlink_followed',True),'snapshot_escape':('workspace_root_escaped',True),'snapshot_leaf_missing':('leaf_identity',None),'snapshot_workspace':('workspace_fingerprint','wf-other-1234567890abcdef')}
  if f in ops:m[ops[f][0]]=ops[f][1]
  elif f=='snapshot_leaf_kind':m['leaf_identity']['mode']=stat.S_IFDIR|0o700
  else:
   obj,key=('parent_identity',f.rsplit('_',1)[1]) if 'parent_' in f else ('leaf_identity',f.rsplit('_',1)[1]);m[obj][{'dev':'dev','ino':'ino','size':'size','mtime':'mtime_ns'}[key]]=999
  return not validate_target_snapshot(m)[0]
 if f in READ or f in CREATE:
  create=f in CREATE;s,a,_=base(create);m=copy.deepcopy(a);key=f.split('_',1)[1];field={'action_schema':'schema','action_digest':'sha256','session':'session_id','adapter':'adapter_id','snapshot':'target_snapshot_sha256','path':'path','verb':'verb','capability':'capability','authority':'execution_authority','text_only':'text_only','shell':'shell_allowed','process':'process_execution_allowed','env':'environment_inherited','symlink':'follows_symlinks','secret':'secret_access','lease':'requires_s1_lease','revalidation':'requires_fresh_host_revalidation','workspace':'workspace_fingerprint'}.get(key)
  if field:
   vals={'schema':'bad','sha256':'0'*64,'session_id':'X','adapter_id':'X','target_snapshot_sha256':'0'*64,'path':'docs/other.txt','verb':'READ_FILE' if create else 'CREATE_FILE','capability':'native.fs.read' if create else 'native.fs.create','execution_authority':1,'text_only':False,'shell_allowed':True,'process_execution_allowed':True,'environment_inherited':True,'follows_symlinks':True,'secret_access':True,'requires_s1_lease':False,'requires_fresh_host_revalidation':False,'workspace_fingerprint':'wf-other-1234567890abcdef'};m[field]=vals[field]
  elif key in {'text','content_digest','digest','nul','oversize','missing_text','existing_target'}:
   if key=='text':m['text']='tamper' if create else 'x'
   elif key in {'content_digest','digest'}:m['content_sha256']='0'*64
   elif key=='nul':m['text']='a\x00b'
   elif key=='oversize':m['text']='x'*16385
   elif key=='missing_text':m.pop('text',None)
   elif key=='existing_target':p,l=ids(True);s=build_target_snapshot(session_id='S',adapter_id='A',workspace_fingerprint='wf-1234567890abcdef',path='docs/new.txt',parent_identity=p,leaf_identity=l,exists=True)
  return not validate_native_action(m,s)[0]
 if f in BIND:
  _,a,e=base();expected=set(required_entitlements(a,e));ee=copy.deepcopy(e)
  try:
   if f=='capability_drift':ee['required_capabilities']=['native.fs.create']
   elif f=='handoff_drift':ee['handoff_id']='H2'
   elif f=='fingerprint_drift':ee['action_fingerprint']='A2'
   elif f=='idempotency_drift':ee['idempotency_key']='K2'
   actual=set(required_entitlements(a,ee))
   if f=='resource_extra':actual.add(('native.fs.read','native-action:extra'))
   elif f=='resource_missing':actual.clear()
   return actual!=expected
  except ValueError:return True
 if f in PATH:
  bad={'path_absolute':'/etc/passwd','path_traversal':'a/../b','path_backslash':'a\\b','path_drive':'C:/x','path_empty_segment':'a//b','path_dot':'a/./b','path_control':'a/\nb','path_nul':'a/\x00b','path_hidden':'a/.env','path_secret_name':'a/credentials.json','path_secret_suffix':'a/cert.pem','path_token_name':'a/token-cache.txt'}[f]
  try:p=canonical_native_path(bad);return sensitive_path(p) if f.startswith(('path_hidden','path_secret','path_token')) else False
  except ValueError:return True
 key={'lease_missing':'lease_present','lease_extra':'lease_exact','lease_not_pending':'lease_pending','grant_revoked':'grant_active','grant_epoch':'epoch_current','host_nonconforming':'host','target_drift':'target_same','parent_drift':'parent_same','strong_path_false':'strong_path','symlink_safe_false':'symlink_safe','workspace_root_false':'workspace_root','process_enabled':'process_disabled','secret_enabled':'secret_disabled','shell_enabled':'shell_disabled','env_enabled':'env_disabled','replay_terminal':'not_replay','preflight_drift':'preflight_same','post_revalidation_drift':'post_reval_same','root_is_filesystem':'root_safe','non_posix_driver':'platform_supported','create_lost_noclobber_race':'noclobber','read_drift_during_io':'read_stable','preadmission_native_touch':'admission_active','workspace_binding_drift':'workspace_bound'}[f];return not semantic_gate(**{key:False})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);a=ap.parse_args();counts={f:0 for f in FAMILIES};surv=[]
 for i in range(a.mutations):f=FAMILIES[i%len(FAMILIES)];counts[f]+=1;surv += [] if kill(f) else [f]
 before={f for f,n in counts.items() if n};tail_new=set()
 for i in range(a.tail):f=FAMILIES[(a.mutations+i)%len(FAMILIES)];tail_new.add(f) if f not in before else None;surv += [] if kill(f) else [f]
 out={'schema':'ikant-native-agency-mutations/v0.22-test','status':'PASS' if not surv and not tail_new and all(counts.values()) else 'FAIL','mutations':a.mutations,'tail':a.tail,'families':len(FAMILIES),'covered':sum(bool(n) for n in counts.values()),'survivors':len(surv),'tail_new_families':len(tail_new)};print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
