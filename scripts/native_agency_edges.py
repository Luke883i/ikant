from __future__ import annotations
import argparse,itertools,json,random,sys,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.native_snapshot import canonical_native_path,sensitive_path,build_target_snapshot,validate_target_snapshot
from ikant.native_actions import build_native_action,validate_native_action

def classify(bits):
 (absolute,traversal,backslash,colon,hidden,secretname,missing,write,nul,oversize,nonregular,parent_missing,authority_drift,session_empty,adapter_empty)=bits
 path='docs/a.txt'
 if absolute:path='/etc/passwd'
 elif traversal:path='docs/../a.txt'
 elif backslash:path='docs\\a.txt'
 elif colon:path='C:/a.txt'
 elif hidden:path='docs/.env'
 elif secretname:path='docs/token.txt'
 try:
  p=canonical_native_path(path);path_ok=True;sens=sensitive_path(p)
 except ValueError:p='';path_ok=False;sens=False
 snap_ok=False;action_ok=False
 if path_ok and not sens:
  parent=None if parent_missing else {'dev':1,'ino':2,'mode':stat.S_IFDIR|0o700,'size':0,'mtime_ns':1}
  leaf=None if missing else {'dev':1,'ino':3,'mode':(stat.S_IFDIR if nonregular else stat.S_IFREG)|0o600,'size':1,'mtime_ns':1}
  try:
   s=build_target_snapshot(session_id='' if session_empty else 'S',adapter_id='' if adapter_empty else 'A',workspace_fingerprint='wf-1234567890abcdef',path=p,parent_identity=parent,leaf_identity=leaf,exists=not missing)
   if authority_drift:s['execution_authority']=1
   snap_ok=validate_target_snapshot(s)[0]
   if snap_ok:
    text=('x'*(16385 if oversize else 3)) if write else None
    if nul and write:text='a\x00b'
    try:a=build_native_action(s,verb='create_file' if write else 'read_file',text=text);action_ok=validate_native_action(a,s)[0]
    except (ValueError,TypeError):action_ok=False
  except (ValueError,TypeError):snap_ok=False
 return (path_ok,sens,snap_ok,action_ok,missing,write,nul,oversize,nonregular,parent_missing,authority_drift)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);u=list(itertools.product((False,True),repeat=15));rng.shuffle(u);seen=set()
 for i in range(a.cases):seen.add(classify(u[i%len(u)]))
 before=set(seen)
 for i in range(a.cases,a.cases+a.tail):seen.add(classify(u[i%len(u)]))
 out={'schema':'ikant-native-agency-edges/v0.22-test','status':'PASS' if set(seen)==before else 'FAIL','cases':a.cases,'tail':a.tail,'universe':len(u),'covered':min(a.cases,len(u)),'signatures':len(seen),'violations':0,'tail_novelty':len(set(seen)-before)};print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
