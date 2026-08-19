from __future__ import annotations
import argparse,json,random,sys
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.execution_handoff import build_execution_ledger
from ikant.execution_receipts import EXECUTION_RECEIPT_SCHEMA,REVALIDATION_RECEIPT_SCHEMA,record_execution_receipt,seal_receipt
from ikant.outcome_reconciliation import reconcile_execution_outcome

@dataclass
class N:evidence:float=.97
class R:
 def __init__(s):s.nodes={'A':N(),'B':N()};s.runtime={'session_id':'S'};s.durable=False
 def _write_runtime(s):pass
DOMAINS=(
 ('service-recovery','service.ready','service.healthy','deploy.restart'),
 ('database-migration','db.backup','db.schema.current','db.migrate'),
 ('credential-rotation','credential.backup','credential.rotated','auth.rotate'),
 ('artifact-deploy','artifact.verified','artifact.deployed','deploy.release'),
 ('backup-restore','backup.valid','data.restored','backup.restore'),
 ('message-publication','draft.approved','message.published','publish.message'),
 ('dependency-upgrade','tests.green','dependency.updated','dependency.update'),
 ('data-export','scope.approved','export.ready','data.export'),
)
UNIVERSE=1<<16

def cand(node,status,fp,ap,cap):return {'node_id':node,'fingerprint':fp,'required_capabilities':[cap],'decision':{'status':status,'approval':{'receipt_sha256':ap} if ap else None}}
def rv(env,bad=False):
 p={'schema':REVALIDATION_RECEIPT_SCHEMA,'actor_type':'host','session_id':env['session_id'],'cycle_id':env['cycle_id'],'intent_sha256':env['intent_sha256'],'handoff_id':env['handoff_id'],'idempotency_key':env['idempotency_key'],'action_fingerprint':env['action_fingerprint'],'action_ledger_sha256':env['action_ledger_sha256'],'plan_ledger_sha256':env['plan_ledger_sha256'],'system_safety_law_checked':True,'tool_capability_checked':not bad,'current_action_status':'HOST_EXECUTION_ELIGIBLE','grants_runtime_execution_authority':False,'executes_action':False};return seal_receipt(p)
def rec(env,outcome,bind_bad=False,conflict=False):
 obs=list(env['declared_postconditions'])
 if conflict and obs:obs=['!'+obs[0].lstrip('!')]
 p={'schema':EXECUTION_RECEIPT_SCHEMA,'actor_type':'human' if env['handoff_kind']=='HUMAN' else 'host','session_id':env['session_id'],'cycle_id':'OLD' if bind_bad else env['cycle_id'],'intent_sha256':env['intent_sha256'],'handoff_id':env['handoff_id'],'idempotency_key':env['idempotency_key'],'action_fingerprint':env['action_fingerprint'],'action_ledger_sha256':env['action_ledger_sha256'],'plan_ledger_sha256':env['plan_ledger_sha256'],'outcome':outcome,'execution_ref':'tool:'+env['step_id'] if outcome in {'EXECUTED','FAILED'} else '','observed_predicates':obs,'runtime_epistemic_authority':0.0,'grants_runtime_execution_authority':False,'causes_runtime_execution':False};return seal_receipt(p)
