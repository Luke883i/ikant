import json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation,FRAME_SCHEMA,MAX_FRAME_BYTES,EXIT_COMMAND,RESUME_COMMAND
from ikant.invariants import V09_EGRESS_SCHEMA
FRAME='+----+\n| > iKant: test |\n+----+'
class EgressV10(unittest.TestCase):
 def guard(self,td):
  p=Path(td)/'egress.json';return DashboardEgressGuard(p,runtime_session_id='SES-X') if p.exists() else DashboardEgressGuard.create(p,runtime_session_id='SES-X')
 def test_two_phase_keeps_pending_until_ack(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');self.assertEqual(g.state,EgressState.FRAME_PENDING)
   with self.assertRaises(EgressViolation):g.seal_frame(FRAME,kind='TURN2')
   self.assertTrue(g.acknowledge_visible(r,FRAME));self.assertEqual(g.state,EgressState.LOCKED)
 def test_prefix_suffix_breach(self):
  for actual in ['x'+FRAME,FRAME+'x','```\n'+FRAME+'\n```',FRAME+'\nsummary']:
   with self.subTest(actual=actual[:12]),tempfile.TemporaryDirectory() as td:
    g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');self.assertFalse(g.acknowledge_visible(r,actual));self.assertEqual(g.state,EgressState.BREACHED)
 def test_crash_recovery_replays_exact_bytes(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN',cycle_id='C1');del g;g2=self.guard(td);rr,text=g2.pending_frame();self.assertEqual(text,FRAME);self.assertEqual(rr.frame_sha256,r.frame_sha256);self.assertTrue(g2.acknowledge_visible(rr,text))
 def test_pending_artifact_tamper_breaches(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);g.seal_frame(FRAME,kind='TURN');Path(g.record.pending_frame_path).write_text(FRAME+'x')
   with self.assertRaises(EgressViolation):g.pending_frame()
   self.assertEqual(g.state,EgressState.BREACHED)
 def test_journal_tamper_detected(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');g.acknowledge_visible(r,FRAME);p=g.journal_path;rows=p.read_text().splitlines();d=json.loads(rows[-1]);d['event']='FAKE';rows[-1]=json.dumps(d);p.write_text('\n'.join(rows)+'\n')
   with self.assertRaises(EgressViolation):self.guard(td)
 def test_release_is_two_phase(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='EXIT',release_after_frame=True);self.assertEqual(g.state,EgressState.RELEASE_PENDING);self.assertTrue(g.acknowledge_visible(r,FRAME));self.assertEqual(g.state,EgressState.RELEASED)
 def test_resume_requires_integrity(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='EXIT',release_after_frame=True);g.acknowledge_visible(r,FRAME)
   with self.assertRaises(EgressViolation):g.resume(runtime_integrity_ok=False)
   g.resume(runtime_integrity_ok=True);self.assertEqual(g.record.epoch,2)
 def test_exact_commands(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);self.assertEqual(g.classify_user_text(EXIT_COMMAND),'EXIT');self.assertEqual(g.classify_user_text(RESUME_COMMAND),'RESUME')
   for x in [' EXIT IKANT','EXIT IKANT ','exit ikant','"EXIT IKANT"','EXIT\u200b IKANT','RESUME IKANT\n']:self.assertEqual(g.classify_user_text(x),'INTENT')
 def test_frame_bounds(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(EgressViolation):self.guard(td).seal_frame('x'*(MAX_FRAME_BYTES+1),kind='TURN')
 def test_v09_locked_migrates(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'egress.json';p.write_text(json.dumps({'schema':V09_EGRESS_SCHEMA,'runtime_session_id':'SES-X','state':'DASHBOARD_LOCKED','epoch':2,'frame_seq':4,'last_frame_sha256':None,'last_cycle_id':None,'last_kind':'TURN','updated_at':'x','breach_reason':None}));g=self.guard(td);self.assertEqual(g.state,EgressState.LOCKED);self.assertEqual(g.record.epoch,2)
 def test_v09_pending_migrates_to_breach(self):
  for state in ['FRAME_PENDING','RELEASE_PENDING']:
   with self.subTest(state=state),tempfile.TemporaryDirectory() as td:
    p=Path(td)/'egress.json';p.write_text(json.dumps({'schema':V09_EGRESS_SCHEMA,'runtime_session_id':'SES-X','state':state,'epoch':1,'frame_seq':1,'last_frame_sha256':'a'*64,'last_cycle_id':'C','last_kind':'TURN','updated_at':'x','breach_reason':None}));g=self.guard(td);self.assertEqual(g.state,EgressState.BREACHED);self.assertIn('v0.9 pending',g.record.breach_reason)
 def test_corrupt_state_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'egress.json';p.write_text('{oops')
   with self.assertRaises(EgressViolation):self.guard(td)
if __name__=='__main__':unittest.main()
