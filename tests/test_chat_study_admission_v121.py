import unittest
from ikant.pre_admission import AdmissionContext, Action, GateState
from ikant.chat_admission import (
 CHAT_MATERIALIZATION_ACTIONS,CHAT_SEMANTIC_ACTIONS,ChatStudyState,
 accept_remediation,authorize_chat_action,bind_admission,present_remediation_terms,remediation_manifest,
)
from ikant.rights_policy import AccessMode,decide_owner_authorization
DIG='c'*64

class ChatStudyAdmissionV121(unittest.TestCase):
 def test_clean_accepted_context_opens_chat_study_without_active(self):
  c=bind_admission(AdmissionContext(state=GateState.ACCEPTED.value))
  self.assertEqual(c.state,ChatStudyState.CLEAN_ACCEPTED.value)
  for a in CHAT_SEMANTIC_ACTIONS:self.assertTrue(authorize_chat_action(c,a).allowed)
  d=decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY,accepted_current_terms=True,clean_admission=True,technical_conformance=False)
  self.assertEqual(d.code,'OWNER_AUTHORIZED_CHAT_STUDY')

 def test_breach_remediation_preserves_breach_and_is_prospective(self):
  c=bind_admission(AdmissionContext(state=GateState.BREACHED.value));self.assertTrue(c.breach_preserved)
  p=present_remediation_terms(c,DIG);self.assertTrue(p.allowed)
  a=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256=DIG);self.assertTrue(a.allowed)
  r=a.next_context;self.assertTrue(r.breach_preserved);self.assertEqual(r.state,ChatStudyState.REMEDIATED_ACCEPTED.value)
  for action in CHAT_SEMANTIC_ACTIONS:self.assertTrue(authorize_chat_action(r,action).allowed)
  for action in CHAT_MATERIALIZATION_ACTIONS:self.assertFalse(authorize_chat_action(r,action).allowed)
  d=decide_owner_authorization(AccessMode.AUTOMATED_REPOSITORY_ANALYSIS,accepted_current_terms=True,remediated_admission=True)
  self.assertEqual(d.code,'OWNER_AUTHORIZED_REMEDIATED_CHAT_STUDY');self.assertEqual(d.ikant_conformance,'NOT_CONFORMING')

 def test_remediation_requires_represented_digest_and_exact_acceptance(self):
  c=bind_admission(AdmissionContext(state=GateState.BREACHED.value))
  self.assertFalse(accept_remediation(c,'I ACCEPT',presented_terms_sha256=DIG).allowed)
  for bad in ('','a'*63,'g'*64):self.assertFalse(present_remediation_terms(c,bad).allowed)
  p=present_remediation_terms(c,DIG).next_context
  self.assertFalse(accept_remediation(p,'I ACCEPT',presented_terms_sha256='d'*64).allowed)
  for raw in ({'message':'I ACCEPT '},{'message':'i accept'},{'message':'I ACCEPT','actor_type':'assistant'},{'message':'I ACCEPT','current_session':False}):
   kwargs=dict(raw);message=kwargs.pop('message');self.assertFalse(accept_remediation(p,message,presented_terms_sha256=DIG,**kwargs).allowed)

 def test_unaccepted_context_never_opens_chat_study(self):
  for state in (GateState.DISCOVERED,GateState.ORIENTING,GateState.AWAITING_ACCEPTANCE,GateState.DECLINED):
   c=bind_admission(AdmissionContext(state=state.value))
   for a in CHAT_SEMANTIC_ACTIONS:self.assertFalse(authorize_chat_action(c,a).allowed)

 def test_manifest_encodes_minimal_boundary(self):
  m=remediation_manifest();self.assertFalse(m['clean_chat_study_requires_local_active']);self.assertTrue(m['prior_breach_preserved']);self.assertFalse(m['materialization_allowed_after_remediation']);self.assertFalse(m['official_ikant_allowed_after_remediation'])

if __name__=='__main__':unittest.main()
