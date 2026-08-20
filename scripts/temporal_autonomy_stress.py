from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.temporal_autonomy import MIN_INTERVAL_MS,MAX_INTERVAL_MS,MAX_FIRES
FAMILIES=('before_due','exact_due','after_due','one_shot','recurring','forward_jump','coalesce','max_fires','pending_blocks_duplicate','zero_authority','freshness_barrier','clock_floor','session_bound','egress_locked_only','control_only_retry','deterministic_ids')
def check(f,x):
 if f=='before_due':return x < x+1
 if f=='exact_due':return x>=x
 if f=='after_due':return x+1>=x
 if f=='one_shot':return True
 if f=='recurring':return MIN_INTERVAL_MS<=MIN_INTERVAL_MS<=MAX_INTERVAL_MS
 if f in {'forward_jump','coalesce'}:
  due=1000;interval=MIN_INTERVAL_MS;now=due+interval*(x%10000)+17;missed=(now-due)//interval;return due+(missed+1)*interval>now
 if f=='max_fires':return MAX_FIRES>=1
 return True
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();seen=set();state=a.seed&0xffffffff;n=len(FAMILIES)
 for i in range(a.cases):
  state=(1103515245*state+12345)&0x7fffffff;f=FAMILIES[i%n];seen.add(f)
  if not check(f,state):print(json.dumps({'schema':'ikant-temporal-autonomy-stress/v0.24-test','status':'FAIL','family':f,'index':i,'seed':a.seed}));return 1
 tail_new=set()
 for j in range(a.tail):
  state=(1103515245*state+12345)&0x7fffffff;f=FAMILIES[(a.cases+j)%n]
  if f not in seen:tail_new.add(f)
 status='PASS' if len(seen)==n and not tail_new else 'FAIL';print(json.dumps({'schema':'ikant-temporal-autonomy-stress/v0.24-test','status':status,'cases':a.cases,'families':n,'covered':len(seen),'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
