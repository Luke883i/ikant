import tempfile, unittest
from dataclasses import dataclass, field
from pathlib import Path

from ikant.plan_graph import build_plan_graph, normalize_predicate
from ikant.world_model import simulate_success_path, counterfactual_dependency, build_rollback_graph
from ikant.decision_lattice import build_decision_lattice
from ikant.planning import finalize_planning

@dataclass
class N:
    id: str
    evidence: float=.9
    metadata: dict=field(default_factory=dict)
class R:
    def __init__(self, durable=False, root=None):
        self.nodes={}; self.runtime={'session_id':'S'}; self.durable=durable; self.state_dir=Path(root or '.')
    def _write_runtime(self): pass

def cand(nid, status='HOST_EXECUTION_ELIGIBLE', material=True, impact='LOW', rev='REVERSIBLE', caps=('deploy.restart',), rollback='restore'):
    return {'node_id':nid,'material':material,'required_capabilities':list(caps),'impact_level':impact,'reversibility':rev,'rollback_plan':rollback,'decision':{'status':status}}

def practical(*candidates):
    return {'action_ledger':{'candidates':list(candidates)}}

def add(rt,nid,**meta):
    rt.nodes[nid]=N(nid,metadata=meta); return rt.nodes[nid]

class GraphTests(unittest.TestCase):
    def test_singleton_is_not_multi_step_inference(self):
        rt=R();add(rt,'A');g=build_plan_graph(rt,practical(cand('A'))['action_ledger']);p=g['plans'][0]
        self.assertEqual(p['plan_id'],'singleton:A');self.assertTrue(p['structural_valid']);self.assertEqual(p['topological_order'],['A'])
    def test_explicit_dag(self):
        rt=R();add(rt,'A',plan_id='P',plan_step_id='s1');add(rt,'B',plan_id='P',plan_step_id='s2',plan_depends_on=['s1'])
        p=build_plan_graph(rt,practical(cand('A'),cand('B'))['action_ledger'])['plans'][0]
        self.assertEqual(p['topological_order'],['s1','s2']);self.assertTrue(p['structural_valid'])
    def test_unknown_dependency_fails(self):
        rt=R();add(rt,'A',plan_id='P',plan_step_id='s1',plan_depends_on=['missing'])
        p=build_plan_graph(rt,practical(cand('A'))['action_ledger'])['plans'][0];self.assertFalse(p['structural_valid'])
    def test_cycle_fails(self):
        rt=R();add(rt,'A',plan_id='P',plan_step_id='a',plan_depends_on=['b']);add(rt,'B',plan_id='P',plan_step_id='b',plan_depends_on=['a'])
        p=build_plan_graph(rt,practical(cand('A'),cand('B'))['action_ledger'])['plans'][0];self.assertIn('dependency cycle',p['structural_errors'])
    def test_duplicate_step_fails(self):
        rt=R();add(rt,'A',plan_id='P',plan_step_id='x');add(rt,'B',plan_id='P',plan_step_id='x')
        p=build_plan_graph(rt,practical(cand('A'),cand('B'))['action_ledger'])['plans'][0];self.assertFalse(p['structural_valid'])
    def test_mixed_problem_fails(self):
        rt=R();add(rt,'A',plan_id='P',decision_problem_id='D1');add(rt,'B',plan_id='P',decision_problem_id='D2',plan_step_id='B',plan_depends_on=['A'])
        p=build_plan_graph(rt,practical(cand('A'),cand('B'))['action_ledger'])['plans'][0];self.assertIn('mixed decision problem',p['structural_errors'])
    def test_bad_predicate_fails(self):
        with self.assertRaises(ValueError): normalize_predicate('*')

class WorldTests(unittest.TestCase):
    def plan(self):
        rt=R();add(rt,'A',plan_id='P',plan_step_id='a',plan_initial_conditions=['!service.healthy'],plan_preconditions=['!service.healthy'],plan_postconditions=['service.healthy'],plan_assumptions=['fault.verified']);add(rt,'B',plan_id='P',plan_step_id='b',plan_depends_on=['a'],plan_preconditions=['service.healthy'],plan_postconditions=['traffic.restored'],plan_assumptions=['route.valid'])
        return build_plan_graph(rt,practical(cand('A'),cand('B'))['action_ledger'])['plans'][0]
    def test_success_path(self):
        w=simulate_success_path(self.plan());self.assertTrue(w['valid']);self.assertIn('traffic.restored',w['final_state']);self.assertNotIn('!service.healthy',w['final_state'])
    def test_missing_precondition_fails(self):
        p=self.plan();p['initial_conditions']=[];w=simulate_success_path(p);self.assertFalse(w['valid'])
    def test_postcondition_can_flip_state(self):
        p=self.plan();w=simulate_success_path(p);self.assertIn('service.healthy',w['final_state'])
    def test_counterfactual_ablation_propagates(self):
        c=counterfactual_dependency(self.plan());row=next(x for x in c['assumptions'] if x['assumption']=='fault.verified');self.assertEqual(row['affected_steps'],['a','b']);self.assertEqual(row['dependency_fraction'],1.0)
    def test_counterfactual_is_not_causality_claim(self): self.assertFalse(counterfactual_dependency(self.plan())['real_world_causality_claim'])
    def test_rollback_reverse_dependency(self):
        r=build_rollback_graph(self.plan());self.assertIn({'from':'rollback:b','to':'rollback:a'},r['edges'])

