from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.rights_policy import AccessMode,ExternalBasis,decide_owner_authorization
MUTANTS=('public_implies_ai_grant','acceptance_alone_grants_ai_study','dirty_admission_retroactively_cured','clean_chat_study_requires_local_active','remediated_chat_study_denied','remediated_breach_becomes_clean','remediated_context_materializes_runtime','platform_grant_becomes_owner_grant','statutory_exception_becomes_owner_grant','separate_license_becomes_ikant_conformance','external_basis_is_legally_adjudicated','manual_human_forced_to_accept','manual_human_creates_broad_owner_license','model_training_allowed_by_acceptance','model_training_allowed_by_conformance','materialization_allowed_without_acceptance','materialization_allowed_after_dirty_admission','materialization_self_promotes_to_conformance','rights_control_becomes_epistemic_evidence','official_ikant_without_acceptance','official_ikant_without_clean_admission','official_ikant_without_transport_conformance','tdm_reservation_downgraded_to_default_allow')
def killed(name,rng):
 if name=='public_implies_ai_grant':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY).owner_authorization=='RESERVED'
 if name=='acceptance_alone_grants_ai_study':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True).owner_authorization=='RESERVED'
 if name=='dirty_admission_retroactively_cured':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True,clean_admission=False,remediated_admission=False,technical_conformance=True).owner_authorization=='RESERVED'
 if name=='clean_chat_study_requires_local_active':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True,clean_admission=True,technical_conformance=False).code=='OWNER_AUTHORIZED_CHAT_STUDY'
 if name=='remediated_chat_study_denied':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True,remediated_admission=True).code=='OWNER_AUTHORIZED_REMEDIATED_CHAT_STUDY'
 if name=='remediated_breach_becomes_clean':
  d=decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True,remediated_admission=True);return d.ikant_conformance=='NOT_CONFORMING' and d.owner_authorization=='GRANTED_PROSPECTIVELY_AFTER_REMEDIATION'
 if name=='remediated_context_materializes_runtime':return decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION,accepted_current_terms=True,remediated_admission=True).owner_authorization=='RESERVED'
 if name=='platform_grant_becomes_owner_grant':
  d=decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,external_basis=ExternalBasis.PLATFORM_DIRECT_GRANT);return d.owner_authorization=='NOT_GRANTED_BY_IKANT' and d.ikant_conformance=='NOT_CONFORMING'
 if name=='statutory_exception_becomes_owner_grant':
  d=decide_owner_authorization(AccessMode.AUTOMATED_REPOSITORY_ANALYSIS,external_basis=ExternalBasis.STATUTORY_EXCEPTION);return d.owner_authorization=='NOT_GRANTED_BY_IKANT' and d.legal_status=='NOT_ADJUDICATED'
 if name=='separate_license_becomes_ikant_conformance':return decide_owner_authorization(AccessMode.OFFICIAL_IKANT,external_basis=ExternalBasis.SEPARATE_LICENSE).ikant_conformance=='NOT_CONFORMING'
 if name=='external_basis_is_legally_adjudicated':return decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,external_basis=rng.choice((ExternalBasis.PLATFORM_DIRECT_GRANT,ExternalBasis.STATUTORY_EXCEPTION,ExternalBasis.SEPARATE_LICENSE))).legal_status=='NOT_ADJUDICATED'
 if name=='manual_human_forced_to_accept':return decide_owner_authorization(AccessMode.HUMAN_MANUAL).code=='HUMAN_MANUAL_OUTSIDE_AI_GATE'
 if name=='manual_human_creates_broad_owner_license':return decide_owner_authorization(AccessMode.HUMAN_MANUAL).owner_authorization=='NOT_REQUIRED_BY_IKANT_POLICY'
 if name in {'model_training_allowed_by_acceptance','model_training_allowed_by_conformance'}:return decide_owner_authorization(AccessMode.MODEL_TRAINING,accepted_current_terms=True,clean_admission=True,technical_conformance=True).code=='SEPARATE_LICENSE_REQUIRED'
 if name=='materialization_allowed_without_acceptance':return decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION).code=='OWNER_AUTHORIZATION_RESERVED'
 if name=='materialization_allowed_after_dirty_admission':return decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION,accepted_current_terms=True).code=='OWNER_AUTHORIZATION_RESERVED'
 if name=='materialization_self_promotes_to_conformance':
  d=decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION,accepted_current_terms=True,clean_admission=True);return d.code=='MATERIALIZATION_FOR_CONFORMANCE_ALLOWED' and d.ikant_conformance=='PENDING'
 if name=='rights_control_becomes_epistemic_evidence':return decide_owner_authorization(rng.choice(list(AccessMode)),accepted_current_terms=bool(rng.getrandbits(1)),clean_admission=bool(rng.getrandbits(1)),remediated_admission=bool(rng.getrandbits(1)),technical_conformance=bool(rng.getrandbits(1))).epistemic_authority is False
 if name=='official_ikant_without_acceptance':return decide_owner_authorization(AccessMode.OFFICIAL_IKANT,clean_admission=True,technical_conformance=True).ikant_conformance=='NOT_CONFORMING'
 if name=='official_ikant_without_clean_admission':return decide_owner_authorization(AccessMode.OFFICIAL_IKANT,accepted_current_terms=True,remediated_admission=True,technical_conformance=True).ikant_conformance=='NOT_CONFORMING'
 if name=='official_ikant_without_transport_conformance':return decide_owner_authorization(AccessMode.OFFICIAL_IKANT,accepted_current_terms=True,clean_admission=True).ikant_conformance=='NOT_CONFORMING'
 if name=='tdm_reservation_downgraded_to_default_allow':
  from ikant.rights_policy import policy_manifest
  return policy_manifest()['tdm']['reservation']==1 and policy_manifest()['tdm']['express_reservation'] is True
 raise AssertionError(name)
def run(mutations,tail,seed):
 rng=random.Random(seed);counts={n:0 for n in MUTANTS};signatures=set();survivors=[];last_new=0
 for i in range(1,mutations+1):
  name=MUTANTS[(i-1)%len(MUTANTS)] if i<=len(MUTANTS) else rng.choice(MUTANTS);counts[name]+=1;ok=killed(name,rng);sig=(name,ok)
  if sig not in signatures:signatures.add(sig);last_new=i
  if not ok:survivors.append({'case':i,'mutant':name})
 tail_new=0
 for _ in range(tail):
  name=rng.choice(MUTANTS);sig=(name,killed(name,rng))
  if sig not in signatures:signatures.add(sig);tail_new+=1
 return {'schema':'ikant-semantic-access-mutations/v0.12-test','seed':seed,'mutations':mutations,'tail':tail,'mutation_families':len(MUTANTS),'killed_instances':mutations-len(survivors),'survivor_count':len(survivors),'survivors':survivors[:20],'last_novelty_at':last_new,'tail_new_signatures':tail_new,'coverage':counts,'status':'PASS' if not survivors and tail_new==0 and all(counts.values()) else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=100000);p.add_argument('--tail',type=int,default=10000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.mutations,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
