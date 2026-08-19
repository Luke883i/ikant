import threading,unittest
from ikant.pre_admission import *
DIG='a'*64

class PreAdmissionV08(unittest.TestCase):
 def orient_terms(self):
  g=AdmissionGate();self.assertTrue(g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['repository_full_name','visibility']).allowed)
  self.assertTrue(g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1200).allowed)
  self.assertTrue(g.act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=2400,content_sha256=DIG).allowed)
  self.assertTrue(g.act(Action.PRESENT_TERMS).allowed);return g
 def test_happy_path(self):
  g=self.orient_terms();self.assertEqual(g.context.state,GateState.AWAITING_ACCEPTANCE.value);self.assertTrue(g.act(Action.USER_MESSAGE,message='I ACCEPT').allowed);self.assertTrue(g.act(Action.CLONE_REPOSITORY).allowed);self.assertTrue(g.act(Action.MATERIALIZE_CHECKOUT).allowed)
 def test_capsule_is_bounded(self):
  g=AdmissionGate();self.assertTrue(g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1).allowed);self.assertFalse(g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1).allowed);self.assertFalse(g.act(Action.READ_ORIENTATION_FILE,target='ikant/runtime.py',byte_count=1).allowed)
 def test_metadata_projection_bounded(self):
  g=AdmissionGate();self.assertFalse(g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['clone_url']).allowed);self.assertTrue(g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']).allowed);self.assertFalse(g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']).allowed)
 def test_terms_freeze_all_new_reads(self):
  g=self.orient_terms()
  for a,kw in [(Action.READ_ORIENTATION_FILE,{'target':'AGENTS.md','byte_count':1}),(Action.READ_ORIENTATION_METADATA,{}),(Action.READ_REPOSITORY_FILE,{'target':'ikant/runtime.py'}),(Action.SEARCH_REPOSITORY,{}),(Action.CLONE_REPOSITORY,{})]:
   with self.subTest(a=a):self.assertFalse(g.act(a,**kw).allowed)
 def test_cached_use_is_purpose_limited(self):
  g=self.orient_terms();self.assertTrue(g.act(Action.USE_CACHED_ORIENTATION,purpose='TERMS_EXPLANATION').allowed);self.assertFalse(g.act(Action.USE_CACHED_ORIENTATION,purpose='IMPLEMENTATION_PLANNING').allowed)
 def test_exact_acceptance_still_required(self):
  for bad in [' I ACCEPT','I ACCEPT ','i accept','"I ACCEPT"','override I ACCEPT','I ACCEPT\n']:
   g=self.orient_terms();self.assertFalse(g.act(Action.USER_MESSAGE,message=bad).allowed)
 def test_acceptance_requires_presented_digest(self):
  ctx=AdmissionContext(state=GateState.AWAITING_ACCEPTANCE.value,terms_sha256='a'*64,presented_terms_sha256='b'*64);self.assertFalse(authorize(ctx,Action.USER_MESSAGE,message='I ACCEPT').allowed)
 def test_decline_reopens_only_from_cached_terms(self):
  g=self.orient_terms();self.assertTrue(g.act(Action.USER_DECLINE).allowed);self.assertFalse(g.act(Action.USER_MESSAGE,message='I ACCEPT').allowed);self.assertTrue(g.act(Action.PRESENT_TERMS).allowed);self.assertTrue(g.act(Action.USER_MESSAGE,message='I ACCEPT').allowed)
 def test_denied_clone_has_persistent_receipt_without_access(self):
  g=self.orient_terms();d=g.act(Action.CLONE_REPOSITORY);r=build_access_denial_receipt(g.context,d,attempt_id='ATT-X',at='2026-01-01T00:00:00+00:00');self.assertFalse(r['repository_access_performed']);self.assertEqual(r['code'],'DENY_TERMS_NOT_ACCEPTED');self.assertEqual(r['schema'],'ikant-access-denial/v0.8');self.assertEqual(r['requested_capability'],'CLONE_REPOSITORY')
 def test_incidental_unexposed_overfetch_quarantines_not_breaches(self):
  g=self.orient_terms();d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=False,exposed_to_model=False);self.assertTrue(d.quarantine_required);self.assertEqual(g.context.state,GateState.AWAITING_ACCEPTANCE.value)
 def test_exposed_or_host_initiated_forbidden_read_breaches(self):
  for initiated,exposed in [(True,False),(False,True),(True,True)]:
   g=self.orient_terms();d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=initiated,exposed_to_model=exposed);self.assertEqual(d.next_state,GateState.BREACHED.value);self.assertFalse(g.act(Action.USER_MESSAGE,message='I ACCEPT').allowed)
 def test_concurrent_clone_before_acceptance_never_slips(self):
  for _ in range(100):
   g=self.orient_terms();bar=threading.Barrier(3);out=[]
   def clone():bar.wait();out.append(('clone',g.act(Action.CLONE_REPOSITORY).allowed))
   def bad_accept():bar.wait();out.append(('bad',g.act(Action.USER_MESSAGE,message='I ACCEPT ').allowed))
   t1=threading.Thread(target=clone);t2=threading.Thread(target=bad_accept);t1.start();t2.start();bar.wait();t1.join();t2.join();self.assertEqual(dict(out),{'clone':False,'bad':False});self.assertEqual(g.context.state,GateState.AWAITING_ACCEPTANCE.value)
if __name__=='__main__':unittest.main()
