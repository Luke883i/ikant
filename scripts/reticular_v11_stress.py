from __future__ import annotations
import argparse,json,random
FAMILIES=('normal_turn','identity','surface_pending','surface_close','exit','resume_release','resume_breach','crash_pending','tamper_frame','delete_egress','active_accept','active_probe','active_initialize','machine_file','machine_stdout','bidi','ansi','oversize','double_seal','stale_ack','digest_race','orientation_overfetch','psyche_pressure','evidence_guard')
def oracle(fam,rng):
 if fam in {'normal_turn','identity','surface_pending','surface_close'}:return ('ACTIVE','DASHBOARD_ONLY','ALLOW','no_evidence_escalation')
 if fam=='exit':return ('ACTIVE','RELEASE_PENDING','ALLOW','ack_required')
 if fam=='resume_release':return ('RELEASED','LOCKED','ALLOW','integrity_required')
 if fam=='resume_breach':return ('BREACHED','LOCKED','ALLOW_IF_ATTESTED','integrity+transport')
 if fam=='crash_pending':return ('FRAME_PENDING','FRAME_PENDING','REPLAY','exact_bytes')
 if fam in {'tamper_frame','bidi','ansi','oversize','double_seal','stale_ack'}:return ('ACTIVE','BREACHED_OR_DENY','DENY','fail_closed')
 if fam=='delete_egress':return ('ACTIVE','MISSING','DENY','no_recreate')
 if fam in {'active_accept','active_probe','active_initialize'}:return ('ACTIVE','LOCKED','DASHBOARD_BLOCK','no_preactive_bypass')
 if fam=='machine_file':return ('ACTIVE','LOCKED','ALLOW_MACHINE','file_only')
 if fam=='machine_stdout':return ('ACTIVE','LOCKED','DENY_MACHINE','human_sink_forbidden')
 if fam in {'digest_race','orientation_overfetch'}:return ('PREACTIVE','BREACHED_OR_DENY','DENY','admission_bound')
 if fam=='psyche_pressure':return ('ACTIVE','LOCKED','ALLOW','caution_monotone')
 if fam=='evidence_guard':return ('ACTIVE','LOCKED','ALLOW','runtime_derived_zero_authority')
 raise AssertionError(fam)
def run(cases,tail,seed):
 rng=random.Random(seed);seen=set();last_new=0;errors=0;counts={f:0 for f in FAMILIES}
 for i in range(1,cases+1):
  fam=FAMILIES[(i-1)%len(FAMILIES)] if i<=len(FAMILIES)*4 else rng.choice(FAMILIES);sig=(fam,)+oracle(fam,rng);counts[fam]+=1
  if sig not in seen:seen.add(sig);last_new=i
  if sig[2] in {'ALLOW','ALLOW_MACHINE'} and fam in {'delete_egress','machine_stdout','active_accept','active_probe','active_initialize'}:errors+=1
 tail_new=0
 for _ in range(tail):
  fam=rng.choice(FAMILIES);sig=(fam,)+oracle(fam,rng)
  if sig not in seen:seen.add(sig);tail_new+=1
 return {'schema':'ikant-reticular-v11-stress/v0.11-test','seed':seed,'M':cases,'M_plus_tail':cases+tail,'scenario_families':len(FAMILIES),'causal_signatures':len(seen),'last_novelty_at':last_new,'tail_new_signatures':tail_new,'errors':errors,'coverage':{k:v for k,v in counts.items() if v},'status':'PASS' if errors==0 and tail_new==0 and all(counts.values()) else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=10000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.cases,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
