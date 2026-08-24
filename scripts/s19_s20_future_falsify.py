from __future__ import annotations
import argparse, hashlib, json, secrets
from collections import Counter
from pathlib import Path
MASK=(1<<64)-1
DOMAINS=('memory_root','memory_dependency','memory_replay','retrieval','task_schedule','task_wake','task_cancel','task_payload','runtime_epoch','residency','backup_restore','migration','privacy_erase','connector_future','transaction_future','native_future','release_update','cross_memory_task','crash_restart','surface_truth')
PHASES=8;CONTEXTS=8;CLASSES=4;FAMILIES=128;SIGNATURE_SPACE=FAMILIES*PHASES*CONTEXTS*CLASSES;SEED_FANOUT=64
ROOT=Path(__file__).resolve().parents[1]
def source_probe():
    errors=[]
    memory=(ROOT/'ikant'/'memory_governance.py').read_text(encoding='utf-8') if (ROOT/'ikant'/'memory_governance.py').exists() else ''
    tasks=(ROOT/'ikant'/'task_governance.py').read_text(encoding='utf-8') if (ROOT/'ikant'/'task_governance.py').exists() else ''
    runtime=(ROOT/'ikant'/'governance_runtime.py').read_text(encoding='utf-8') if (ROOT/'ikant'/'governance_runtime.py').exists() else ''
    app=(ROOT/'ikant'/'local_app.py').read_text(encoding='utf-8') if (ROOT/'ikant'/'local_app.py').exists() else ''
    gates={'support_aware_forget':'_support_aware_closure' in memory and 'preserved_node_ids' in memory,'exact_forget_confirmation':'forget_action_fingerprint' in memory and 'ACTION_CONFIRMATION' in memory,'cross_session_tombstone':'origin_session_id' in memory and 'reconcile_memory_governance' in memory,'single_plaintext_capsule':'TEMPORAL_INTENT_CAPSULE_SCHEMA' in tasks and 'raw_intent_in_core_journal' in tasks,'orphan_capsule_reconcile':'_cleanup_orphan_capsules' in tasks,'memory_dependency_wake_gate':'_memory_status' in tasks and 'BLOCKED_GOVERNANCE' in tasks,'honest_residency':'IN_PROCESS_ONLY' in tasks and 'background_guaranteed' in tasks,'future_authority_barriers':'future_connector_scope_revalidation_required' in tasks and 'future_transaction_approval_revalidation_required' in tasks,'governed_product_runner':'GovernedTemporalTaskRunner' in runtime and 'GovernedTemporalTaskRunner' in app and 'TemporalAutonomyRunner' not in app}
    return [k for k,v in gates.items() if not v]
AS_IS={'memory_availability_gate','evidence_immutable','temporal_replay_hash','schedule_exact_human_auth','wake_zero_authority','wake_freshness_barrier','cancel_pending_terminal','clock_rollback_block','control_retry_only','egress_locked_polling','causal_turn_commit','runtime_epoch_integrity'}
THREATS=(
('forget_only_root',{'forget_support_closure'}),('forget_derived_chain',{'forget_support_closure','forget_replay_op'}),('forget_kills_alt_support',{'derived_alt_support_preserve'}),('forget_no_preview',{'forget_preview_digest','forget_task_impact_projection'}),('forget_without_exact_user_decision',{'forget_exact_confirmation'}),('forget_replay_resurrects',{'forget_replay_op','forget_tombstone_migration'}),('backup_restores_forgotten',{'backup_restore_tombstone_precedence','forget_tombstone_migration'}),('migration_drops_tombstone',{'forget_tombstone_migration','task_schema_migration_guard'}),('derived_task_uses_forgotten_memory',{'task_memory_dependency_gate','wake_current_memory_revalidation'}),('explicit_task_cancelled_by_unrelated_forget',{'explicit_task_independence'}),('task_impact_hidden',{'forget_task_impact_projection','task_projection_user_visible'}),('task_raw_intent_duplicated',{'intent_capsule_single_copy','capsule_ref_only_in_journal'}),('wake_raw_intent_duplicated',{'intent_capsule_single_copy','capsule_ref_only_in_journal'}),('capsule_tamper_not_detected',{'intent_capsule_integrity','wake_capsule_tamper_block'}),('capsule_missing_still_wakes',{'wake_capsule_missing_block'}),('erase_scope_forgets_capsule',{'intent_capsule_erase_scope'}),('task_has_no_creation_epoch',{'task_creation_epoch_receipt'}),('task_implies_background_residency',{'residency_truth_in_process'}),('task_not_user_visible',{'task_projection_user_visible'}),('update_replays_unknown_task_schema',{'task_schema_migration_guard'}),('connector_uses_wake_as_scope',{'future_connector_fresh_scope','wake_freshness_barrier'}),('transaction_uses_wake_as_approval',{'future_transaction_fresh_approval','wake_zero_authority'}),('native_host_becomes_second_runtime',{'future_native_single_runtime','residency_truth_in_process'}),('future_host_claims_always_on_without_supply',{'residency_truth_in_process','future_native_single_runtime'}),('restored_task_references_erased_capsule',{'intent_capsule_erase_scope','wake_capsule_missing_block','task_schema_migration_guard'}),('forgotten_memory_reappears_via_connector',{'task_memory_dependency_gate','future_connector_fresh_scope','forget_tombstone_migration'}),('forgotten_memory_reappears_via_backup',{'backup_restore_tombstone_precedence','forget_replay_op'}),('wake_after_forget_reuses_old_context',{'wake_current_memory_revalidation','wake_freshness_barrier'}),('schedule_authority_survives_epoch_change',{'task_creation_epoch_receipt','wake_freshness_barrier'}),('cancelled_task_capsule_executes',{'cancel_pending_terminal','wake_capsule_missing_block'}),('privacy_erase_rewrites_evidence_history',{'evidence_immutable','intent_capsule_erase_scope'}),('forget_rewrites_audit_history',{'evidence_immutable','forget_replay_op'}),('schedule_failure_leaves_plaintext_orphan',{'orphan_capsule_reconciliation','intent_capsule_single_copy'}),('new_session_restore_drops_forget_tombstone',{'cross_session_tombstone_replay','backup_restore_tombstone_precedence'}),('direct_s6_runner_bypasses_governance',{'governed_product_runner'}),)
def splitmix64(x):
    x=(x+0x9E3779B97F4A7C15)&MASK;x=((x^(x>>30))*0xBF58476D1CE4E5B9)&MASK;x=((x^(x>>27))*0x94D049BB133111EB)&MASK;return x^(x>>31)
