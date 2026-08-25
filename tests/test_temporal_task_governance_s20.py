from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from ikant.human_frame import build_actor_binding,build_human_frame,issue_interaction_receipt
from ikant.task_governance import GovernedTemporalTasks,TemporalTaskGovernanceAuthorityError,TemporalTaskGovernanceError,erase_intent_action_fingerprint,governed_schedule_action_fingerprint,governed_schedule_spec
from ikant.temporal_autonomy import cancel_action_fingerprint
from ikant.governance_runtime import task_governance_projection
SECRET=b't'*32;SESSION='SES-S20';BINDING=build_actor_binding(session_id=SESSION,channel_id='web-paired',secret=SECRET)
def auth(fp,seq=1,title='Temporal control'):
 f=build_human_frame(session_id=SESSION,actor_binding_id=BINDING.binding_id,frame_seq=seq,purpose='ACTION_CONFIRMATION',title=title,body='Confirm exact control.',action_fingerprint=fp);return f,issue_interaction_receipt(f,binding=BINDING,decision='APPROVE',secret=SECRET)
def memfile(root:Path,records:dict):
 raw=json.dumps({k:records[k] for k in sorted(records)},sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest();(root/'temporal-memory.json').write_text(json.dumps({'records':records,'summary':{'sha256':sha}}),encoding='utf-8')
class TemporalTaskGovernanceS20Tests(unittest.TestCase):
 def setup_root(self,td):
  root=Path(td);(root/'runtime.json').write_text(json.dumps({'session_id':SESSION,'runtime_epoch':{'epoch_id':'E-7','ordinal':7}}),encoding='utf-8');return root
 def test_plaintext_exists_only_in_single_capsule_not_core_journal_or_wake(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='testo privato task',due_at_ms=1000,now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));task=g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);journal=(root/'temporal-autonomy-events.jsonl').read_text(encoding='utf-8');self.assertNotIn('testo privato task',journal);caps=list((root/'temporal-intents').glob('*.json'));self.assertEqual(len(caps),1);self.assertIn('testo privato task',caps[0].read_text(encoding='utf-8'));wake=g.poll(now_ms=1000)[0];self.assertEqual(wake['intent_text'],'testo privato task');self.assertNotIn('testo privato task',(root/'temporal-autonomy-events.jsonl').read_text(encoding='utf-8'));self.assertEqual(task['residency']['mode'],'IN_PROCESS_ONLY')
 def test_failed_authorization_leaves_no_plaintext_orphan_capsule(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='must not orphan',due_at_ms=1000,now_ms=0);f,r=auth('temporal:schedule:'+'0'*64)
   with self.assertRaises(TemporalTaskGovernanceAuthorityError):g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0)
   self.assertEqual(list((root/'temporal-intents').glob('*.json')),[])
 def test_memory_dependency_is_revalidated_at_wake_and_independent_task_survives(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);memfile(root,{'A':{'available':False}});g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='derived reminder',due_at_ms=1000,memory_dependency_ids=['A'],now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);w=g.poll(now_ms=1000)[0];self.assertFalse(w['claimable']);self.assertEqual(w['blocked_memory_dependency_ids'],['A']);self.assertEqual(w['execution_authority'],0.0)
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='explicit independent reminder',due_at_ms=1000,now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);w=g.poll(now_ms=1000)[0];self.assertTrue(w['claimable'])
 def test_capsule_tamper_blocks_claim_without_turning_wake_into_authority(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='later',due_at_ms=1000,now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);cap=next((root/'temporal-intents').glob('*.json'));raw=json.loads(cap.read_text());raw['intent_text']='tampered';cap.write_text(json.dumps(raw),encoding='utf-8');w=g.poll(now_ms=1000)[0];self.assertFalse(w['claimable']);self.assertEqual(w['governance_status'],'BLOCKED_GOVERNANCE');self.assertEqual(w['execution_authority'],0.0)
   with self.assertRaises(TemporalTaskGovernanceError):g.claim_wake(w['wake_id'],worker_id='worker',now_ms=1000)
 def test_creation_epoch_is_provenance_not_reusable_authority_and_residency_is_honest(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='later',due_at_ms=1000,now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));task=g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);self.assertEqual(task['creation_epoch']['epoch_id'],'E-7');self.assertFalse(task['residency']['background_guaranteed']);self.assertFalse(task['residency']['native_resident_host_attested']);self.assertTrue(task['future_boundaries']['transaction_approval_revalidation_required']);(root/'runtime.json').write_text(json.dumps({'session_id':SESSION,'runtime_epoch':{'epoch_id':'E-8','ordinal':8}}),encoding='utf-8');w=g.poll(now_ms=1000)[0];self.assertEqual(w['creation_epoch']['epoch_id'],'E-7');self.assertEqual(w['current_epoch']['epoch_id'],'E-8');self.assertTrue(w['fresh_human_interaction_required_for_material_execution'])
 def test_terminal_task_intent_can_be_erased_without_rewriting_journal(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);g=GovernedTemporalTasks(root,session_id=SESSION);spec=governed_schedule_spec(session_id=SESSION,intent_text='erase me',due_at_ms=1000,now_ms=0);f,r=auth(governed_schedule_action_fingerprint(spec));task=g.schedule(spec,f,r,binding=BINDING,secret=SECRET,now_ms=0);cf,cr=auth(cancel_action_fingerprint(task['task_id']),seq=2,title='Cancel');g.cancel(task['task_id'],cf,cr,binding=BINDING,secret=SECRET,now_ms=1);ef,er=auth(erase_intent_action_fingerprint(task['task_id']),seq=3,title='Erase intent');out=g.erase_intent(task['task_id'],ef,er,binding=BINDING,secret=SECRET);self.assertTrue(out['intent_erased']);self.assertEqual(list((root/'temporal-intents').glob('*.json')),[]);self.assertIn('TASK_SCHEDULED',(root/'temporal-autonomy-events.jsonl').read_text(encoding='utf-8'));self.assertNotIn('erase me',(root/'temporal-autonomy-events.jsonl').read_text(encoding='utf-8'))
 def test_surface_task_projection_is_strictly_read_only(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.setup_root(td);before=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file());out=task_governance_projection(root,session_id=SESSION);after=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file());self.assertEqual(before,after);self.assertEqual(out['integrity'],'VERIFIED');self.assertTrue(out['read_only_projection']);self.assertEqual(out['task_count'],0)
if __name__=='__main__':unittest.main()
