from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from ikant.human_frame import build_actor_binding,build_human_frame,issue_interaction_receipt
from ikant.temporal_autonomy import (
 CLOCK_ROLLBACK_TOLERANCE_MS,CLAIM_TTL_MS,MAX_INTENT_BYTES,TemporalAutonomyError,TemporalAutonomyKernel,TemporalAutonomyRunner,TemporalAuthorityError,cancel_action_fingerprint,schedule_action_fingerprint,schedule_spec
)
SECRET=b'x'*32
SESSION='SES-1'
BINDING=build_actor_binding(session_id=SESSION,channel_id='web-paired',secret=SECRET)
def authorize(spec,*,seq=1,fingerprint=None):
 frame=build_human_frame(session_id=SESSION,actor_binding_id=BINDING.binding_id,frame_seq=seq,purpose='ACTION_CONFIRMATION',title='Temporal control',body='Confirm exact temporal control.',action_fingerprint=fingerprint or schedule_action_fingerprint(spec))
 return frame,issue_interaction_receipt(frame,binding=BINDING,decision='APPROVE',secret=SECRET)
def cancel_authorize(task_id,*,seq=2):
 frame=build_human_frame(session_id=SESSION,actor_binding_id=BINDING.binding_id,frame_seq=seq,purpose='ACTION_CONFIRMATION',title='Cancel temporal control',body='Cancel exact temporal task.',action_fingerprint=cancel_action_fingerprint(task_id))
 return frame,issue_interaction_receipt(frame,binding=BINDING,decision='APPROVE',secret=SECRET)
