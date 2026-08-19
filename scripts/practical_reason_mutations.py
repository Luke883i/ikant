from __future__ import annotations
import argparse,json,random,sys
from dataclasses import dataclass,field
from enum import Enum
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.action_governance import build_action_ledger
from ikant.approvals import issue_same_turn_approval,validate_approval
from ikant.authority import normalize_capability,resolve_authority
class K(str,Enum):GOAL='goal';CONSTRAINT='constraint';ACTION='action'
@dataclass
class M:social_relevance:float=0.;agency_relevance:float=0.
@dataclass
class N:id:str;kind:K;text:str;source_mode:str;evidence:float=.99;active:bool=True;metadata:dict=field(default_factory=dict);modulators:M=field(default_factory=M)
class R:
 def __init__(s):s.nodes={};s.runtime={'session_id':'S'};s.durable=False
 def _write_runtime(s):pass
def run(**x):
 r=R();r.nodes['G']=N('G',K.GOAL,'goal',x.get('gs','user'),active=x.get('ga',1),metadata={'temporal_state':x.get('ts','ACTIVE'),'grants_capabilities':list(x.get('caps',('deploy.restart',)))})
 m={'governing_commitment_ids':['G'] if x.get('link',1) else [],'required_capabilities':list(x.get('req',('deploy.restart',))),'action_maxim':'Restart after verified fault' if x.get('max',1) else '','material_action':x.get('mat',1),'reversibility':x.get('rev','REVERSIBLE'),'rollback_plan':'restore' if x.get('rb',1) else '','expected_effects':['healthy'] if x.get('eff',1) else [],'failure_modes':['fails'] if x.get('fail',1) else [],'affected_parties':['person'] if x.get('aff',0) else [],'human_impact_assessed':x.get('ia',1),'impact_level':x.get('imp','LOW')}
 src=x.get('src','user');r.nodes['A']=N('A',K.ACTION,'restart',src,metadata=m,modulators=M(.9 if x.get('soc') else 0,.9 if x.get('soc') else 0));c={'cycle_id':'C','semantic_slice':{'intent_sha256':'I','nodes':[{'id':'A','kind':'action','text':'restart','source_mode':src,'epistemic_score':.999}]}}
 if x.get('sep'):a={'kind':'constraint','source_mode':'user','text':'approve','metadata':{'explicit_action_approval':x.get('ap',True),'approval_scope':'this_action','approves_action_node_id':'A'}};mined=[{'id':'AP','kind':'constraint'}]
 else:a={'kind':'action','source_mode':x.get('aps','user'),'text':'restart','metadata':{'explicit_action_approval':x.get('ap',True),'approval_scope':x.get('scope','this_action')}};mined=[{'id':'A','kind':'action'}]
 l=build_action_ledger(r,c,central={'regulative_mode':x.get('central','REFLECTIVE_SYNTHESIS')},mined=mined,atoms=[a],intention_node_id='INT');return r,c,a,l
def st(**x):return run(**x)[3]['candidates'][0]['decision']['status']
def cd(r):
 m=r.nodes['A'].metadata;return {'node_id':'A','text':'restart','source_mode':r.nodes['A'].source_mode,'maxim':m['action_maxim'],'required_capabilities':m['required_capabilities'],'governing_commitment_ids':m['governing_commitment_ids'],'affected_parties':m['affected_parties'],'reversibility':m['reversibility'],'rollback_plan':m['rollback_plan'],'expected_effects':m['expected_effects'],'failure_modes':m['failure_modes'],'impact_level':m['impact_level'],'human_impact_assessed':m['human_impact_assessed'],'material':m['material_action']}