def seeds(master):return [splitmix64(master+i*0x9E3779B97F4A7C15) for i in range(SEED_FANOUT)]
def sig(i,master):
    idx=(i*(SIGNATURE_SPACE-1)+(master%SIGNATURE_SPACE))%SIGNATURE_SPACE;family=idx%FAMILIES;q=idx//FAMILIES;phase=q%PHASES;q//=PHASES;context=q%CONTEXTS;return idx,family,phase,context,family%len(DOMAINS)
def threat_mask(i,master,fan):
    x=splitmix64(fan[i%SEED_FANOUT]^i^(master<<1));n=1+((x>>61)&3);mask=0
    for j in range(n):
        x=splitmix64(x+j+0xA0761D6478BD642F);t=int((x+(i%len(THREATS))+j*11)%len(THREATS));mask|=1<<t
    return mask
def corpus(cases,master):
    fan=seeds(master);buckets=Counter();seen=bytearray(SIGNATURE_SPACE);pairs=set();hits=[0]*FAMILIES
    for i in range(cases):
        idx,fam,phase,ctx,d1=sig(i,master);seen[idx]=1;hits[fam]+=1;d2=splitmix64(master+i*17+0xD1B54A32D192ED03)%len(DOMAINS);pairs.add(tuple(sorted((d1,int(d2)))));buckets[threat_mask(i,master,fan)]+=1
    return buckets,sum(seen),len(pairs),min(hits),max(hits),fan
def evaluate_buckets(buckets,architecture):
    survivors=0;missing=Counter()
    for mask,count in buckets.items():
        need=set();m=mask;ti=0
        while m:
            if m&1:need|=(THREATS[ti][1]-architecture)
            m>>=1;ti+=1
        if need:survivors+=count;missing.update({x:count for x in need})
    return survivors,missing
def converge(buckets):
    arch=set(AS_IS);rounds=[]
    for r in range(20):
        survivors,missing=evaluate_buckets(buckets,arch);rounds.append({'round':r,'survivors':survivors,'enabled_new':sorted(arch-AS_IS),'top_missing':missing.most_common(8)})
        if survivors==0:break
        candidates=[k for k,_ in missing.most_common() if k not in arch]
        if not candidates:break
        arch.update(candidates[:4])
    return arch,rounds
def run(cases,tail,master):
    buckets,observed,pairs,minhit,maxhit,fan=corpus(cases,master);arch,rounds=converge(buckets);survivors,_=evaluate_buckets(buckets,arch);seen=bytearray(SIGNATURE_SPACE)
    for i in range(cases):seen[sig(i,master)[0]]=1
    new=0
    for i in range(cases,cases+tail):idx=sig(i,master)[0];new+=int(not seen[idx]);seen[idx]=1
    errors=source_probe();coverage_required=cases>=SIGNATURE_SPACE;coverage_ok=(not coverage_required) or (observed==SIGNATURE_SPACE and new==0)
    return {'schema':'ikant-s19-s20-future-falsification/v3-test','status':'PASS' if survivors==0 and coverage_ok and not errors else 'FAIL','coverage_required':coverage_required,'coverage_complete':coverage_ok,'source_probe_errors':errors,'master_seed':master,'seed_fanout':SEED_FANOUT,'seed_fanout_sha256':hashlib.sha256(json.dumps(fan).encode()).hexdigest(),'cases':cases,'tail':tail,'domains':list(DOMAINS),'families':FAMILIES,'phases':PHASES,'contexts':CONTEXTS,'mutation_classes':CLASSES,'semantic_signature_space':SIGNATURE_SPACE,'semantic_signatures':observed,'domain_pair_space':len(DOMAINS)*(len(DOMAINS)+1)//2,'domain_pairs_observed':pairs,'family_min_hits':minhit,'family_max_hits':maxhit,'tail_new_signatures':new,'initial_survivors':rounds[0]['survivors'],'final_survivors':survivors,'rounds':rounds,'as_is_protections':sorted(AS_IS),'converged_new_protections':sorted(arch-AS_IS),'threats':[{'name':n,'requires':sorted(req)} for n,req in THREATS],'unique_scenario_buckets':len(buckets),'interpretation':'Architecture/fault-vocabulary falsification only; not production reliability, not physical crash/browser/provider/native execution.'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--mutations',type=int);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int);ap.add_argument('--mode',default='falsify');a=ap.parse_args();size=a.mutations if a.mutations is not None else a.cases;seed=a.seed if a.seed is not None else secrets.randbits(64);out=run(max(1,size),max(0,a.tail),seed);out['mode']=a.mode;print(json.dumps(out,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()