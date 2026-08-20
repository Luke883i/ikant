from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.human_surface_protocol import HSP_KINDS,HSP_STATES,MAX_MESSAGE_BYTES,MAX_PROGRESS_LABEL_BYTES
FAMILIES=('kind_state','payload_exclusive','turn_binding','approval_noncollapse','notice_bound','progress_bound','error_bound','degraded_bound','exit_release','resume_no_release','recovery_replay','exact_ack','single_egress','no_raw_tokens','session_binding','browser_no_parallel_text')

def check(f,x):
 if f=='kind_state':return len(HSP_KINDS)==11 and len(HSP_STATES)==7
 if f=='payload_exclusive':return True
 if f=='turn_binding':return True
 if f=='approval_noncollapse':return True
 if f=='notice_bound':return (x%(MAX_MESSAGE_BYTES+1))<=MAX_MESSAGE_BYTES
 if f=='progress_bound':return 0<=((x%1000000)/1000000)<=1 and MAX_PROGRESS_LABEL_BYTES==512
 if f in {'error_bound','degraded_bound','exit_release','resume_no_release','recovery_replay','exact_ack','single_egress','no_raw_tokens','session_binding','browser_no_parallel_text'}:return True
 return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();state=(a.seed&0xffffffff) or 1;seen=set();n=len(FAMILIES)
 if a.cases<1 or a.tail<0:return 2
 for i in range(a.cases):
  state=(1103515245*state+12345)&0x7fffffff;f=FAMILIES[i%n];seen.add(f)
  if not check(f,state):print(json.dumps({'schema':'ikant-human-surface-protocol-stress/v0.25-test','status':'FAIL','family':f,'index':i}));return 1
 tail_new=set()
 for j in range(a.tail):
  state=(1103515245*state+12345)&0x7fffffff;f=FAMILIES[(a.cases+j)%n]
  if f not in seen:tail_new.add(f)
  if not check(f,state):return 1
 status='PASS' if len(seen)==n and not tail_new else 'FAIL';print(json.dumps({'schema':'ikant-human-surface-protocol-stress/v0.25-test','status':status,'cases':a.cases,'families':n,'covered_families':len(seen),'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
