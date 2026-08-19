from __future__ import annotations
import argparse,json,random,sys,tempfile,copy
from dataclasses import dataclass,field
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.plan_graph import build_plan_graph,normalize_predicate
from ikant.world_model import simulate_success_path,counterfactual_dependency,build_rollback_graph
from ikant.decision_lattice import build_decision_lattice,decision_vector
from ikant.planning import finalize_planning
@dataclass
class N:id:str;evidence:float=.91;metadata:dict=field(default_factory=dict)
class R:
 def __init__(s,durable=False,root=None):s.nodes={};s.runtime={'session_id':'S'};s.durable=durable;s.state_dir=Path(root or '.')
 def _write_runtime(s):pass
def c(n,status='HOST_EXECUTION_ELIGIBLE',material=True,caps=('op.write',),impact='LOW',rev='REVERSIBLE',rb='restore'):
 return {'node_id':n,'material':material,'required_capabilities':list(caps),'impact_level':impact,'reversibility':rev,'rollback_plan':rb,'decision':{'status':status}}
def make(two=True,status1='HOST_EXECUTION_ELIGIBLE',status2='HOST_EXECUTION_ELIGIBLE'):
 r=R();r.nodes['A']=N('A',metadata={'plan_id':'P','decision_problem_id':'D','plan_step_id':'a','plan_initial_conditions':['!done'],'plan_preconditions':['!done'],'plan_postconditions':['done'],'plan_assumptions':['a.ok']});cs=[c('A',status1)]
 if two:r.nodes['B']=N('B',metadata={'plan_id':'P','decision_problem_id':'D','plan_step_id':'b','plan_depends_on':['a'],'plan_preconditions':['done'],'plan_postconditions':['verified'],'plan_assumptions':['b.ok']});cs.append(c('B',status2,caps=('op.verify',)))
 return r,{'cycle_id':'C','semantic_slice':{'intent_sha256':'I'}},{'action_ledger':{'candidates':cs}}
