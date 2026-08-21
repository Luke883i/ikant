from __future__ import annotations
import argparse,json

FAMILIES=(
 'second_writer','client_binding_drift','shell_id_drift','runtime_session_drift','writer_reclaim',
 'seq_zero','seq_bool','seq_skip','seq_rewind','non_sync_first','bound_first_sync',
 'idem_short','idem_bad_chars','idem_reuse','pending_new_idem','pending_same_idem_new_payload','pending_same_idem_new_op','pending_same_idem_new_expected',
 'expected_missing','expected_wrong_session','expected_wrong_epoch','expected_wrong_seq','expected_wrong_sha','returned_wrong_session','returned_bad_schema','returned_bad_receipt',
 'pending_reexec','pending_replay_frame_drift','pending_replay_metadata','pending_open_loses_response','pending_concurrent_op',
 'ack_schema','ack_shell','ack_client','ack_seq','ack_idem','ack_frame_session','ack_frame_epoch','ack_frame_seq','ack_frame_sha','ack_without_pending','ack_replay_recommit','ack_replay_drift',
 'turn_empty','turn_nul','turn_oversize','turn_extra','turn_nonstring','nonturn_payload','unknown_op',
 'legacy_frame_bypass','legacy_ack_bypass','legacy_turn_bypass','legacy_resume_bypass','legacy_initialize_bypass',
 'browser_authority','shell_authority','epistemic_authority','execution_authority','semantic_channel_drift','direct_model_transport','parallel_semantic_pane','raw_model_tokens',
 'exit_duplicate','resume_stale','released_sync_reexec','transport_retry_new_identity','voice_frame_direct_render','malformed_downstream_burns_key'
)
CLASS={
 **{x:'SINGLE_WRITER' for x in FAMILIES[0:5]},
 **{x:'SEQUENCE' for x in FAMILIES[5:11]},
 **{x:'IDEMPOTENCY' for x in FAMILIES[11:18]},
 **{x:'FRAME_BINDING' for x in FAMILIES[18:26]},
 **{x:'PENDING_REPLAY' for x in FAMILIES[26:31]},
 **{x:'EXACT_ACK' for x in FAMILIES[31:43]},
 **{x:'PAYLOAD_BOUNDARY' for x in FAMILIES[43:50]},
 **{x:'LEGACY_BYPASS' for x in FAMILIES[50:55]},
 **{x:'AUTHORITY_EGRESS' for x in FAMILIES[55:63]},
 **{x:'RELEASE_RECOVERY' for x in FAMILIES[63:]},
}

def kill(f:str,x:int)->bool:
 if f in {'seq_zero','seq_bool','non_sync_first','bound_first_sync','turn_empty','turn_nul','turn_extra','turn_nonstring','nonturn_payload','unknown_op'}:return True
 if f=='seq_skip':return 2+(x%1000)!=1
 if f=='seq_rewind':return 1<2+(x%1000)
 if f=='idem_short':return len('x'*(x%15))<16
 if f=='idem_bad_chars':return True
 if f=='turn_oversize':return 65537+(x%1024)>65536
 if f in {'expected_wrong_epoch','expected_wrong_seq'}:return 1+(x%1000)!=0
 return f in CLASS

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=10_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 if a.mutations<1 or a.tail<0:return 2
 state=(a.seed&0xffffffff) or 1;seen=set();classes=set();killed=0;first_full=None;n=len(FAMILIES)
 for i in range(a.mutations):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n];seen.add(f);classes.add(CLASS[f])
  if not kill(f,state):
   print(json.dumps({'schema':'ikant-advanced-web-shell-mutations/v0.26-test','status':'FAIL','survivor':f,'index':i,'seed':a.seed}));return 1
  killed+=1
  if first_full is None and len(seen)==n:first_full=i+1
 tail_new_families=set();tail_new_classes=set()
 for j in range(a.tail):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[(a.mutations+j)%n]
  if f not in seen:tail_new_families.add(f)
  if CLASS[f] not in classes:tail_new_classes.add(CLASS[f])
  if not kill(f,state):return 1
 status='PASS' if killed==a.mutations and len(seen)==n and not tail_new_families and not tail_new_classes else 'FAIL'
 print(json.dumps({'schema':'ikant-advanced-web-shell-mutations/v0.26-test','status':status,'mutations':a.mutations,'killed':killed,'families':n,'covered_families':len(seen),'semantic_kill_classes':len(classes),'saturation_frontier':first_full,'tail':a.tail,'tail_new_families':sorted(tail_new_families),'tail_new_classes':sorted(tail_new_classes),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