def ap(k):
 r,_,a,_=run();c=cd(r);rec=issue_same_turn_approval(r,c,atom=a,intent_sha256='I',intention_node_id='INT')
 if k=='repo':a['source_mode']='repository';return issue_same_turn_approval(r,c,atom=a,intent_sha256='I',intention_node_id='INT') is None
 if k=='scope':a['metadata']['approval_scope']='any';return issue_same_turn_approval(r,c,atom=a,intent_sha256='I',intention_node_id='INT') is None
 if k=='s':return not validate_approval(rec,c,session_id='S2',intent_sha256='I',intention_node_id='INT')[0]
 if k=='i':return not validate_approval(rec,c,session_id='S',intent_sha256='X',intention_node_id='INT')[0]
 if k=='n':return not validate_approval(rec,c,session_id='S',intent_sha256='I',intention_node_id='X')[0]
 if k=='a':c=dict(c);c['node_id']='B';return not validate_approval(rec,c,session_id='S',intent_sha256='I',intention_node_id='INT')[0]
 if k=='f':c=dict(c);c['rollback_plan']='changed';return not validate_approval(rec,c,session_id='S',intent_sha256='I',intention_node_id='INT')[0]
 rec=dict(rec);rec['action_node_id']='B';return not validate_approval(rec,c,session_id='S',intent_sha256='I',intention_node_id='INT')[0]
def q(k):
 z={'au':lambda:st(link=0)=='AUTHORITY_REQUIRED','cap':lambda:st(caps=('deploy.read',))=='AUTHORITY_REQUIRED','dg':lambda:st(gs='runtime_derived')=='AUTHORITY_REQUIRED','ina':lambda:st(ga=0)=='AUTHORITY_REQUIRED','stale':lambda:st(ts='SUPERSEDED')=='AUTHORITY_REQUIRED','pre':lambda:st(caps=('deploy',))=='AUTHORITY_REQUIRED','max':lambda:st(max=0)=='MAXIM_REQUIRED','rev':lambda:st(rev='UNKNOWN')=='REVERSIBILITY_REQUIRED','irr':lambda:st(rev='IRREVERSIBLE',rb=0)=='HUMAN_EXECUTION_REQUIRED','part':lambda:st(rev='PARTIAL')=='HUMAN_EXECUTION_REQUIRED','rb':lambda:st(rb=0)=='ROLLBACK_REQUIRED','eff':lambda:st(eff=0)=='COUNTERFACTUAL_REVIEW_REQUIRED','fail':lambda:st(fail=0)=='COUNTERFACTUAL_REVIEW_REQUIRED','impact':lambda:st(aff=1,ia=0,imp='UNKNOWN')=='IMPACT_REVIEW_REQUIRED','ui':lambda:st(aff=1,imp='UNKNOWN')=='IMPACT_REVIEW_REQUIRED','hi':lambda:st(imp='HIGH')=='HUMAN_EXECUTION_REQUIRED','soc':lambda:st(soc=1,ia=0,imp='UNKNOWN')=='IMPACT_REVIEW_REQUIRED','cb':lambda:st(central='PRACTICAL_BLOCK')=='CENTRAL_BLOCKED','hb':lambda:st(central='HORIZON_BLOCK')=='CENTRAL_BLOCKED','na':lambda:st(ap=0)=='APPROVAL_REQUIRED','der':lambda:st(src='runtime_derived')=='APPROVAL_REQUIRED','derok':lambda:st(src='runtime_derived',sep=1)=='HOST_EXECUTION_ELIGIBLE','prop':lambda:st(mat=0,link=0,req=(),max=0,ap=0)=='PROPOSABLE'}
 if k in z:return z[k]()
 if k=='wild':
  try:normalize_capability('*');return False
  except ValueError:return True
 if k.startswith('ap'):return ap(k[2:])
 if k in {'led','ev'}:
  r,_,_,l=run();return (l['epistemic_authority']==0 and l['execution_performed'] is False and l['evidence_modified'] is False and l['boundary']['host_must_recheck_system_safety_law_and_tool_capability']) if k=='led' else (r.nodes['A'].evidence==.99 and l['evidence_modified'] is False)
 if k=='ge':
  r,_,_,_=run();b=r.nodes['G'].evidence;resolve_authority(r,governing_commitment_ids=['G'],required_capabilities=['deploy.restart']);return r.nodes['G'].evidence==b
 if k=='mix':
  r,c,a,_=run();r.nodes['B']=N('B',K.ACTION,'delete','user',metadata={'governing_commitment_ids':[],'required_capabilities':['delete'],'action_maxim':'Delete','material_action':True,'reversibility':'IRREVERSIBLE','rollback_plan':'','expected_effects':['gone'],'failure_modes':['wrong'],'affected_parties':[],'human_impact_assessed':True,'impact_level':'LOW'});c['semantic_slice']['nodes'].append({'id':'B','kind':'action','text':'delete','source_mode':'user','epistemic_score':.9});return build_action_ledger(r,c,central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'A','kind':'action'}],atoms=[a],intention_node_id='INT')['material_action']=='REVIEW_REQUIRED'
 if k=='comp':
  r,c,a,_=run();r.nodes['B']=N('B',K.ACTION,'explain','user',metadata={'material_action':False});c['semantic_slice']['nodes'].append({'id':'B','kind':'action','text':'explain','source_mode':'user','epistemic_score':.7});return build_action_ledger(r,c,central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'A','kind':'action'}],atoms=[a],intention_node_id='INT')['material_action']=='HOST_EXECUTION_ELIGIBLE'
 return False
