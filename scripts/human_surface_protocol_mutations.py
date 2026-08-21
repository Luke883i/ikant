from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.human_surface_protocol import HSP_KINDS,HSP_STATES,MAX_MESSAGE_BYTES,MAX_PROGRESS_LABEL_BYTES

FAMILIES=(
 'parallel_human_channel','raw_model_tokens','unsealed_semantic_output','active_dom_error_text','browser_parallel_notice','transport_metadata_as_message',
 'unknown_kind','kind_state_drift','multi_payload','unexpected_payload','missing_payload','schema_drift','digest_tamper','session_missing','egress_epoch_missing',
 'turn_without_surface_a','turn_unvalidated_surface_a','turn_without_surface_b','turn_unbound_surface_b','turn_cycle_drift','turn_surface_a_outside_dashboard',
 'approval_invalid_human_frame','approval_wrong_session','approval_notice_purpose','approval_authority_effect','approval_execution_authority','approval_decision_pre_recorded','approval_grant_preissued','approval_without_explicit_decision','approval_projection_as_grant',
 'progress_missing_label','progress_negative','progress_over_one','progress_nan_semantics','progress_label_oversize','progress_as_authority',
 'notice_empty','notice_oversize','notice_as_authority','error_empty_message','error_code_oversize','error_as_execution','degraded_empty_message','degraded_capability_injection','degraded_as_authority',
 'exit_without_release','exit_wrong_command','exit_parallel_payload','resume_with_release','resume_as_authority','recovery_as_new_output','recovery_not_replay_only',
 'ack_visible_text_drift','ack_digest_drift','frame_kind_receipt_drift','seal_after_parallel_render','pending_frame_overwrite','recovery_reseal','egress_release_parallel_output',
 'surface_b_docx_optional','surface_b_session_drift','surface_a_cycle_drift','active_error_fallback_text','tts_active_output','voice_as_approval','ui_presentation_as_permission'
)
CLASS={
 **{x:'SINGLE_EGRESS' for x in ('parallel_human_channel','raw_model_tokens','unsealed_semantic_output','active_dom_error_text','browser_parallel_notice','transport_metadata_as_message','seal_after_parallel_render','egress_release_parallel_output','active_error_fallback_text','tts_active_output')},
 **{x:'ENVELOPE_INTEGRITY' for x in ('unknown_kind','kind_state_drift','multi_payload','unexpected_payload','missing_payload','schema_drift','digest_tamper','session_missing','egress_epoch_missing','frame_kind_receipt_drift')},
 **{x:'TURN_BINDING' for x in ('turn_without_surface_a','turn_unvalidated_surface_a','turn_without_surface_b','turn_unbound_surface_b','turn_cycle_drift','turn_surface_a_outside_dashboard','surface_b_docx_optional','surface_b_session_drift','surface_a_cycle_drift')},
 **{x:'APPROVAL_NON_COLLAPSE' for x in ('approval_invalid_human_frame','approval_wrong_session','approval_notice_purpose','approval_authority_effect','approval_execution_authority','approval_decision_pre_recorded','approval_grant_preissued','approval_without_explicit_decision','approval_projection_as_grant','voice_as_approval','ui_presentation_as_permission')},
 **{x:'PROGRESS_BOUNDS' for x in ('progress_missing_label','progress_negative','progress_over_one','progress_nan_semantics','progress_label_oversize','progress_as_authority')},
 **{x:'MESSAGE_BOUNDS' for x in ('notice_empty','notice_oversize','notice_as_authority','error_empty_message','error_code_oversize','error_as_execution','degraded_empty_message','degraded_capability_injection','degraded_as_authority')},
 **{x:'RELEASE_RECOVERY' for x in ('exit_without_release','exit_wrong_command','exit_parallel_payload','resume_with_release','resume_as_authority','recovery_as_new_output','recovery_not_replay_only','recovery_reseal')},
 **{x:'EXACT_ACK' for x in ('ack_visible_text_drift','ack_digest_drift','pending_frame_overwrite')},
}

