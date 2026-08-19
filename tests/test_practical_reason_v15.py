import json
import tempfile
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ikant.action_governance import build_action_ledger, decide_action
from ikant.approvals import issue_same_turn_approval, validate_approval
from ikant.authority import normalize_capability, resolve_authority
from ikant.practical_reason import finalize_practical_reason

class K(str, Enum):
    GOAL='goal'; CONSTRAINT='constraint'; ACTION='action'; CLAIM='claim'
@dataclass
class M:
    social_relevance: float=0.0
    agency_relevance: float=0.0
@dataclass
class N:
    id: str; kind: K; text: str; source_mode: str; evidence: float=.7; active: bool=True; metadata: dict=field(default_factory=dict); modulators: M=field(default_factory=M)
class R:
    def __init__(self, durable=False, root=None):
        self.nodes={}; self.runtime={'session_id':'S'}; self.durable=durable
        self.state_dir=Path(root or '.')
    def _write_runtime(self): pass

def goal(rt, nid='G', caps=('deploy.restart',), active=True, source='user'):
    rt.nodes[nid]=N(nid,K.GOAL,'keep service healthy',source,metadata={'temporal_state':'ACTIVE','grants_capabilities':list(caps)},active=active)
    return rt.nodes[nid]

def action(rt, nid='A', **overrides):
    meta={'governing_commitment_ids':['G'],'required_capabilities':['deploy.restart'],'action_maxim':'Restart service to restore health after verified failure','material_action':True,'reversibility':'REVERSIBLE','rollback_plan':'start prior instance','expected_effects':['service restarts'],'failure_modes':['restart fails'],'human_impact_assessed':True,'impact_level':'LOW'}
    meta.update(overrides)
    rt.nodes[nid]=N(nid,K.ACTION,'restart service','user',metadata=meta)
    return rt.nodes[nid]

def cycle(rt):
    return {'cycle_id':'C','semantic_slice':{'intent_sha256':'I','nodes':[{'id':'A','kind':'action','text':'restart service','source_mode':'runtime_derived','epistemic_score':.9}]}}
def atom(approve=True):
    return {'kind':'action','source_mode':'user','text':'restart service','metadata':{'explicit_action_approval':approve,'approval_scope':'this_action'}}

class Authority(unittest.TestCase):
    def test_exact_capability(self):
        rt=R();goal(rt);a=resolve_authority(rt,governing_commitment_ids=['G'],required_capabilities=['deploy.restart']);self.assertTrue(a['authority_satisfied'])
    def test_missing_capability(self):
        rt=R();goal(rt,caps=('deploy.read',));a=resolve_authority(rt,governing_commitment_ids=['G'],required_capabilities=['deploy.restart']);self.assertFalse(a['authority_satisfied']);self.assertEqual(a['missing_capabilities'],['deploy.restart'])
    def test_derived_commitment_cannot_grant(self):
        rt=R();goal(rt,source='runtime_derived');self.assertFalse(resolve_authority(rt,governing_commitment_ids=['G'],required_capabilities=['deploy.restart'])['authority_satisfied'])
    def test_inactive_commitment_cannot_grant(self):
        rt=R();goal(rt,active=False);self.assertFalse(resolve_authority(rt,governing_commitment_ids=['G'],required_capabilities=[])['authority_satisfied'])
    def test_no_wildcard(self):
        with self.assertRaises(ValueError):normalize_capability('*')

class Approval(unittest.TestCase):
    def test_same_turn_binding(self):
        rt=R();goal(rt);action(rt);c={'node_id':'A','text':'restart service','source_mode':'user','maxim':rt.nodes['A'].metadata['action_maxim'],'required_capabilities':['deploy.restart'],'governing_commitment_ids':['G'],'affected_parties':[],'reversibility':'REVERSIBLE','material':True}
        rec=issue_same_turn_approval(rt,c,atom=atom(),intent_sha256='I',intention_node_id='INT')
        self.assertTrue(validate_approval(rec,c,session_id='S',intent_sha256='I',intention_node_id='INT')[0])
        self.assertFalse(validate_approval(rec,c,session_id='S2',intent_sha256='I',intention_node_id='INT')[0])
        self.assertFalse(validate_approval(rec,c,session_id='S',intent_sha256='J',intention_node_id='INT')[0])
    def test_repository_cannot_fake_human_approval(self):
        rt=R();c={'node_id':'A','text':'x','maxim':'m','required_capabilities':[],'governing_commitment_ids':[],'affected_parties':[],'reversibility':'REVERSIBLE','material':True}
        a=atom();a['source_mode']='repository';self.assertIsNone(issue_same_turn_approval(rt,c,atom=a,intent_sha256='I',intention_node_id='INT'))

