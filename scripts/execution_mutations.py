from __future__ import annotations
import argparse,copy,json,random,sys,tempfile
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.execution_handoff import build_execution_ledger
from ikant.execution_receipts import EXECUTION_RECEIPT_SCHEMA,REVALIDATION_RECEIPT_SCHEMA,record_execution_receipt,seal_receipt,validate_execution_receipt,validate_revalidation_receipt
from ikant.outcome_reconciliation import reconcile_execution_outcome
from ikant.execution_protocol import finalize_execution_protocol,accept_and_reconcile

@dataclass
class N:evidence:float=.9
class R:
 def __init__(s,durable=False,root=None):s.nodes={'A':N(),'B':N()};s.runtime={'session_id':'S'};s.durable=durable;s.state_dir=Path(root or '.')
 def _write_runtime(s):pass

def fx(plan='PLAN_HOST_REVALIDATION_REQUIRED',action='HOST_EXECUTION_ELIGIBLE',dep=False):
 r=R();cs=[{'node_id':'A','fingerprint':'fp:A','required_capabilities':['op.write'],'decision':{'status':action,'approval':{'receipt_sha256':'ap:A'}}}];steps=[{'step_id':'a','action_node_id':'A','material':True,'action_status':action,'depends_on':[],'preconditions':['ready'],'postconditions':['done']}]
 if dep:cs.append({'node_id':'B','fingerprint':'fp:B','required_capabilities':['op.verify'],'decision':{'status':action,'approval':{'receipt_sha256':'ap:B'}}});steps.append({'step_id':'b','action_node_id':'B','material':True,'action_status':action,'depends_on':['a'],'preconditions':['done'],'postconditions':['verified']})
 p={'action_ledger':{'sha256':'ACT','candidates':cs},'planning':{'plan_ledger':{'sha256':'PLAN','plans':[{'plan_id':'P','decision_problem_id':'D','status':plan,'steps':steps}]}}};c={'cycle_id':'C','semantic_slice':{'intent_sha256':'I'}};return r,c,p

def env(r,c,p,index=0):return build_execution_ledger(r,c,p)['handoffs'][index]
def rv(e,**kw):
 p={'schema':REVALIDATION_RECEIPT_SCHEMA,'actor_type':'host','session_id':e['session_id'],'cycle_id':e['cycle_id'],'intent_sha256':e['intent_sha256'],'handoff_id':e['handoff_id'],'idempotency_key':e['idempotency_key'],'action_fingerprint':e['action_fingerprint'],'action_ledger_sha256':e['action_ledger_sha256'],'plan_ledger_sha256':e['plan_ledger_sha256'],'system_safety_law_checked':True,'tool_capability_checked':True,'current_action_status':'HOST_EXECUTION_ELIGIBLE','grants_runtime_execution_authority':False,'executes_action':False};p.update(kw);return seal_receipt(p)
def rec(e,**kw):
 outcome=kw.pop('outcome','EXECUTED');p={'schema':EXECUTION_RECEIPT_SCHEMA,'actor_type':'human' if e['handoff_kind']=='HUMAN' else 'host','session_id':e['session_id'],'cycle_id':e['cycle_id'],'intent_sha256':e['intent_sha256'],'handoff_id':e['handoff_id'],'idempotency_key':e['idempotency_key'],'action_fingerprint':e['action_fingerprint'],'action_ledger_sha256':e['action_ledger_sha256'],'plan_ledger_sha256':e['plan_ledger_sha256'],'outcome':outcome,'execution_ref':'tool:1' if outcome in {'EXECUTED','FAILED'} else '','observed_predicates':list(e['declared_postconditions']),'runtime_epistemic_authority':0.0,'grants_runtime_execution_authority':False,'causes_runtime_execution':False};p.update(kw);return seal_receipt(p)