def scenario(i):
 name,pre,post,cap=DOMAINS[i&7];human=bool(i&(1<<3));review=bool(i&(1<<4));block=bool(i&(1<<5));dependent=bool(i&(1<<6));drift=bool(i&(1<<7));missing_fp=bool(i&(1<<8));missing_ap=bool(i&(1<<9));bad_rv=bool(i&(1<<10));bind_bad=bool(i&(1<<11));failed=bool(i&(1<<12));declined=bool(i&(1<<13));obs_conflict=bool(i&(1<<14));replay_conflict=bool(i&(1<<15))
 if block:plan_status='PLAN_BLOCKED'
 elif review:plan_status='PLAN_REVIEW_REQUIRED'
 elif human:plan_status='PLAN_HUMAN_EXECUTION_REQUIRED'
 else:plan_status='PLAN_HOST_REVALIDATION_REQUIRED'
 action_status='HUMAN_EXECUTION_REQUIRED' if human else 'HOST_EXECUTION_ELIGIBLE';step_status='APPROVAL_REQUIRED' if drift else action_status
 rt=R();cands=[cand('A',action_status,'' if missing_fp else 'fp:A','' if missing_ap else 'ap:A',cap)];steps=[{'step_id':'a','action_node_id':'A','material':True,'action_status':step_status,'depends_on':[],'preconditions':[pre],'postconditions':[post]}]
 if dependent:
  cands.append(cand('B',action_status,'fp:B','ap:B',cap+'.verify'));steps.append({'step_id':'b','action_node_id':'B','material':True,'action_status':action_status,'depends_on':['a'],'preconditions':[post],'postconditions':[post+'.verified']})
 practical={'action_ledger':{'sha256':'ACT:'+name,'candidates':cands},'planning':{'plan_ledger':{'sha256':'PLAN:'+name,'plans':[{'plan_id':'P','decision_problem_id':'D','status':plan_status,'steps':steps}]}}}
 cycle={'cycle_id':'C:'+str(i),'semantic_slice':{'intent_sha256':'I:'+name}}
 before={k:v.evidence for k,v in rt.nodes.items()};ledger=build_execution_ledger(rt,cycle,practical);assert before=={k:v.evidence for k,v in rt.nodes.items()};assert ledger['execution_authority']==0 and ledger['execution_performed'] is False
 env=ledger['handoffs'][-1]
 outcome='DECLINED' if declined else ('FAILED' if failed else 'EXECUTED');rr=rec(env,outcome,bind_bad,obs_conflict);reval=rv(env,bad_rv) if env['handoff_kind']=='HOST' else None
 first=record_execution_receipt(rt,env,rr,revalidation_receipt=reval)
 recon=None
 if first['status'] in {'RECORDED','IDEMPOTENT_REPLAY'}:recon=reconcile_execution_outcome(env,rr);assert recon['next_step_auto_advance'] is False and recon['epistemic_authority']==0
 second=None
 if replay_conflict and first['status']=='RECORDED':
  rr2=dict(rr);rr2['execution_ref']='tool:other';rr2=seal_receipt(rr2);second=record_execution_receipt(rt,env,rr2,revalidation_receipt=reval)['status'];assert second=='RECEIPT_CONFLICT'
 if plan_status in {'PLAN_BLOCKED','PLAN_REVIEW_REQUIRED'}:assert all(x['handoff_state']=='NOT_HANDOFFABLE' for x in ledger['handoffs'])
 if drift or missing_fp or missing_ap:assert ledger['handoffs'][0]['handoff_state']=='NOT_HANDOFFABLE'
 if dependent:assert ledger['handoffs'][-1]['handoff_state'] in {'PREDECESSOR_RECONCILIATION_REQUIRED','NOT_HANDOFFABLE'}
 return (name,plan_status,tuple(x['handoff_state'] for x in ledger['handoffs']),first['status'],None if recon is None else recon['status'],second)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);order=list(range(UNIVERSE));rng.shuffle(order);seen=set();covered=set()
 for j in range(a.cases):idx=order[j%UNIVERSE];covered.add(idx);seen.add(scenario(idx))
 before=len(seen);tail_new=0
 for j in range(a.tail):idx=order[(a.cases+j)%UNIVERSE];sig=scenario(idx);tail_new+=sig not in seen;seen.add(sig)
 expected=min(a.cases,UNIVERSE);saturated=a.cases>=UNIVERSE;status='PASS' if len(covered)==expected and (not saturated or tail_new==0) else 'FAIL';print(json.dumps({'schema':'ikant-execution-stress/v0.17-test','status':status,'seed':a.seed,'cases':a.cases,'tail':a.tail,'domains':len(DOMAINS),'explicit_universe':UNIVERSE,'covered_configurations':len(covered),'expected_coverage':expected,'consequence_signatures':len(seen),'signatures_before_tail':before,'tail_new_signatures':tail_new,'saturated':saturated and tail_new==0},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