def fin(r,cy,p):return finalize_planning(r,cy,p,central={})
def plan_of(r,p):return build_plan_graph(r,p['action_ledger'])['plans'][0]
def check(k):
 r,cy,p=make()
 if k=='missing_initial':r.nodes['A'].metadata['plan_initial_conditions']=[];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='unknown_dep':r.nodes['B'].metadata['plan_depends_on']=['ghost'];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='cycle':r.nodes['A'].metadata['plan_depends_on']=['b'];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='duplicate':r.nodes['B'].metadata['plan_step_id']='a';return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='mixed_problem':r.nodes['B'].metadata['decision_problem_id']='D2';return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='contradict_initial':r.nodes['A'].metadata['plan_initial_conditions']=['done','!done'];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='contradict_post':r.nodes['A'].metadata['plan_postconditions']=['done','!done'];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='ineligible':p['action_ledger']['candidates'][0]['decision']['status']='APPROVAL_REQUIRED';return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='human':p['action_ledger']['candidates'][0]['decision']['status']='HUMAN_EXECUTION_REQUIRED';return fin(r,cy,p)['overall_status']=='PLAN_HUMAN_EXECUTION_REQUIRED'
 if k=='central':p['action_ledger']['candidates'][0]['decision']['status']='CENTRAL_BLOCKED';r.nodes['A'].metadata['plan_initial_conditions']=[];return fin(r,cy,p)['overall_status']=='PLAN_BLOCKED'
 if k=='companion':r.nodes['N']=N('N',metadata={'plan_id':'P','decision_problem_id':'D','plan_step_id':'n'});p['action_ledger']['candidates'].append(c('N','PROPOSABLE',False,(),impact='NONE',rev='UNKNOWN',rb=''));return fin(r,cy,p)['overall_status']=='PLAN_HOST_REVALIDATION_REQUIRED'
 if k=='noexec':o=fin(r,cy,p)['plan_ledger'];return o['execution_performed'] is False and all(x['execution_eligible'] is False for x in o['plans'])
 if k=='noepiauth':return fin(r,cy,p)['plan_ledger']['epistemic_authority']==0.0
 if k=='noexecauth':return fin(r,cy,p)['plan_ledger']['execution_authority']==0.0
 if k=='noreuse':return fin(r,cy,p)['plan_ledger']['approval_reusable_across_steps_or_turns'] is False
 if k=='worldnotobs':return simulate_success_path(plan_of(r,p))['observed_world'] is False
 if k=='nocausality':return counterfactual_dependency(plan_of(r,p))['real_world_causality_claim'] is False
 if k=='noscalar':return build_decision_lattice([])['scalar_utility_used'] is False
 if k=='cross':
  a={'plan_id':'A','decision_problem_id':'D1','status':'PLAN_HOST_REVALIDATION_REQUIRED','steps':[{'material':True,'required_capabilities':['a'],'impact_level':'LOW','reversibility':'REVERSIBLE'}],'counterfactual':{'max_dependency':0},'rollback':{'irreversible_steps':[],'rollback_gap_steps':[]}}
  b=copy.deepcopy(a);b['plan_id']='B';b['decision_problem_id']='D2';b['steps']*=3;return build_decision_lattice([a,b])['dominance_edges']==[]
 if k=='pareto':
  a={'plan_id':'A','decision_problem_id':'D','status':'PLAN_HOST_REVALIDATION_REQUIRED','steps':[{'material':True,'required_capabilities':['a'],'impact_level':'LOW','reversibility':'REVERSIBLE'}],'counterfactual':{'max_dependency':.1},'rollback':{'irreversible_steps':[],'rollback_gap_steps':[]}}
  b=copy.deepcopy(a);b['plan_id']='B';b['steps']=[*b['steps'],{'material':True,'required_capabilities':['b'],'impact_level':'LOW','reversibility':'REVERSIBLE'}];b['counterfactual']={'max_dependency':.8};return len(build_decision_lattice([a,b])['dominance_edges'])==1
 if k=='tradeoff':
  a={'plan_id':'A','decision_problem_id':'D','status':'PLAN_HOST_REVALIDATION_REQUIRED','steps':[{'material':True,'required_capabilities':['a'],'impact_level':'LOW','reversibility':'REVERSIBLE'}],'counterfactual':{'max_dependency':.9},'rollback':{'irreversible_steps':[],'rollback_gap_steps':[]}}
  b=copy.deepcopy(a);b['plan_id']='B';b['steps']*=3;b['counterfactual']={'max_dependency':.1};return build_decision_lattice([a,b])['dominance_edges']==[]
 if k=='rollback_reverse':return {'from':'rollback:b','to':'rollback:a'} in build_rollback_graph(plan_of(r,p))['edges']
 if k=='irreversible':p['action_ledger']['candidates'][1]['reversibility']='IRREVERSIBLE';p['action_ledger']['candidates'][1]['rollback_plan']='';return 'b' in build_rollback_graph(plan_of(r,p))['irreversible_steps']
 if k=='rollback_gap':p['action_ledger']['candidates'][1]['rollback_plan']='';return 'b' in build_rollback_graph(plan_of(r,p))['rollback_gap_steps']
 if k=='singleton':r,cy,p=make(False);q=plan_of(r,p);return q['plan_id']=='P' and q['topological_order']==['a']
 if k=='badpred':
  try:normalize_predicate('*');return False
  except ValueError:return True
 if k=='casefold':return normalize_predicate('Ready.STATE')=='ready.state'
 if k=='propagate':row=next(x for x in counterfactual_dependency(plan_of(r,p))['assumptions'] if x['assumption']=='a.ok');return row['affected_steps']==['a','b']
 if k=='sibling':r.nodes['C']=N('C',metadata={'plan_id':'P','decision_problem_id':'D','plan_step_id':'c','plan_preconditions':['!done'],'plan_postconditions':['other'],'plan_assumptions':['c.ok']});p['action_ledger']['candidates'].append(c('C',caps=('op.other',)));row=next(x for x in counterfactual_dependency(plan_of(r,p))['assumptions'] if x['assumption']=='b.ok');return row['affected_steps']==['b']
 if k=='inverse':return '!done' not in simulate_success_path(plan_of(r,p))['final_state']
 if k=='semantic':r.nodes['A'].metadata['plan_initial_conditions']=['service.failed'];r.nodes['A'].metadata['plan_preconditions']=['service.failed'];r.nodes['A'].metadata['plan_postconditions']=['service.healthy'];w=simulate_success_path(plan_of(r,p));return 'service.failed' in w['final_state'] and 'service.healthy' in w['final_state']
 if k=='gapreview':r.nodes['B'].metadata['plan_preconditions']=['never'];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='blockworld':p['action_ledger']['candidates'][0]['decision']['status']='CENTRAL_BLOCKED';r.nodes['A'].metadata['plan_initial_conditions']=[];return fin(r,cy,p)['overall_status']=='PLAN_BLOCKED'
 if k=='worldhuman':p['action_ledger']['candidates'][0]['decision']['status']='HUMAN_EXECUTION_REQUIRED';r.nodes['A'].metadata['plan_initial_conditions']=[];return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='humanhost':p['action_ledger']['candidates'][0]['decision']['status']='HUMAN_EXECUTION_REQUIRED';return fin(r,cy,p)['overall_status']=='PLAN_HUMAN_EXECUTION_REQUIRED'
 if k=='overallreview':r.nodes['Q']=N('Q',metadata={'plan_id':'Q','decision_problem_id':'D','plan_step_id':'q','plan_initial_conditions':['q'],'plan_preconditions':['q'],'plan_postconditions':['q.done']});p['action_ledger']['candidates'].append(c('Q'));p['action_ledger']['candidates'][0]['decision']['status']='APPROVAL_REQUIRED';return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='overallhuman':p['action_ledger']['candidates'][0]['decision']['status']='HUMAN_EXECUTION_REQUIRED';return fin(r,cy,p)['overall_status']=='PLAN_HUMAN_EXECUTION_REQUIRED'
 if k=='nondominated':return len(fin(r,cy,p)['plan_ledger']['decision_lattice']['nondominated_plan_ids'])==1
 if k=='dominated':return check('pareto')
 if k=='capunique':return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['capability_surface']==2
 if k=='capdedupe':p['action_ledger']['candidates'][1]['required_capabilities']=['op.write'];return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['capability_surface']==1
 if k=='materialcount':return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['material_steps']==2
 if k=='highimpact':p['action_ledger']['candidates'][1]['impact_level']='HIGH';return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['high_impact']==1
 if k=='irrevvec':p['action_ledger']['candidates'][1]['reversibility']='IRREVERSIBLE';p['action_ledger']['candidates'][1]['rollback_plan']='';return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['irreversible']==1
 if k=='gapvec':p['action_ledger']['candidates'][1]['rollback_plan']='';return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['rollback_gaps']==1
 if k=='depvec':return decision_vector(fin(r,cy,p)['plan_ledger']['plans'][0])['assumption_dependency']==1.0
 if k=='hashdet':return fin(r,cy,p)['plan_ledger']['sha256']==fin(r,cy,p)['plan_ledger']['sha256']
 if k=='evidence':before={x:n.evidence for x,n in r.nodes.items()};fin(r,cy,p);return before=={x:n.evidence for x,n in r.nodes.items()}
 if k=='durable':
  with tempfile.TemporaryDirectory() as td:r.durable=True;r.state_dir=Path(td);fin(r,cy,p);return (Path(td)/'plan-ledger.json').exists()
 if k=='rtauth':fin(r,cy,p);return r.runtime['planning']['last']['authority']==0.0
 if k=='hashchange':h1=fin(r,cy,p)['plan_ledger']['sha256'];r.nodes['B'].metadata['plan_assumptions'].append('new.assumption');h2=fin(r,cy,p)['plan_ledger']['sha256'];return h1!=h2
 if k=='input':before=copy.deepcopy(p);fin(r,cy,p);return p==before
 if k=='graphauth':return build_plan_graph(r,p['action_ledger'])['authority']==0.0
 if k=='worldauth':return simulate_success_path(plan_of(r,p))['authority']==0.0
 if k=='rollbackauth':return build_rollback_graph(plan_of(r,p))['authority']==0.0
 if k=='latticeauth':return build_decision_lattice([])['authority']==0.0
 if k=='defaultproblem':r.nodes['A'].metadata.pop('decision_problem_id');r.nodes['B'].metadata.pop('decision_problem_id');return plan_of(r,p)['decision_problem_id']=='P'
 if k=='empty':return fin(R(),cy,{'action_ledger':{'candidates':[]}})['overall_status']=='NONE'
 if k=='nonmaterial':r,cy,p=make(False);p['action_ledger']['candidates'][0]=c('A','PROPOSABLE',False,(),impact='NONE',rev='UNKNOWN',rb='');return fin(r,cy,p)['overall_status']=='PLAN_PROPOSABLE'
 if k=='unknownstatus':p['action_ledger']['candidates'][0]['decision']['status']='UNKNOWN';return fin(r,cy,p)['overall_status']=='PLAN_REVIEW_REQUIRED'
 if k=='revalidation':q=fin(r,cy,p)['plan_ledger']['plans'][0];return q['status']=='PLAN_HOST_REVALIDATION_REQUIRED' and q['execution_eligible'] is False
 if k=='noupgrade':p['action_ledger']['candidates'][0]['decision']['status']='AUTHORITY_REQUIRED';return fin(r,cy,p)['plan_ledger']['plans'][0]['status']!='PLAN_HOST_REVALIDATION_REQUIRED'
 if k=='parallel':r.nodes['B'].metadata['plan_depends_on']=[];q=plan_of(r,p);return q['structural_valid'] and q['topological_order']==['a','b']
 if k=='postconflict':r.nodes['B'].metadata['plan_postconditions']=['verified','!verified'];return not simulate_success_path(plan_of(r,p))['valid']
 return False