class Governance(unittest.TestCase):
    def ledger(self, *, approve=True, central='REFLECTIVE_SYNTHESIS', action_overrides=None, goal_caps=('deploy.restart',), goal_active=True):
        rt=R();goal(rt,caps=goal_caps,active=goal_active);action(rt,**(action_overrides or {}));before=rt.nodes['A'].evidence
        out=build_action_ledger(rt,cycle(rt),central={'regulative_mode':central},mined=[{'id':'A','kind':'action'}],atoms=[atom(approve)],intention_node_id='INT')
        self.assertEqual(rt.nodes['A'].evidence,before);return out
    def test_eligible_reversible_action(self):
        x=self.ledger();self.assertEqual(x['candidates'][0]['decision']['status'],'HOST_EXECUTION_ELIGIBLE');self.assertFalse(x['execution_performed'])
    def test_approval_does_not_fill_capability(self):
        x=self.ledger(goal_caps=('deploy.read',));self.assertEqual(x['candidates'][0]['decision']['status'],'AUTHORITY_REQUIRED')
    def test_approval_required(self):
        self.assertEqual(self.ledger(approve=False)['candidates'][0]['decision']['status'],'APPROVAL_REQUIRED')
    def test_impact_blocks_before_approval(self):
        x=self.ledger(action_overrides={'affected_parties':['person:1'],'human_impact_assessed':False,'impact_level':'UNKNOWN'});self.assertEqual(x['candidates'][0]['decision']['status'],'IMPACT_REVIEW_REQUIRED')
    def test_irreversible_never_host_eligible(self):
        x=self.ledger(action_overrides={'reversibility':'IRREVERSIBLE','rollback_plan':''});self.assertEqual(x['candidates'][0]['decision']['status'],'HUMAN_EXECUTION_REQUIRED')
    def test_high_impact_never_host_eligible(self):
        x=self.ledger(action_overrides={'affected_parties':['person:1'],'impact_level':'HIGH'});self.assertEqual(x['candidates'][0]['decision']['status'],'HUMAN_EXECUTION_REQUIRED')
    def test_central_block_dominates(self):
        self.assertEqual(self.ledger(central='PRACTICAL_BLOCK')['candidates'][0]['decision']['status'],'CENTRAL_BLOCKED')
    def test_maxim_required(self):
        self.assertEqual(self.ledger(action_overrides={'action_maxim':''})['candidates'][0]['decision']['status'],'MAXIM_REQUIRED')
    def test_reversibility_required(self):
        self.assertEqual(self.ledger(action_overrides={'reversibility':'UNKNOWN'})['candidates'][0]['decision']['status'],'REVERSIBILITY_REQUIRED')
    def test_rollback_required(self):
        self.assertEqual(self.ledger(action_overrides={'rollback_plan':''})['candidates'][0]['decision']['status'],'ROLLBACK_REQUIRED')
    def test_counterfactual_review_required(self):
        self.assertEqual(self.ledger(action_overrides={'failure_modes':[]})['candidates'][0]['decision']['status'],'COUNTERFACTUAL_REVIEW_REQUIRED')
    def test_unlinked_goal_not_inferred(self):
        self.assertEqual(self.ledger(action_overrides={'governing_commitment_ids':[]})['candidates'][0]['decision']['status'],'AUTHORITY_REQUIRED')
    def test_nonmaterial_is_proposable(self):
        x=self.ledger(approve=False,action_overrides={'material_action':False,'governing_commitment_ids':[],'required_capabilities':[],'action_maxim':''});self.assertEqual(x['candidates'][0]['decision']['status'],'PROPOSABLE')

    def test_derived_action_requires_separate_user_approval_constraint(self):
        rt=R();goal(rt);action(rt);rt.nodes['A'].source_mode='runtime_derived'
        c=cycle(rt);c['semantic_slice']['nodes'][0]['source_mode']='runtime_derived'
        approval={'kind':'constraint','source_mode':'user','text':'approve proposed restart','metadata':{'explicit_action_approval':True,'approval_scope':'this_action','approves_action_node_id':'A'}}
        out=build_action_ledger(rt,c,central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'AP','kind':'constraint'}],atoms=[approval],intention_node_id='INT')
        self.assertEqual(out['candidates'][0]['decision']['status'],'HOST_EXECUTION_ELIGIBLE')

    def test_durable_ledger_projection(self):
        with tempfile.TemporaryDirectory() as td:
            rt=R(True,td);goal(rt);action(rt);out=build_action_ledger(rt,cycle(rt),central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'A','kind':'action'}],atoms=[atom()],intention_node_id='INT')
            self.assertTrue((Path(td)/'action-ledger.json').exists());self.assertEqual(out['epistemic_authority'],0.0)

    def test_nonmaterial_companion_does_not_cancel_material_eligibility(self):
        rt=R();goal(rt);action(rt)
        rt.nodes['B']=N('B',K.ACTION,'explain restart','user',metadata={'material_action':False})
        c=cycle(rt);c['semantic_slice']['nodes'].append({'id':'B','kind':'action','text':'explain restart','source_mode':'user','epistemic_score':.7})
        out=build_action_ledger(rt,c,central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'A','kind':'action'}],atoms=[atom()],intention_node_id='INT')
        self.assertEqual(out['material_action'],'HOST_EXECUTION_ELIGIBLE')

    def test_practical_reason_boundary(self):
        rt=R();goal(rt);action(rt);out=finalize_practical_reason(rt,cycle(rt),temporal_core={'replay':{'sha256':'T'}},central={'regulative_mode':'REFLECTIVE_SYNTHESIS'},mined=[{'id':'A','kind':'action'}],atoms=[atom()],intention_node_id='INT')
        self.assertTrue(out['boundaries']['eligibility_is_not_execution']);self.assertEqual(out['material_action'],'HOST_EXECUTION_ELIGIBLE')

if __name__=='__main__': unittest.main()
