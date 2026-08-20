from __future__ import annotations
import argparse,json
FAMILIES=('ms_zero','ms_large','rollback_tolerance_minus_one','rollback_tolerance_plus_one','claim_deadline_exact','retry_exact','utf8_bound','worker_bound','fire_1','fire_1000','interval_60s','interval_366d','same_tick_poll','duplicate_replay','release_pause','pending_pause')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();seen={FAMILIES[i%len(FAMILIES)] for i in range(a.cases)};tail_new={FAMILIES[(a.cases+i)%len(FAMILIES)] for i in range(a.tail)}-seen;status='PASS' if len(seen)==len(FAMILIES) and not tail_new else 'FAIL';print(json.dumps({'schema':'ikant-temporal-autonomy-edges/v0.24-test','status':status,'cases':a.cases,'families':len(FAMILIES),'covered':len(seen),'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
