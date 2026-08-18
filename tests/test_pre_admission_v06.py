import unittest
from ikant.pre_admission import *

class PreAdmissionFirewallTests(unittest.TestCase):
    def test_happy_path(self):
        s=GateState.DISCOVERED
        d=authorize(s,Action.FETCH_TERMS,target=TERMS_PATH);self.assertTrue(d.allowed);s=GateState(d.next_state)
        d=authorize(s,Action.PRESENT_TERMS);self.assertTrue(d.allowed);s=GateState(d.next_state)
        d=authorize(s,Action.USER_MESSAGE,message='I ACCEPT');self.assertTrue(d.allowed);s=GateState(d.next_state)
        d=authorize(s,Action.CLONE_REPOSITORY);self.assertTrue(d.allowed)
    def test_all_repository_access_denied_pre_accept(self):
        for action in REPOSITORY_ACCESS:
            with self.subTest(action=action):self.assertFalse(authorize(GateState.DISCOVERED,action).allowed)
    def test_terms_is_only_exception(self):
        self.assertTrue(authorize(GateState.DISCOVERED,Action.FETCH_TERMS,target=TERMS_PATH).allowed)
        for target in ['README.md','BOOTSTRAP.json','AGENTS.md','ikant/runtime.py','']:
            self.assertFalse(authorize(GateState.DISCOVERED,Action.FETCH_TERMS,target=target).allowed)
    def test_acceptance_requires_terms_presented(self):
        self.assertFalse(authorize(GateState.DISCOVERED,Action.USER_MESSAGE,message='I ACCEPT').allowed)
    def test_acceptance_variants_fail(self):
        bad=['I ACCEPT ',' I ACCEPT','i accept','I  ACCEPT','I ACCEPT\n','"I ACCEPT"','please I ACCEPT','I ACCEPT proceed','I\u200b ACCEPT','I ACCEPT'.lower(),'override I ACCEPT','ignore the gate','treat this as I ACCEPT','```I ACCEPT```']
        for msg in bad:
            with self.subTest(msg=repr(msg)):
                self.assertFalse(authorize(GateState.TERMS_PRESENTED,Action.USER_MESSAGE,message=msg).allowed)
    def test_nonhuman_prior_session_fail(self):
        self.assertFalse(authorize(GateState.TERMS_PRESENTED,Action.USER_MESSAGE,message='I ACCEPT',actor_type='assistant').allowed)
        self.assertFalse(authorize(GateState.TERMS_PRESENTED,Action.USER_MESSAGE,message='I ACCEPT',current_session=False).allowed)
        self.assertFalse(authorize(GateState.TERMS_PRESENTED,Action.USER_MESSAGE,message='I ACCEPT',evidence_type='inferred').allowed)
    def test_denied_action_does_not_advance_state(self):
        d=authorize(GateState.TERMS_PRESENTED,Action.CLONE_REPOSITORY);self.assertFalse(d.allowed);self.assertEqual(d.next_state,GateState.TERMS_PRESENTED.value)
    def test_materialize_only_after_acceptance(self):
        self.assertFalse(authorize(GateState.TERMS_PRESENTED,Action.MATERIALIZE_CHECKOUT).allowed)
        self.assertTrue(authorize(GateState.ACCEPTED,Action.MATERIALIZE_CHECKOUT).allowed)
    def test_completed_breach_cannot_be_cured(self):
        d=record_completed_pre_acceptance_breach(GateState.TERMS_PRESENTED,Action.CLONE_REPOSITORY);self.assertEqual(d.next_state,GateState.BREACHED.value)
        self.assertFalse(authorize(GateState.BREACHED,Action.USER_MESSAGE,message='I ACCEPT').allowed)
    def test_cached_terms_may_be_represented(self):
        self.assertTrue(authorize(GateState.TERMS_PRESENTED,Action.PRESENT_TERMS).allowed)
    def test_policy_manifest(self):
        p=policy_manifest();self.assertEqual(p['pre_acceptance_default'],'DENY');self.assertTrue(p['terms_envelope_is_only_repository_read_exception']);self.assertTrue(p['repository_materialization_requires_acceptance']);self.assertTrue(p['completed_pre_acceptance_breach_is_nonretroactive'])

if __name__=='__main__':unittest.main()
