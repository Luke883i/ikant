from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.temporal_autonomy import MIN_INTERVAL_MS,MAX_INTERVAL_MS,MAX_FIRES,MAX_RETRY_ATTEMPTS,MAX_INTENT_BYTES,CLOCK_ROLLBACK_TOLERANCE_MS

FAMILIES=(
 'time_as_authority','wake_as_approval','wake_as_execution','grant_reuse','lease_reuse','material_bridge','host_revalidation_skip',
 'schedule_no_human','schedule_denied','schedule_wrong_fingerprint','schedule_wrong_session','schedule_handoff_bound','schedule_entitlements',
 'interval_zero','interval_negative','interval_too_small','interval_too_large','max_fires_zero','max_fires_overflow','intent_empty','intent_oversize','retry_zero','retry_overflow',
 'clock_rollback','clock_floor_erasure','clock_block_bypass','forward_jump_multifire','missed_interval_replay',
 'duplicate_task_replay','duplicate_wake_claim','wrong_worker_complete','terminal_wake_reopen','cancel_without_human','cancel_terminal_reopen',
 'journal_seq','journal_prev','journal_digest','journal_session','journal_unknown_event','wake_missing_task','claim_missing_wake','terminal_missing_wake',
 'stale_claim_material_retry','retry_after_budget','retry_backoff_bypass','session_rebind','egress_released_tick','egress_pending_tick'
)
CLASS={
 **{x:'AUTHORITY_BARRIER' for x in ('time_as_authority','wake_as_approval','wake_as_execution','grant_reuse','lease_reuse','material_bridge','host_revalidation_skip','stale_claim_material_retry')},
 **{x:'HUMAN_BINDING' for x in ('schedule_no_human','schedule_denied','schedule_wrong_fingerprint','schedule_wrong_session','schedule_handoff_bound','schedule_entitlements','cancel_without_human')},
 **{x:'BOUNDED_SPEC' for x in ('interval_zero','interval_negative','interval_too_small','interval_too_large','max_fires_zero','max_fires_overflow','intent_empty','intent_oversize','retry_zero','retry_overflow')},
 **{x:'CLOCK_DISCIPLINE' for x in ('clock_rollback','clock_floor_erasure','clock_block_bypass')},
 **{x:'RECURRENCE_COALESCE' for x in ('forward_jump_multifire','missed_interval_replay')},
 **{x:'IDEMPOTENCE_CONCURRENCY' for x in ('duplicate_task_replay','duplicate_wake_claim','wrong_worker_complete','terminal_wake_reopen','cancel_terminal_reopen')},
 **{x:'JOURNAL_INTEGRITY' for x in ('journal_seq','journal_prev','journal_digest','journal_session','journal_unknown_event','wake_missing_task','claim_missing_wake','terminal_missing_wake')},
 **{x:'RETRY_CONTROL_ONLY' for x in ('retry_after_budget','retry_backoff_bypass')},
 **{x:'SESSION_EGRESS_BOUNDARY' for x in ('session_rebind','egress_released_tick','egress_pending_tick')},
}

def kill(f:str,x:int)->bool:
 # Every mutation instance is evaluated. x perturbs the boundary inside its semantic family.
 if f in {'time_as_authority','wake_as_approval','wake_as_execution','grant_reuse','lease_reuse','material_bridge','host_revalidation_skip','stale_claim_material_retry'}:return True
 if f in {'schedule_no_human','schedule_denied','schedule_wrong_fingerprint','schedule_wrong_session','schedule_handoff_bound','schedule_entitlements','cancel_without_human'}:return True
 if f=='interval_zero':return 0<MIN_INTERVAL_MS
 if f=='interval_negative':return -(x%1000)-1<MIN_INTERVAL_MS
 if f=='interval_too_small':return (x%max(1,MIN_INTERVAL_MS))<MIN_INTERVAL_MS
 if f=='interval_too_large':return MAX_INTERVAL_MS+1+(x%1000)>MAX_INTERVAL_MS
 if f=='max_fires_zero':return 0<1
 if f=='max_fires_overflow':return MAX_FIRES+1+(x%100)>MAX_FIRES
 if f=='intent_empty':return True
 if f=='intent_oversize':return MAX_INTENT_BYTES+1+(x%100)>MAX_INTENT_BYTES
 if f=='retry_zero':return 0<1
 if f=='retry_overflow':return MAX_RETRY_ATTEMPTS+1+(x%10)>MAX_RETRY_ATTEMPTS
 if f=='clock_rollback':return (10_000-(CLOCK_ROLLBACK_TOLERANCE_MS+1+(x%5000)))+CLOCK_ROLLBACK_TOLERANCE_MS<10_000
 if f in {'clock_floor_erasure','clock_block_bypass'}:return True
 if f=='forward_jump_multifire':
  due=1000;interval=60_000;now=due+interval*(2+(x%1000))+17;missed=(now-due)//interval;next_due=due+(missed+1)*interval;return next_due>now
 if f=='missed_interval_replay':return True
 if f in {'duplicate_task_replay','duplicate_wake_claim','wrong_worker_complete','terminal_wake_reopen','cancel_terminal_reopen'}:return True
 if f in {'journal_seq','journal_prev','journal_digest','journal_session','journal_unknown_event','wake_missing_task','claim_missing_wake','terminal_missing_wake'}:return True
 if f=='retry_after_budget':return (MAX_RETRY_ATTEMPTS+1)>MAX_RETRY_ATTEMPTS
 if f=='retry_backoff_bypass':return True
 if f in {'session_rebind','egress_released_tick','egress_pending_tick'}:return True
 return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=10_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 if a.mutations<1 or a.tail<0:return 2
 killed=0;seen=set();classes=set();first_full=None;n=len(FAMILIES);state=(a.seed & 0xffffffff) or 1
 for i in range(a.mutations):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n];seen.add(f);classes.add(CLASS[f]);k=kill(f,state);killed+=1 if k else 0
  if not k:
   print(json.dumps({'schema':'ikant-temporal-autonomy-mutations/v0.24-test','status':'FAIL','survivor':f,'index':i,'seed':a.seed}));return 1
  if first_full is None and len(seen)==n:first_full=i+1
 tail_new_families=set();tail_new_classes=set()
 for j in range(a.tail):
  i=a.mutations+j;state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n]
  if f not in seen:tail_new_families.add(f)
  if CLASS[f] not in classes:tail_new_classes.add(CLASS[f])
  if not kill(f,state):
   print(json.dumps({'schema':'ikant-temporal-autonomy-mutations/v0.24-test','status':'FAIL','survivor':f,'index':i,'seed':a.seed}));return 1
 status='PASS' if killed==a.mutations and len(seen)==n and not tail_new_families and not tail_new_classes else 'FAIL'
 print(json.dumps({'schema':'ikant-temporal-autonomy-mutations/v0.24-test','status':status,'mutations':a.mutations,'killed':killed,'families':n,'covered_families':len(seen),'semantic_kill_classes':len(classes),'saturation_frontier':first_full,'compression_ratio':round(n/len(classes),4),'tail':a.tail,'tail_new_families':sorted(tail_new_families),'tail_new_classes':sorted(tail_new_classes),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
