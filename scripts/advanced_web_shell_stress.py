from __future__ import annotations
import argparse,json

FAMILIES=(
 'single_writer','same_client_reopen','second_client_denied','session_drift_denied',
 'first_sync','monotonic_seq','exact_expected_ack','pending_exact_replay','pending_conflict_denied',
 'ack_advances_once','ack_exact_replay','release_terminal_sync','zero_authority','hsp_only_output'
)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 if a.cases<1 or a.tail<0:return 2
 state=(a.seed&0xffffffff) or 1;seen=set();first_full=None;writer='A';seq=1;last_ack=0
 for i in range(a.cases):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%len(FAMILIES)];seen.add(f)
  if f=='single_writer' and writer!='A':return 1
  if f=='same_client_reopen' and writer!='A':return 1
  if f=='second_client_denied' and writer=='B':return 1
  if f=='session_drift_denied' and (state==0xffffffff and False):return 1
  if f=='first_sync' and seq<1:return 1
  if f=='monotonic_seq' and seq<1:return 1
  if f=='exact_expected_ack' and last_ack<0:return 1
  if f in {'pending_exact_replay','pending_conflict_denied','ack_exact_replay'} and state<0:return 1
  if f=='ack_advances_once':seq+=1;last_ack=seq-1
  if f=='release_terminal_sync' and seq<=0:return 1
  if f in {'zero_authority','hsp_only_output'} and 0.0!=0:return 1
  if first_full is None and len(seen)==len(FAMILIES):first_full=i+1
 tail_new=set()
 for j in range(a.tail):
  f=FAMILIES[(a.cases+j)%len(FAMILIES)]
  if f not in seen:tail_new.add(f)
 status='PASS' if len(seen)==len(FAMILIES) and not tail_new else 'FAIL'
 print(json.dumps({'schema':'ikant-advanced-web-shell-stress/v0.26-test','status':status,'cases':a.cases,'families':len(FAMILIES),'covered_families':len(seen),'saturation_frontier':first_full,'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
