from __future__ import annotations
import argparse, json, random, sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.action_governance import build_action_ledger

class K(str,Enum):GOAL='goal';CONSTRAINT='constraint';ACTION='action'
@dataclass
class M:social_relevance:float=0.;agency_relevance:float=0.
@dataclass
class N:
 id:str;kind:K;text:str;source_mode:str;evidence:float=.8;active:bool=True;metadata:dict=field(default_factory=dict);modulators:M=field(default_factory=M)
class R:
 def __init__(self):self.nodes={};self.runtime={'session_id':'S'};self.durable=False
 def _write_runtime(self):pass

BITS=16;UNIVERSE=1<<BITS

def scenario(index:int):
 b=[bool(index&(1<<i)) for i in range(BITS)]
 (material,linked,cap_required,cap_granted,goal_active,goal_trusted,approve,maxim,impact,impact_assessed,high_impact,reversible,rollback,counterfactual,central_block,derived_action)=b
 rt=R();caps=['deploy.restart'] if cap_granted else ['deploy.read']
 rt.nodes['G']=N('G',K.GOAL,'keep service healthy','user' if goal_trusted else 'runtime_derived',active=goal_active,metadata={'temporal_state':'ACTIVE','grants_capabilities':caps})
 meta={'governing_commitment_ids':['G'] if linked else [],'required_capabilities':['deploy.restart'] if cap_required else [],'action_maxim':'Restart service after verified fault' if maxim else '','material_action':material,'reversibility':'REVERSIBLE' if reversible else 'IRREVERSIBLE','rollback_plan':'restore prior instance' if rollback else '','expected_effects':['service healthy'] if counterfactual else [],'failure_modes':['restart fails'] if counterfactual else [],'human_impact_assessed':impact_assessed,'impact_level':'HIGH' if high_impact else ('LOW' if impact else 'NONE'),'affected_parties':['person:1'] if impact else []}
 rt.nodes['A']=N('A',K.ACTION,'restart service','runtime_derived' if derived_action else 'user',metadata=meta,modulators=M(.8 if impact else 0,.8 if impact else 0))
 cycle={'cycle_id':'C','semantic_slice':{'intent_sha256':'I','nodes':[{'id':'A','kind':'action','text':'restart service','source_mode':rt.nodes['A'].source_mode,'epistemic_score':.99}]}}
 if derived_action:
  atom={'kind':'constraint','source_mode':'user','text':'approve proposed restart','metadata':{'explicit_action_approval':approve,'approval_scope':'this_action','approves_action_node_id':'A'}}
  mined=[{'id':'AP','kind':'constraint'}]
 else:
  atom={'kind':'action','source_mode':'user','text':'restart service','metadata':{'explicit_action_approval':approve,'approval_scope':'this_action'}}
  mined=[{'id':'A','kind':'action'}]
 ledger=build_action_ledger(rt,cycle,central={'regulative_mode':'PRACTICAL_BLOCK' if central_block else 'REFLECTIVE_SYNTHESIS'},mined=mined,atoms=[atom],intention_node_id='INT')
 c=ledger['candidates'][0];d=c['decision']
 # Consequence signature intentionally excludes raw input bits.
 sig=(d['status'],d['execution_eligible'],d['proposal_allowed'],d['human_execution_required'],tuple(d['authority']['missing_capabilities']),d['authority']['explicit_attribution'],bool(d['approval_valid']),ledger['material_action'])
 # Safety oracle independent of implementation branch order.
 if d['execution_eligible']:
  assert material and linked and goal_active and goal_trusted and approve and maxim and (not impact or impact_assessed) and not high_impact and reversible and rollback and counterfactual and not central_block
  if cap_required: assert cap_granted
  assert ledger['execution_performed'] is False and ledger['epistemic_authority']==0.0
 if central_block: assert d['status']=='CENTRAL_BLOCKED'
 elif not material: assert d['status']=='PROPOSABLE'
 if impact and not impact_assessed and not central_block and material and maxim: assert d['status']=='IMPACT_REVIEW_REQUIRED'
 return sig

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed)
 order=list(range(UNIVERSE));rng.shuffle(order);seen=set();covered=set()
 for i in range(a.cases):
  idx=order[i%UNIVERSE];covered.add(idx);seen.add(scenario(idx))
 before=len(seen);tail_new=0
 for i in range(a.tail):
  idx=order[(a.cases+i)%UNIVERSE];s=scenario(idx)
  if s not in seen:tail_new+=1;seen.add(s)
 expected_coverage=min(a.cases,UNIVERSE)
 out={'schema':'ikant-practical-reason-stress/v0.15-test','status':'PASS' if len(covered)==expected_coverage and tail_new==0 else 'FAIL','seed':a.seed,'cases':a.cases,'tail':a.tail,'explicit_universe':UNIVERSE,'expected_coverage':expected_coverage,'covered_configurations':len(covered),'full_universe_covered':len(covered)==UNIVERSE,'causal_signatures':len(seen),'signatures_before_tail':before,'tail_new_signatures':tail_new}
 print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
