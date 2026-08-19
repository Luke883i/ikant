import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation
from ikant.session_host import prepare_text_frame,acknowledge_prepared_frame,recover_prepared_frame

FRAME='+--+\n| dashboard |\n+--+'
class R:
 def __init__(self,p):self.state_dir=Path(p);self.runtime={'status':'ACTIVE','session_id':'SES-X'}
 def require_active(self):
  if self.runtime['status']!='ACTIVE':raise PermissionError

class HostV10(unittest.TestCase):
 def test_prepare_does_not_ack(self):
  with tempfile.TemporaryDirectory() as td:
   rt=R(td);p=prepare_text_frame(rt,FRAME,kind='TURN');g=DashboardEgressGuard(Path(td)/'egress.json',runtime_session_id='SES-X');self.assertEqual(g.state,EgressState.FRAME_PENDING);self.assertFalse(p['acknowledged'])
   p2=acknowledge_prepared_frame(rt,p,FRAME);self.assertTrue(p2['acknowledged']);self.assertEqual(p2['delivery_state'],EgressState.LOCKED.value)
 def test_write_failure_can_recover(self):
  with tempfile.TemporaryDirectory() as td:
   rt=R(td);p=prepare_text_frame(rt,FRAME,kind='TURN');rec=recover_prepared_frame(rt);self.assertEqual(rec['text'],FRAME);self.assertTrue(rec['recovery']);acknowledge_prepared_frame(rt,rec,FRAME)
 def test_extra_byte_breaches(self):
  with tempfile.TemporaryDirectory() as td:
   rt=R(td);p=prepare_text_frame(rt,FRAME,kind='TURN')
   with self.assertRaises(EgressViolation):acknowledge_prepared_frame(rt,p,FRAME+'x')
if __name__=='__main__':unittest.main()