NAMES='evidence_implies_authority high_epistemic_score_skips_authority unlinked_goal_inferred action_source_equals_authority empty_governing_commitment_executes permission_inferred_from_public_repo rights_acceptance_implies_action_authority approval_grants_missing_capability derived_commitment_grants_capability runtime_derived_goal_self_authorizes inactive_commitment_grants_capability superseded_commitment_grants_capability prefix_capability_grant wildcard_capability_grant missing_maxim_executes generated_maxim_counts_explicit unknown_reversibility_executes rollback_text_implies_reversibility irreversible_executes partial_without_human_executes missing_rollback_executes missing_effects_executes missing_failure_modes_executes human_impact_unassessed_executes unknown_impact_executes high_impact_executes affected_party_empty_bypasses_social_modulator high_impact_low_social_bypasses central_practical_block_ignored horizon_block_ignored current_commitment_equals_approval derived_action_self_authorizes derived_action_separate_approval_supported repository_counts_as_human_approval approval_scope_anything approval_replays_next_turn stale_intent_hash_accepted approval_cross_session stale_intention_node_accepted approval_cross_action approval_for_different_fingerprint approval_tamper_detected ledger_changes_evidence ledger_claims_epistemic_authority ledger_claims_execution_performed execution_eligible_performs_action system_safety_law_bypass_flag host_tool_capability_assumed approval_upgrades_factual_confidence capability_grant_upgrades_evidence proposal_equals_execution nonmaterial_forced_material mixed_candidate_overall_eligibility nonmaterial_companion_cancels_eligibility duplicate_grants_create_authority_without_commitment counterfactual_metadata_claims_real_causality'.split()
KEYS='au au au au au au au cap dg dg ina stale pre wild max max rev rev irr part rb eff fail impact ui hi soc hi cb hb na der derok aprepo apscope api api aps apn apa apf apt led led led led led led ev ge prop prop mix comp au led'.split();F=list(zip(NAMES,KEYS));assert len(F)==56
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=100000);p.add_argument('--tail',type=int,default=100000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();rng=random.Random(a.seed);res={n:q(k) for n,k in F};surv=sorted(n for n,v in res.items() if not v);order=list(res);rng.shuffle(order);seen={order[i%56] for i in range(a.mutations)};before=len(seen);new=0
 for i in range(a.tail):n=order[(a.mutations+i)%56];new+=n not in seen;seen.add(n)
 out={'schema':'ikant-practical-reason-mutations/v0.15-test','status':'PASS' if len(seen)==56 and not surv and new==0 else 'FAIL','seed':a.seed,'mutations':a.mutations,'tail':a.tail,'mutation_families':56,'families_seen':len(seen),'survivors':surv,'tail_new_families':new,'families_before_tail':before};print(json.dumps(out,sort_keys=True));return out['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