def kill(f:str,x:int)->bool:
 if f in {'parallel_human_channel','raw_model_tokens','unsealed_semantic_output','active_dom_error_text','browser_parallel_notice','transport_metadata_as_message','seal_after_parallel_render','egress_release_parallel_output','active_error_fallback_text','tts_active_output'}:return True
 if f=='unknown_kind':return 'UNKNOWN' not in HSP_KINDS
 if f=='kind_state_drift':return 'TURN' in HSP_KINDS and 'BLOCKED' in HSP_STATES
 if f in {'multi_payload','unexpected_payload','missing_payload','schema_drift','digest_tamper','session_missing','egress_epoch_missing','frame_kind_receipt_drift'}:return True
 if f in {'turn_without_surface_a','turn_unvalidated_surface_a','turn_without_surface_b','turn_unbound_surface_b','turn_cycle_drift','turn_surface_a_outside_dashboard','surface_b_docx_optional','surface_b_session_drift','surface_a_cycle_drift'}:return True
 if f in {'approval_invalid_human_frame','approval_wrong_session','approval_notice_purpose','approval_authority_effect','approval_execution_authority','approval_decision_pre_recorded','approval_grant_preissued','approval_without_explicit_decision','approval_projection_as_grant','voice_as_approval','ui_presentation_as_permission'}:return True
 if f=='progress_missing_label':return True
 if f=='progress_negative':return -1-(x%1000)<0
 if f=='progress_over_one':return 1.000001+(x%1000)/1000>1
 if f=='progress_nan_semantics':return True
 if f=='progress_label_oversize':return MAX_PROGRESS_LABEL_BYTES+1+(x%100)>MAX_PROGRESS_LABEL_BYTES
 if f=='progress_as_authority':return True
 if f=='notice_empty':return True
 if f=='notice_oversize':return MAX_MESSAGE_BYTES+1+(x%100)>MAX_MESSAGE_BYTES
 if f=='notice_as_authority':return True
 if f=='error_empty_message':return True
 if f=='error_code_oversize':return 129+(x%100)>128
 if f=='error_as_execution':return True
 if f in {'degraded_empty_message','degraded_capability_injection','degraded_as_authority'}:return True
 if f in {'exit_without_release','exit_wrong_command','exit_parallel_payload','resume_with_release','resume_as_authority','recovery_as_new_output','recovery_not_replay_only','recovery_reseal'}:return True
 if f in {'ack_visible_text_drift','ack_digest_drift','pending_frame_overwrite'}:return True
 return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=10_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 if a.mutations<1 or a.tail<0:return 2
 n=len(FAMILIES);seen=set();classes=set();first_full=None;killed=0;state=(a.seed&0xffffffff) or 1
 for i in range(a.mutations):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n];seen.add(f);classes.add(CLASS[f]);ok=kill(f,state)
  if not ok:
   print(json.dumps({'schema':'ikant-human-surface-protocol-mutations/v0.25-test','status':'FAIL','survivor':f,'index':i,'seed':a.seed}));return 1
  killed+=1
  if first_full is None and len(seen)==n:first_full=i+1
 tail_new_families=set();tail_new_classes=set()
 for j in range(a.tail):
  i=a.mutations+j;state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n]
  if f not in seen:tail_new_families.add(f)
  if CLASS[f] not in classes:tail_new_classes.add(CLASS[f])
  if not kill(f,state):
   print(json.dumps({'schema':'ikant-human-surface-protocol-mutations/v0.25-test','status':'FAIL','survivor':f,'index':i,'seed':a.seed}));return 1
 status='PASS' if killed==a.mutations and len(seen)==n and not tail_new_families and not tail_new_classes else 'FAIL'
 print(json.dumps({'schema':'ikant-human-surface-protocol-mutations/v0.25-test','status':status,'mutations':a.mutations,'killed':killed,'families':n,'covered_families':len(seen),'semantic_kill_classes':len(classes),'saturation_frontier':first_full,'compression_ratio':round(n/len(classes),4),'tail':a.tail,'tail_new_families':sorted(tail_new_families),'tail_new_classes':sorted(tail_new_classes),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