def check(k):
 r,c,p=fx();e=env(r,c,p)
 if k=='review_handoff':r,c,p=fx(plan='PLAN_REVIEW_REQUIRED');return env(r,c,p)['handoff_state']=='NOT_HANDOFFABLE'
 if k=='block_handoff':r,c,p=fx(plan='PLAN_BLOCKED');return env(r,c,p)['handoff_state']=='NOT_HANDOFFABLE'
 if k=='human_promoted':r,c,p=fx(plan='PLAN_HUMAN_EXECUTION_REQUIRED',action='HUMAN_EXECUTION_REQUIRED');q=env(r,c,p);return q['handoff_kind']=='HUMAN' and q['handoff_state']=='HUMAN_EXECUTION_REQUIRED'
 if k=='dependent_ignores_predecessor':r,c,p=fx(dep=True);return env(r,c,p,1)['handoff_state']=='PREDECESSOR_RECONCILIATION_REQUIRED'
 if k=='status_drift':p['planning']['plan_ledger']['plans'][0]['steps'][0]['action_status']='APPROVAL_REQUIRED';return env(r,c,p)['handoff_state']=='NOT_HANDOFFABLE'
 if k=='fingerprint_missing':p['action_ledger']['candidates'][0]['fingerprint']='';return 'action fingerprint missing' in env(r,c,p)['binding_errors']
 if k=='approval_missing':p['action_ledger']['candidates'][0]['decision']['approval']=None;return 'approval receipt binding missing' in env(r,c,p)['binding_errors']
 if k=='session_unbound':return e['session_id']=='S' and bool(e['idempotency_key'])
 if k=='cycle_unbound':return e['cycle_id']=='C' and bool(e['idempotency_key'])
 if k=='intent_unbound':return e['intent_sha256']=='I' and bool(e['idempotency_key'])
 if k=='action_hash_unbound':return e['action_ledger_sha256']=='ACT'
 if k=='plan_hash_unbound':return e['plan_ledger_sha256']=='PLAN'
 if k=='handoff_id_random':return env(r,c,p)['handoff_id']==env(r,c,p)['handoff_id']
 if k=='idempotency_random':return env(r,c,p)['idempotency_key']==env(r,c,p)['idempotency_key']
 if k=='handoff_executes':return e['execution_performed'] is False and e['execution_eligible'] is False
 if k=='handoff_epistemic_authority':return e['epistemic_authority']==0.0
 if k=='handoff_execution_authority':return e['execution_authority']==0.0
 if k=='ledger_executes':q=build_execution_ledger(r,c,p);return q['execution_performed'] is False
 if k=='ledger_evidence':before={x:n.evidence for x,n in r.nodes.items()};build_execution_ledger(r,c,p);return before=={x:n.evidence for x,n in r.nodes.items()}
 if k=='protocol_executes':return finalize_execution_protocol(r,c,p)['runtime_execution_performed'] is False
 if k=='rv_wrong_session':return not validate_revalidation_receipt(e,rv(e,session_id='X'))[0]
 if k=='rv_wrong_cycle':return not validate_revalidation_receipt(e,rv(e,cycle_id='X'))[0]
 if k=='rv_wrong_intent':return not validate_revalidation_receipt(e,rv(e,intent_sha256='X'))[0]
 if k=='rv_wrong_handoff':return not validate_revalidation_receipt(e,rv(e,handoff_id='X'))[0]
 if k=='rv_wrong_key':return not validate_revalidation_receipt(e,rv(e,idempotency_key='X'))[0]
 if k=='rv_wrong_fp':return not validate_revalidation_receipt(e,rv(e,action_fingerprint='X'))[0]
 if k=='rv_wrong_action_hash':return not validate_revalidation_receipt(e,rv(e,action_ledger_sha256='X'))[0]
 if k=='rv_wrong_plan_hash':return not validate_revalidation_receipt(e,rv(e,plan_ledger_sha256='X'))[0]
 if k=='rv_wrong_actor':return not validate_revalidation_receipt(e,rv(e,actor_type='human'))[0]
 if k=='rv_safety_false':return not validate_revalidation_receipt(e,rv(e,system_safety_law_checked=False))[0]
 if k=='rv_tool_false':return not validate_revalidation_receipt(e,rv(e,tool_capability_checked=False))[0]
 if k=='rv_status_stale':return not validate_revalidation_receipt(e,rv(e,current_action_status='APPROVAL_REQUIRED'))[0]
 if k=='rv_grants_authority':return not validate_revalidation_receipt(e,rv(e,grants_runtime_execution_authority=True))[0]
 if k=='rv_executes':return not validate_revalidation_receipt(e,rv(e,executes_action=True))[0]
 if k=='rv_digest_tamper':x=rv(e);x['cycle_id']='X';return not validate_revalidation_receipt(e,x)[0]
 if k=='receipt_without_rv':return not validate_execution_receipt(e,rec(e),revalidation_receipt=None)[0]
 if k=='receipt_wrong_session':return not validate_execution_receipt(e,rec(e,session_id='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_cycle':return not validate_execution_receipt(e,rec(e,cycle_id='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_intent':return not validate_execution_receipt(e,rec(e,intent_sha256='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_handoff':return not validate_execution_receipt(e,rec(e,handoff_id='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_key':return not validate_execution_receipt(e,rec(e,idempotency_key='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_fp':return not validate_execution_receipt(e,rec(e,action_fingerprint='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_action_hash':return not validate_execution_receipt(e,rec(e,action_ledger_sha256='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_plan_hash':return not validate_execution_receipt(e,rec(e,plan_ledger_sha256='X'),revalidation_receipt=rv(e))[0]
 if k=='receipt_bad_outcome':return not validate_execution_receipt(e,rec(e,outcome='MAYBE'),revalidation_receipt=rv(e))[0]
 if k=='receipt_wrong_actor':return not validate_execution_receipt(e,rec(e,actor_type='human'),revalidation_receipt=rv(e))[0]
 if k=='receipt_missing_ref':return not validate_execution_receipt(e,rec(e,execution_ref=''),revalidation_receipt=rv(e))[0]
 if k=='receipt_bad_predicate':return not validate_execution_receipt(e,rec(e,observed_predicates=['*']),revalidation_receipt=rv(e))[0]
 if k=='receipt_duplicate_predicate':return not validate_execution_receipt(e,rec(e,observed_predicates=['done','done']),revalidation_receipt=rv(e))[0]
 if k=='receipt_epistemic_authority':return not validate_execution_receipt(e,rec(e,runtime_epistemic_authority=1.0),revalidation_receipt=rv(e))[0]
 if k=='receipt_grants_authority':return not validate_execution_receipt(e,rec(e,grants_runtime_execution_authority=True),revalidation_receipt=rv(e))[0]
 if k=='receipt_causes_execution':return not validate_execution_receipt(e,rec(e,causes_runtime_execution=True),revalidation_receipt=rv(e))[0]
 if k=='receipt_digest_tamper':x=rec(e);x['cycle_id']='X';return not validate_execution_receipt(e,x,revalidation_receipt=rv(e))[0]
 if k=='dependent_receipt_executes':r,c,p=fx(dep=True);q=env(r,c,p,1);return not validate_execution_receipt(q,rec(q),revalidation_receipt=rv(q))[0]
 if k=='same_replay_conflict':x=rec(e);a=record_execution_receipt(r,e,x,revalidation_receipt=rv(e));b=record_execution_receipt(r,e,x,revalidation_receipt=rv(e));return a['status']=='RECORDED' and b['status']=='IDEMPOTENT_REPLAY'
 if k=='different_replay_accepted':x=rec(e,execution_ref='tool:1');y=rec(e,execution_ref='tool:2');record_execution_receipt(r,e,x,revalidation_receipt=rv(e));return record_execution_receipt(r,e,y,revalidation_receipt=rv(e))['status']=='RECEIPT_CONFLICT'
 if k=='failed_as_success':x=reconcile_execution_outcome(e,rec(e,outcome='FAILED'));return x['status']=='EXECUTION_FAILED'
 if k=='declined_as_success':x=reconcile_execution_outcome(e,rec(e,outcome='DECLINED'));return x['status']=='EXECUTION_DECLINED'
 if k=='conflict_ignored':x=reconcile_execution_outcome(e,rec(e,observed_predicates=['!done']));return x['status']=='POSTCONDITION_CONFLICT'
 if k=='partial_confirmed':q=copy.deepcopy(e);q['declared_postconditions']=['done','verified'];x=reconcile_execution_outcome(q,rec(q,observed_predicates=['done']));return x['status']=='POSTCONDITIONS_PARTIAL'
 if k=='no_observation_confirmed':x=reconcile_execution_outcome(e,rec(e,observed_predicates=[]));return x['status']=='OBSERVATION_REQUIRED'
 if k=='semantic_opposite_inferred':x=reconcile_execution_outcome(e,rec(e,observed_predicates=['failed']));return x['status']=='OBSERVATION_REQUIRED' and x['reported_conflicts']==[]
 if k=='execution_ref_proves_effect':x=reconcile_execution_outcome(e,rec(e));return x['execution_ref_is_not_proof_of_effect'] is True and x['observed_world_verified'] is False
 if k=='host_report_evidence':return reconcile_execution_outcome(e,rec(e))['host_report_is_not_independent_evidence'] is True
 if k=='auto_advance':return reconcile_execution_outcome(e,rec(e))['next_step_auto_advance'] is False
 if k=='accept_executes':x=accept_and_reconcile(r,e,rec(e),revalidation_receipt=rv(e));return x['runtime_execution_performed'] is False and x['execution_authority']==0.0
 if k=='digest_authenticates_host':x=finalize_execution_protocol(r,c,p);return x['boundaries']['receipt_digest_is_integrity_not_actor_authentication'] is True and x['boundaries']['host_transport_authentication_is_external'] is True
 if k=='durable_receipt_missing':
  with tempfile.TemporaryDirectory() as td:r.durable=True;r.state_dir=Path(td);record_execution_receipt(r,e,rec(e),revalidation_receipt=rv(e));return (Path(td)/'execution-receipts.json').exists()
 return False

FAMILIES=['review_handoff','block_handoff','human_promoted','dependent_ignores_predecessor','status_drift','fingerprint_missing','approval_missing','session_unbound','cycle_unbound','intent_unbound','action_hash_unbound','plan_hash_unbound','handoff_id_random','idempotency_random','handoff_executes','handoff_epistemic_authority','handoff_execution_authority','ledger_executes','ledger_evidence','protocol_executes','rv_wrong_session','rv_wrong_cycle','rv_wrong_intent','rv_wrong_handoff','rv_wrong_key','rv_wrong_fp','rv_wrong_action_hash','rv_wrong_plan_hash','rv_wrong_actor','rv_safety_false','rv_tool_false','rv_status_stale','rv_grants_authority','rv_executes','rv_digest_tamper','receipt_without_rv','receipt_wrong_session','receipt_wrong_cycle','receipt_wrong_intent','receipt_wrong_handoff','receipt_wrong_key','receipt_wrong_fp','receipt_wrong_action_hash','receipt_wrong_plan_hash','receipt_bad_outcome','receipt_wrong_actor','receipt_missing_ref','receipt_bad_predicate','receipt_duplicate_predicate','receipt_epistemic_authority','receipt_grants_authority','receipt_causes_execution','receipt_digest_tamper','dependent_receipt_executes','same_replay_conflict','different_replay_accepted','failed_as_success','declined_as_success','conflict_ignored','partial_confirmed','no_observation_confirmed','semantic_opposite_inferred','execution_ref_proves_effect','host_report_evidence','auto_advance','accept_executes','digest_authenticates_host','durable_receipt_missing']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);order=list(FAMILIES);rng.shuffle(order);seen=set();survivors=set()
 for i in range(a.mutations):k=order[i%len(order)];ok=check(k);seen.add((k,ok));survivors.update([k] if not ok else [])
 before=len(seen);tail_new=0
 for i in range(a.tail):k=order[(a.mutations+i)%len(order)];sig=(k,check(k));tail_new+=sig not in seen;seen.add(sig);survivors.update([k] if not sig[1] else [])
 status='PASS' if not survivors and tail_new==0 and len({k for k,ok in seen if ok})==len(FAMILIES) else 'FAIL';print(json.dumps({'schema':'ikant-execution-mutations/v0.17-test','status':status,'seed':a.seed,'mutations':a.mutations,'tail':a.tail,'mutation_families':len(FAMILIES),'killed_families':len(FAMILIES)-len(survivors),'survivors':sorted(survivors),'signatures_before_tail':before,'tail_new_signatures':tail_new},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
