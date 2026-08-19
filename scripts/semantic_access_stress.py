from __future__ import annotations
import argparse,itertools,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.rights_policy import AccessMode,ExternalBasis,decide_owner_authorization

def scenarios():return list(itertools.product(list(AccessMode),(False,True),(False,True),(False,True),list(ExternalBasis)))
def violations(sc,d):
 mode,accepted,clean,technical,basis=sc;errors=[]
 if d.epistemic_authority:errors.append('control_promoted_to_evidence')
 if basis is not ExternalBasis.NONE:
  if d.legal_status!='NOT_ADJUDICATED':errors.append('external_basis_adjudicated')
  if d.ikant_conformance=='CONFORMING':errors.append('external_basis_promoted_to_conformance')
  return errors
 if mode is AccessMode.HUMAN_MANUAL:
  if d.code!='HUMAN_MANUAL_OUTSIDE_AI_GATE':errors.append('manual_human_forced_into_ai_gate')
 elif mode is AccessMode.CONFORMANCE_MATERIALIZATION:
  allowed=accepted and clean
  if allowed!=(d.code=='MATERIALIZATION_FOR_CONFORMANCE_ALLOWED'):errors.append('materialization_gate_mismatch')
  if d.ikant_conformance=='CONFORMING':errors.append('materialization_self_promoted')
 elif mode is AccessMode.MODEL_TRAINING:
  if d.code!='SEPARATE_LICENSE_REQUIRED':errors.append('training_licensed_by_access_contract')
 else:
  allowed=accepted and clean and technical
  if allowed!=(d.code=='OWNER_AUTHORIZED_CONFORMING_IKANT'):errors.append('substantive_ai_gate_mismatch')
 return errors
def signature(sc,d):return tuple(x.value if hasattr(x,'value') else x for x in sc)+(d.code,d.owner_authorization,d.ikant_conformance,d.legal_status,d.epistemic_authority)
def run(cases,tail,seed):
 rng=random.Random(seed);universe=scenarios();seen=set();counts={m.value:0 for m in AccessMode};errors=[];last_new=0
 for i in range(1,cases+1):
  sc=universe[(i-1)%len(universe)] if i<=len(universe) else rng.choice(universe);d=decide_owner_authorization(sc[0],accepted_current_terms=sc[1],clean_admission=sc[2],technical_conformance=sc[3],external_basis=sc[4]);counts[sc[0].value]+=1;bad=violations(sc,d)
  if bad:errors.append({'case':i,'scenario':[x.value if hasattr(x,'value') else x for x in sc],'errors':bad})
  sig=signature(sc,d)
  if sig not in seen:seen.add(sig);last_new=i
 tail_new=0
 for _ in range(tail):
  sc=rng.choice(universe);d=decide_owner_authorization(sc[0],accepted_current_terms=sc[1],clean_admission=sc[2],technical_conformance=sc[3],external_basis=sc[4]);sig=signature(sc,d)
  if sig not in seen:seen.add(sig);tail_new+=1
 return {'schema':'ikant-semantic-access-stress/v0.12-test','seed':seed,'M':cases,'M_plus_tail':cases+tail,'scenario_universe':len(universe),'causal_signatures':len(seen),'last_novelty_at':last_new,'tail_new_signatures':tail_new,'errors':errors[:20],'error_count':len(errors),'coverage':counts,'status':'PASS' if not errors and tail_new==0 and all(counts.values()) else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=10000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.cases,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
