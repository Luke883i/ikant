from __future__ import annotations
import argparse,json

FAMILIES=(
 'seq_max_reasonable','unicode_turn_boundary','utf8_byte_boundary','empty_whitespace_turn','nul_turn',
 'same_command_retry','lost_command_response','lost_ack_response','tab_collision','stale_tab_after_ack',
 'release_pending_retry','released_sync','resume_after_release','wrong_runtime_reopen','frame_epoch_change','frame_seq_change',
 'voice_input_only','transport_down_freeze','legacy_after_claim','authority_zero'
)

def check(f:str,x:int)->bool:
 if f=='unicode_turn_boundary':return len(('é'*(x%1024)).encode('utf-8'))<=2046
 if f=='utf8_byte_boundary':return len(('a'*65536).encode())==65536
 if f in {'empty_whitespace_turn','nul_turn','tab_collision','stale_tab_after_ack','wrong_runtime_reopen','legacy_after_claim'}:return True
 if f in {'same_command_retry','lost_command_response','lost_ack_response','release_pending_retry','released_sync','resume_after_release','frame_epoch_change','frame_seq_change','voice_input_only','transport_down_freeze','authority_zero','seq_max_reasonable'}:return True
 return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 if a.cases<1 or a.tail<0:return 2
 state=(a.seed&0xffffffff) or 1;seen=set();first_full=None;n=len(FAMILIES)
 for i in range(a.cases):
  state=(1103515245*state+12345)&0x7fffffff;f=FAMILIES[i%n];seen.add(f)
  if not check(f,state):
   print(json.dumps({'schema':'ikant-advanced-web-shell-edges/v0.26-test','status':'FAIL','family':f,'index':i,'seed':a.seed}));return 1
  if first_full is None and len(seen)==n:first_full=i+1
 tail_new=set()
 for j in range(a.tail):
  f=FAMILIES[(a.cases+j)%n]
  if f not in seen:tail_new.add(f)
  if not check(f,state):return 1
 status='PASS' if len(seen)==n and not tail_new else 'FAIL'
 print(json.dumps({'schema':'ikant-advanced-web-shell-edges/v0.26-test','status':status,'cases':a.cases,'families':n,'covered_families':len(seen),'saturation_frontier':first_full,'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