class TemporalAutonomyV24Tests(unittest.TestCase):
 def test_schedule_requires_exact_current_human_confirmation(self):
  spec=schedule_spec(session_id=SESSION,intent_text='check state later',due_at_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);task=kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);self.assertEqual(task['status'],'ACTIVE')
   bad_frame,bad_receipt=authorize(spec,seq=2,fingerprint='temporal:schedule:'+'0'*64)
   with self.assertRaises(TemporalAuthorityError):kernel.schedule(spec,bad_frame,bad_receipt,binding=BINDING,secret=SECRET,now_ms=0)
 def test_wake_is_zero_authority_freshness_barrier(self):
  spec=schedule_spec(session_id=SESSION,intent_text='think later',due_at_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);task=kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);self.assertEqual(kernel.poll(now_ms=999),[]);wake=kernel.poll(now_ms=1000)[0];barrier=wake['freshness_barrier'];self.assertFalse(barrier['execution_eligible']);self.assertFalse(barrier['material_execution_bridge']);self.assertFalse(barrier['pre_wake_approval_reusable']);self.assertFalse(barrier['pre_wake_grant_reusable']);self.assertFalse(barrier['pre_wake_lease_reusable']);self.assertTrue(barrier['fresh_host_revalidation_required']);self.assertEqual(wake['execution_authority'],0.0);kernel.claim_wake(wake['wake_id'],worker_id='worker',now_ms=1000);kernel.complete_wake(wake['wake_id'],worker_id='worker',delivered=True,now_ms=1001);self.assertEqual(kernel.state().tasks[task['task_id']]['status'],'EXHAUSTED')
 def test_recurring_forward_jump_coalesces_to_one_wake(self):
  spec=schedule_spec(session_id=SESSION,intent_text='recurring',due_at_ms=1000,interval_ms=60000,max_fires=3,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);wake=kernel.poll(now_ms=181123)[0];self.assertEqual(wake['missed_intervals_coalesced'],3);self.assertGreater(wake['next_due_at_ms'],181123);self.assertEqual(kernel.poll(now_ms=181124),[])
 def test_clock_rollback_blocks_until_original_floor(self):
  spec=schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=10000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=5000);self.assertEqual(kernel.poll(now_ms=1000),[]);self.assertTrue(kernel.projection()['clock_blocked']);self.assertEqual(kernel.poll(now_ms=2000),[]);self.assertTrue(kernel.projection()['clock_blocked']);kernel.poll(now_ms=5000);self.assertFalse(kernel.projection()['clock_blocked'])
 def test_stale_or_expired_claim_only_retries_control_plane(self):
  spec=schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=1000,retry_attempts=2,retry_base_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);wake=kernel.poll(now_ms=1000)[0];kernel.claim_wake(wake['wake_id'],worker_id='worker',now_ms=1000);kernel.poll(now_ms=1000+CLAIM_TTL_MS);retry=kernel.state().wakes[wake['wake_id']];self.assertEqual(retry['status'],'RETRY_PENDING');self.assertFalse(retry['freshness_barrier']['material_execution_bridge'])
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);wake=kernel.poll(now_ms=1000)[0];kernel.claim_wake(wake['wake_id'],worker_id='worker',now_ms=1000)
   with self.assertRaises(TemporalAutonomyError):kernel.complete_wake(wake['wake_id'],worker_id='worker',delivered=True,now_ms=1000+CLAIM_TTL_MS)
   self.assertEqual(kernel.state().wakes[wake['wake_id']]['status'],'RETRY_PENDING')
 def test_explicit_cancel_terminalizes_pending_wake(self):
  spec=schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);task=kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);wake=kernel.poll(now_ms=1000)[0];cframe,creceipt=cancel_authorize(task['task_id']);out=kernel.cancel(task['task_id'],cframe,creceipt,binding=BINDING,secret=SECRET,now_ms=1001);self.assertEqual(out['status'],'CANCELLED');self.assertEqual(kernel.state().wakes[wake['wake_id']]['status'],'CANCELLED');self.assertEqual(kernel.pending_wakes(),[])
   with self.assertRaises(TemporalAutonomyError):kernel.claim_wake(wake['wake_id'],worker_id='worker',now_ms=1002)
 def test_schedule_replay_is_idempotent_across_time(self):
  spec=schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);a=kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);b=kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=5000);self.assertEqual(a['sha256'],b['sha256']);self.assertEqual(kernel.state().events,1)
 def test_journal_tamper_and_session_rebind_fail_closed(self):
  spec=schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=1000,now_ms=0);frame,receipt=authorize(spec)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0);path=Path(td)/'temporal-autonomy-events.jsonl';row=json.loads(path.read_text(encoding='utf-8').splitlines()[0]);row['payload']['intent_text']='tampered';path.write_text(json.dumps(row)+'\n',encoding='utf-8')
   with self.assertRaises(TemporalAutonomyError):TemporalAutonomyKernel(td,session_id=SESSION)
  with tempfile.TemporaryDirectory() as td:
   kernel=TemporalAutonomyKernel(td,session_id=SESSION);kernel.schedule(spec,frame,receipt,binding=BINDING,secret=SECRET,now_ms=0)
   with self.assertRaises(TemporalAutonomyError):TemporalAutonomyKernel(td,session_id='SES-2')
 def test_bounds_are_fail_closed(self):
  with self.assertRaises(ValueError):schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=0,interval_ms=1,max_fires=2,now_ms=0)
  with self.assertRaises(ValueError):schedule_spec(session_id=SESSION,intent_text='x',due_at_ms=0,max_fires=2,now_ms=0)
  with self.assertRaises(ValueError):schedule_spec(session_id=SESSION,intent_text='x'*(MAX_INTENT_BYTES+1),due_at_ms=0,now_ms=0)
 def test_runner_pauses_outside_locked_egress(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'.ikant';state.mkdir();(state/'runtime.json').write_text(json.dumps({'status':'ACTIVE','session_id':SESSION}),encoding='utf-8');(state/'egress.json').write_text(json.dumps({'runtime_session_id':SESSION,'state':'RELEASED'}),encoding='utf-8');runner=TemporalAutonomyRunner(root,clock_ms=lambda:1000);self.assertEqual(runner.tick(),[]);self.assertFalse((state/'temporal-autonomy.json').exists());(state/'egress.json').write_text(json.dumps({'runtime_session_id':SESSION,'state':'DASHBOARD_LOCKED'}),encoding='utf-8');self.assertEqual(runner.tick(),[]);self.assertTrue((state/'temporal-autonomy.json').exists())
if __name__=='__main__':unittest.main()
