from __future__ import annotations
import argparse,json,random,sys
from dataclasses import dataclass,field
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.planning import finalize_planning

@dataclass
class N:id:str;evidence:float=.97;metadata:dict=field(default_factory=dict)
class R:
 def __init__(self):self.nodes={};self.runtime={'session_id':'S'};self.durable=False
 def _write_runtime(self):pass

def candidate(nid,status='HOST_EXECUTION_ELIGIBLE',*,material=True,caps=(),impact='LOW',rev='REVERSIBLE',rollback='restore'):
 return {'node_id':nid,'material':material,'required_capabilities':list(caps),'impact_level':impact,'reversibility':rev,'rollback_plan':rollback,'decision':{'status':status}}
DOMAINS=(('service-recovery','service.ready','service.healthy','deploy.restart'),('database-migration','db.backup','db.schema.current','db.migrate'),('credential-rotation','credential.backup','credential.rotated','auth.rotate'),('artifact-deploy','artifact.verified','artifact.deployed','deploy.release'),('backup-restore','backup.valid','data.restored','backup.restore'),('message-publication','draft.approved','message.published','publish.message'),('dependency-upgrade','tests.green','dependency.updated','dependency.update'),('data-export','scope.approved','export.ready','data.export'))
BITS=16;UNIVERSE=1<<BITS

def scenario(index:int):
 domain_name,initial,done,cap=DOMAINS[index&7]
 second=bool(index&(1<<3));initial_ok=bool(index&(1<<4));dep_good=bool(index&(1<<5));a_host=bool(index&(1<<6));b_human=bool(index&(1<<7));b_block=bool(index&(1<<8));cycle=bool(index&(1<<9));unknown=bool(index&(1<<10));cross=bool(index&(1<<11));contradict=bool(index&(1<<12));shared=bool(index&(1<<13));nonmaterial=bool(index&(1<<14));alternative=bool(index&(1<<15))
 rt=R();a_meta={'plan_id':'P','decision_problem_id':'D','plan_step_id':'a','plan_initial_conditions':[initial] if initial_ok else [],'plan_preconditions':[initial],'plan_postconditions':[done],'plan_assumptions':['environment.stable']}
 if contradict:a_meta['plan_initial_conditions']=[initial,'!'+initial]
 rt.nodes['A']=N('A',metadata=a_meta);cs=[candidate('A','HOST_EXECUTION_ELIGIBLE' if a_host else 'APPROVAL_REQUIRED',caps=(cap,))]
 if second:
  deps=['a'] if dep_good else []
  if unknown:deps=['ghost']
  rt.nodes['B']=N('B',metadata={'plan_id':'P','decision_problem_id':'D2' if cross else 'D','plan_step_id':'b','plan_depends_on':deps,'plan_preconditions':[done],'plan_postconditions':[done+'.verified'],'plan_assumptions':['environment.stable' if shared else 'second.step.valid']})
  if cycle:rt.nodes['A'].metadata['plan_depends_on']=['b'];rt.nodes['B'].metadata['plan_depends_on']=['a']
  bstatus='CENTRAL_BLOCKED' if b_block else ('HUMAN_EXECUTION_REQUIRED' if b_human else 'HOST_EXECUTION_ELIGIBLE');cs.append(candidate('B',bstatus,caps=(cap+'.verify',),rev='IRREVERSIBLE' if b_human else 'REVERSIBLE',rollback='' if b_human else 'restore'))
 if nonmaterial:rt.nodes['N']=N('N',metadata={'plan_id':'P','decision_problem_id':'D','plan_step_id':'n'});cs.append(candidate('N','PROPOSABLE',material=False,impact='NONE',rev='UNKNOWN',rollback=''))
 if alternative:rt.nodes['Q']=N('Q',metadata={'plan_id':'Q','decision_problem_id':'D','plan_step_id':'q','plan_initial_conditions':['alt.ready'],'plan_preconditions':['alt.ready'],'plan_postconditions':['alt.done'],'plan_assumptions':['alt.stable']});cs.append(candidate('Q','HOST_EXECUTION_ELIGIBLE',caps=(cap+'.alt',)))
 practical={'action_ledger':{'candidates':cs}};cycleobj={'cycle_id':f'C{index}','semantic_slice':{'intent_sha256':f'I{index}'}};before={k:v.evidence for k,v in rt.nodes.items()};out=finalize_planning(rt,cycleobj,practical,central={});ledger=out['plan_ledger'];assert before=={k:v.evidence for k,v in rt.nodes.items()};assert ledger['epistemic_authority']==0 and ledger['execution_authority']==0 and ledger['execution_performed'] is False
 for p in ledger['plans']:
  assert p['execution_eligible'] is False
  if p['status']=='PLAN_HOST_REVALIDATION_REQUIRED':
   rows=[r for r in p['steps'] if r['material']];assert rows and all(r['action_status']=='HOST_EXECUTION_ELIGIBLE' for r in rows) and p['structural_valid'] and p['world']['valid']
  if any(r['action_status']=='CENTRAL_BLOCKED' for r in p['steps'] if r['material']):assert p['status']=='PLAN_BLOCKED'
 return (ledger['overall_status'],tuple((p['plan_id'],p['status'],p['structural_valid'],p['world']['valid'],round(p['counterfactual']['max_dependency'],3),len(p['rollback']['irreversible_steps'])) for p in ledger['plans']),tuple(ledger['decision_lattice']['nondominated_plan_ids']),len(ledger['decision_lattice']['dominance_edges']))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);order=list(range(UNIVERSE));rng.shuffle(order);seen=set();covered=set()
 for i in range(a.cases):idx=order[i%UNIVERSE];covered.add(idx);seen.add(scenario(idx))
 before=len(seen);tail_new=0
 for i in range(a.tail):idx=order[(a.cases+i)%UNIVERSE];sig=scenario(idx);tail_new+=sig not in seen;seen.add(sig)
 expected=min(a.cases,UNIVERSE);status='PASS' if len(covered)==expected and tail_new==0 else 'FAIL';out={'schema':'ikant-planning-stress/v0.16-test','status':status,'seed':a.seed,'cases':a.cases,'tail':a.tail,'domains':len(DOMAINS),'explicit_universe':UNIVERSE,'covered_configurations':len(covered),'expected_coverage':expected,'causal_signatures':len(seen),'signatures_before_tail':before,'tail_new_signatures':tail_new};print(json.dumps(out,sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