class PlanningTests(unittest.TestCase):
    def make(self, status='HOST_EXECUTION_ELIGIBLE', *, two=False, bad_world=False, rev='REVERSIBLE', impact='LOW'):
        rt=R();add(rt,'A',plan_id='P',decision_problem_id='D',plan_step_id='a',plan_initial_conditions=[] if bad_world else ['ready'],plan_preconditions=['ready'],plan_postconditions=['done'],plan_assumptions=['assume.a'])
        cs=[cand('A',status=status,rev=rev,impact=impact,rollback='' if rev=='IRREVERSIBLE' else 'restore')]
        if two:
            add(rt,'B',plan_id='P',decision_problem_id='D',plan_step_id='b',plan_depends_on=['a'],plan_preconditions=['done'],plan_postconditions=['verified'],plan_assumptions=['assume.b']);cs.append(cand('B'))
        return rt, {'cycle_id':'C','semantic_slice':{'intent_sha256':'I'}}, practical(*cs)
    def test_good_plan_requires_revalidation_not_execution(self):
        rt,c,p=self.make(two=True);out=finalize_planning(rt,c,p,central={});plan=out['plan_ledger']['plans'][0]
        self.assertEqual(plan['status'],'PLAN_HOST_REVALIDATION_REQUIRED');self.assertFalse(plan['execution_eligible']);self.assertFalse(out['plan_ledger']['execution_performed'])
    def test_ineligible_action_not_upgraded(self):
        rt,c,p=self.make(status='APPROVAL_REQUIRED');out=finalize_planning(rt,c,p,central={});self.assertEqual(out['overall_status'],'PLAN_REVIEW_REQUIRED')
    def test_human_action_stays_human(self):
        rt,c,p=self.make(status='HUMAN_EXECUTION_REQUIRED',rev='IRREVERSIBLE');out=finalize_planning(rt,c,p,central={});self.assertEqual(out['overall_status'],'PLAN_HUMAN_EXECUTION_REQUIRED')
    def test_central_block_stays_blocked(self):
        rt,c,p=self.make(status='CENTRAL_BLOCKED');out=finalize_planning(rt,c,p,central={});self.assertEqual(out['overall_status'],'PLAN_BLOCKED')
    def test_world_gap_forces_review(self):
        rt,c,p=self.make(bad_world=True);out=finalize_planning(rt,c,p,central={});self.assertEqual(out['overall_status'],'PLAN_REVIEW_REQUIRED')
    def test_evidence_unchanged(self):
        rt,c,p=self.make();before=rt.nodes['A'].evidence;out=finalize_planning(rt,c,p,central={});self.assertEqual(rt.nodes['A'].evidence,before);self.assertEqual(out['plan_ledger']['epistemic_authority'],0.0)
    def test_durable_projection(self):
        with tempfile.TemporaryDirectory() as td:
            rt,c,p=self.make();rt.durable=True;rt.state_dir=Path(td);finalize_planning(rt,c,p,central={});self.assertTrue((Path(td)/'plan-ledger.json').exists())

class LatticeTests(unittest.TestCase):
    def row(self,pid,problem,status='PLAN_HOST_REVALIDATION_REQUIRED',steps=1,impact='LOW',rev='REVERSIBLE',dep=0.0,caps=('a',),gaps=0):
        st=[{'material':True,'required_capabilities':list(caps),'impact_level':impact,'reversibility':rev} for _ in range(steps)]
        return {'plan_id':pid,'decision_problem_id':problem,'status':status,'steps':st,'counterfactual':{'max_dependency':dep},'rollback':{'irreversible_steps':[] if rev!='IRREVERSIBLE' else ['x'],'rollback_gap_steps':['x']*gaps}}
    def test_pareto_dominance(self):
        a=self.row('A','D',steps=1,dep=.2);b=self.row('B','D',steps=2,dep=.8,caps=('a','b'))
        l=build_decision_lattice([a,b]);self.assertIn({'decision_problem_id':'D','dominates':'A','dominated':'B'},l['dominance_edges']);self.assertEqual(l['nondominated_plan_ids'],['A'])
    def test_tradeoff_is_incomparable(self):
        a=self.row('A','D',steps=1,dep=.9);b=self.row('B','D',steps=3,dep=.1)
        l=build_decision_lattice([a,b]);self.assertEqual(l['dominance_edges'],[]);self.assertEqual(l['nondominated_plan_ids'],['A','B'])
    def test_no_cross_problem_comparison(self):
        a=self.row('A','D1');b=self.row('B','D2',steps=9,dep=1.0)
        l=build_decision_lattice([a,b]);self.assertEqual(l['dominance_edges'],[])
    def test_no_scalar_utility(self): self.assertFalse(build_decision_lattice([])['scalar_utility_used'])

if __name__=='__main__': unittest.main()