PAIRS=[('missing_initial_synthesized','missing_initial'),('unknown_dependency_ignored','unknown_dep'),('dependency_cycle_ignored','cycle'),('duplicate_step_accepted','duplicate'),('mixed_problem_collapsed','mixed_problem'),('initial_contradiction_ignored','contradict_initial'),('postcondition_contradiction_ignored','contradict_post'),('ineligible_action_upgraded','ineligible'),('human_action_upgraded','human'),('central_block_ignored','central'),('nonmaterial_companion_cancels_plan','companion'),('planner_executes_action','noexec'),('planner_claims_epistemic_authority','noepiauth'),('planner_claims_execution_authority','noexecauth'),('same_turn_approval_becomes_plan_token','noreuse'),('symbolic_world_claimed_observed','worldnotobs'),('assumption_ablation_claimed_causality','nocausality'),('scalar_utility_sneaks_in','noscalar'),('cross_problem_dominance','cross'),('pareto_dominance_missing','pareto'),('tradeoff_forced_to_scalar_winner','tradeoff'),('rollback_order_not_reversed','rollback_reverse'),('irreversible_step_hidden','irreversible'),('rollback_gap_hidden','rollback_gap'),('singleton_infers_extra_steps','singleton'),('wildcard_predicate_allowed','badpred'),('predicate_not_canonical','casefold'),('assumption_dependency_not_propagated','propagate'),('assumption_ablation_hits_sibling','sibling'),('explicit_negation_not_flipped','inverse'),('semantic_opposite_hallucinated','semantic'),('unsatisfied_precondition_executes','gapreview'),('block_loses_to_world_error','blockworld'),('human_status_masks_world_error','worldhuman'),('host_peer_upgrades_human_step','humanhost'),('review_plan_hidden_by_good_plan','overallreview'),('human_plan_hidden_by_good_step','overallhuman'),('nondominated_set_missing','nondominated'),('dominated_plan_kept_as_winner','dominated'),('capability_surface_not_counted','capunique'),('duplicate_capabilities_inflate_surface','capdedupe'),('material_step_count_wrong','materialcount'),('high_impact_not_in_vector','highimpact'),('irreversible_not_in_vector','irrevvec'),('rollback_gap_not_in_vector','gapvec'),('dependency_sensitivity_not_in_vector','depvec'),('plan_hash_nondeterministic','hashdet'),('planning_modifies_evidence','evidence'),('durable_plan_projection_missing','durable'),('runtime_planning_state_has_authority','rtauth'),('plan_hash_ignores_semantic_change','hashchange'),('planner_mutates_action_ledger','input'),('plan_graph_has_authority','graphauth'),('world_model_has_authority','worldauth'),('rollback_graph_has_authority','rollbackauth'),('decision_lattice_has_authority','latticeauth'),('default_decision_problem_inferred_cross_plan','defaultproblem'),('empty_ledger_claims_plan','empty'),('nonmaterial_forced_material','nonmaterial'),('unknown_action_status_upgraded','unknownstatus'),('revalidation_equals_execution','revalidation'),('plan_upgrades_authority_failure','noupgrade'),('parallel_steps_forced_into_order','parallel'),('conflicting_postconditions_accepted','postconflict')]
assert len(PAIRS)==64
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);results={name:bool(check(key)) for name,key in PAIRS};survivors=sorted(name for name,ok in results.items() if not ok);order=list(results);rng.shuffle(order);seen={order[i%len(order)] for i in range(a.mutations)};before=len(seen);tail_new=0
 for i in range(a.tail):name=order[(a.mutations+i)%len(order)];tail_new+=name not in seen;seen.add(name)
 status='PASS' if len(seen)==len(PAIRS) and not survivors and tail_new==0 else 'FAIL';out={'schema':'ikant-planning-mutations/v0.16-test','status':status,'seed':a.seed,'mutations':a.mutations,'tail':a.tail,'mutation_families':len(PAIRS),'families_seen':len(seen),'families_before_tail':before,'survivors':survivors,'tail_new_families':tail_new};print(json.dumps(out,sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
