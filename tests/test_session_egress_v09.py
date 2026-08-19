import tempfile,threading,unittest
from pathlib import Path
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation,EXIT_COMMAND
FRAME='+--------------------------------+\n| > iKant: dashboard             |\n+--------------------------------+'
class SessionEgressV09(unittest.TestCase):
 def guard(self,td):
  p=Path(td)/'egress.json';return DashboardEgressGuard(p,runtime_session_id='SES-1') if p.exists() else DashboardEgressGuard.create(p,runtime_session_id='SES-1')
 def test_initial_lock(self):
  with tempfile.TemporaryDirectory() as td:self.assertEqual(self.guard(td).state,EgressState.LOCKED)
 def test_exact_frame_round_trip(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');self.assertEqual(g.state,EgressState.FRAME_PENDING);self.assertTrue(g.acknowledge_visible(r,FRAME));self.assertEqual(g.state,EgressState.LOCKED)
 def test_prefix_suffix_wrapper_and_mutation_breach(self):
  for actual in ('x'+FRAME,FRAME+'x','```\n'+FRAME+'\n```',FRAME.replace('iKant','ChatGPT')):
   with self.subTest(actual=actual[:16]),tempfile.TemporaryDirectory() as td:
    g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');self.assertFalse(g.acknowledge_visible(r,actual));self.assertEqual(g.state,EgressState.BREACHED)
 def test_only_exact_exit(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);self.assertEqual(g.classify_user_text(EXIT_COMMAND),'EXIT')
   for s in (' EXIT IKANT','EXIT IKANT ','exit ikant','"EXIT IKANT"','please EXIT IKANT','EXIT IKANT\n'):self.assertEqual(g.classify_user_text(s),'INTENT')
 def test_release_then_resume_with_integrity(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='EXIT',release_after_frame=True);self.assertEqual(g.state,EgressState.RELEASE_PENDING);self.assertTrue(g.acknowledge_visible(r,FRAME));self.assertEqual(g.state,EgressState.RELEASED)
   with self.assertRaises(EgressViolation):g.resume(runtime_integrity_ok=False)
   g.resume(runtime_integrity_ok=True);self.assertEqual(g.state,EgressState.LOCKED);self.assertEqual(g.record.epoch,2)
 def test_stale_receipt_breaches(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r1=g.seal_frame(FRAME,kind='TURN');g.acknowledge_visible(r1,FRAME);r2=g.seal_frame(FRAME+'2',kind='TURN');self.assertFalse(g.acknowledge_visible(r1,FRAME));self.assertEqual(g.state,EgressState.BREACHED);self.assertEqual(r2.frame_seq,2)
 def test_session_binding(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);r=g.seal_frame(FRAME,kind='TURN');g.acknowledge_visible(r,FRAME);self.assertEqual(self.guard(td).record.frame_seq,1)
   with self.assertRaises(EgressViolation):DashboardEgressGuard(Path(td)/'egress.json',runtime_session_id='SES-X')
 def test_concurrent_second_frame_cannot_seal(self):
  with tempfile.TemporaryDirectory() as td:
   g=self.guard(td);bar=threading.Barrier(9);out=[]
   def w(i):
    bar.wait()
    try:r=g.seal_frame(FRAME+str(i),kind='TURN');out.append(('ok',r))
    except Exception as e:out.append(('err',type(e).__name__))
   ts=[threading.Thread(target=w,args=(i,)) for i in range(8)];[t.start() for t in ts];bar.wait();[t.join() for t in ts]
   self.assertEqual(sum(x[0]=='ok' for x in out),1);self.assertEqual(sum(x[0]=='err' for x in out),7);self.assertEqual(g.state,EgressState.FRAME_PENDING)
if __name__=='__main__':unittest.main()
