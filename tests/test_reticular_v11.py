from __future__ import annotations
import io,json,tempfile,unittest
from pathlib import Path
from ikant.invariants import critical_ids,registry_manifest,EGRESS_SCHEMA
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation,activate_runtime_egress,existing_runtime_egress
from ikant.transport import build_reference_attestation,validate_transport_attestation,deliver_human,write_machine_payload
class FakeRuntime:
 def __init__(self,root):self.state_dir=Path(root)/'.ikant';self.state_dir.mkdir(parents=True,exist_ok=True);self.runtime={'status':'ACTIVE','session_id':'SES-test'};self.events=[]
 def require_active(self):
  if self.runtime.get('status')!='ACTIVE':raise PermissionError
 def _write_runtime(self):pass
 def _event(self,op,subject,payload):self.events.append((op,subject,payload))
class ReticularV11Tests(unittest.TestCase):
 def test_registry_has_critical_total_coverage(self):
  ids=set(critical_ids());self.assertTrue({'ADM-001','EPI-001','PSY-001','SUR-001','EGR-001','EGR-002','EGR-003','EGR-004','TRN-001','CLI-001'}<=ids);self.assertEqual(registry_manifest()['egress_schema'],EGRESS_SCHEMA)
 def test_egress_creation_is_initialization_only(self):
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td)
   with self.assertRaises(EgressViolation):activate_runtime_egress(rt)
   g=activate_runtime_egress(rt,initialization=True);self.assertEqual(g.state,EgressState.LOCKED);self.assertTrue(rt.runtime['egress_guard']['required'])
 def test_deleted_required_egress_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td);g=activate_runtime_egress(rt,initialization=True);g.path.unlink()
   with self.assertRaisesRegex(EgressViolation,'required egress state missing'):existing_runtime_egress(rt)
   with self.assertRaisesRegex(EgressViolation,'silent recreation forbidden'):activate_runtime_egress(rt,initialization=True)
 def test_pending_frame_recovery_and_ack(self):
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td);g=activate_runtime_egress(rt,initialization=True);r=g.seal_frame('dashboard',kind='TURN');g2=existing_runtime_egress(rt);rr,text=g2.pending_frame();self.assertEqual(text,'dashboard');self.assertEqual(rr.frame_sha256,r.frame_sha256);self.assertTrue(g2.acknowledge_visible(rr,text));self.assertEqual(g2.state,EgressState.LOCKED)
 def test_v10_pending_migrates_without_losing_recovery(self):
  import hashlib
  from ikant.invariants import LEGACY_EGRESS_SCHEMA,LEGACY_JOURNAL_SCHEMA
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td);sd=rt.state_dir;frames=sd/'egress-frames';frames.mkdir();fp=frames/'epoch-0001-frame-00000001.txt';fp.write_text('legacy-dashboard',encoding='utf-8');dg=hashlib.sha256(b'legacy-dashboard').hexdigest();row={'schema':LEGACY_JOURNAL_SCHEMA,'seq':1,'at':'2026-01-01T00:00:00+00:00','runtime_session_id':'SES-test','event':'SEAL_FRAME','state':'FRAME_PENDING','epoch':1,'frame_seq':1,'payload':{'frame_sha256':dg},'prev_sha256':'0'*64};material=dict(row);row['sha256']=hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();(sd/'egress-events.jsonl').write_text(json.dumps(row,sort_keys=True)+'\n');state={'schema':LEGACY_EGRESS_SCHEMA,'runtime_session_id':'SES-test','state':'FRAME_PENDING','epoch':1,'frame_seq':1,'last_frame_sha256':dg,'last_cycle_id':'CYC-old','last_kind':'TURN','updated_at':'2026-01-01T00:00:00+00:00','breach_reason':None,'journal_seq':1,'last_journal_sha256':row['sha256'],'pending_frame_path':str(fp)};(sd/'egress.json').write_text(json.dumps(state));g=existing_runtime_egress(rt);receipt,text=g.pending_frame();self.assertEqual(text,'legacy-dashboard');self.assertEqual(g.state,EgressState.FRAME_PENDING);self.assertEqual(g.record.schema,EGRESS_SCHEMA);self.assertGreaterEqual(g.record.journal_seq,2)
 def test_v09_pending_migrates_fail_closed(self):
  from ikant.invariants import V09_EGRESS_SCHEMA
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td);sd=rt.state_dir;state={'schema':V09_EGRESS_SCHEMA,'runtime_session_id':'SES-test','state':'FRAME_PENDING','epoch':1,'frame_seq':1,'last_frame_sha256':'a'*64,'last_cycle_id':'C-old','last_kind':'TURN','updated_at':'x','breach_reason':None};(sd/'egress.json').write_text(json.dumps(state),encoding='utf-8');g=existing_runtime_egress(rt);self.assertEqual(g.state,EgressState.BREACHED);self.assertIn('v0.9 pending',g.record.breach_reason)
 def test_breach_resume_requires_transport_attestation(self):
  with tempfile.TemporaryDirectory() as td:
   rt=FakeRuntime(td);g=activate_runtime_egress(rt,initialization=True);r=g.seal_frame('dashboard',kind='TURN');self.assertFalse(g.acknowledge_visible(r,'dashboard extra'));self.assertEqual(g.state,EgressState.BREACHED)
   with self.assertRaisesRegex(EgressViolation,'transport attestation'):g.resume(runtime_integrity_ok=True)
   att=build_reference_attestation(machine_sink='disabled');g.resume(runtime_integrity_ok=True,transport_attestation=att);self.assertEqual(g.state,EgressState.LOCKED)
 def test_bad_transport_attestation_is_rejected(self):
  att=build_reference_attestation(machine_sink='disabled');raw=att.__dict__.copy();raw['channels_separate']=False;ok,errs=validate_transport_attestation(raw);self.assertFalse(ok);self.assertTrue(errs)
 def test_human_transport_exact(self):
  stream=io.StringIO();self.assertEqual(deliver_human('abc',stream=stream),3);self.assertEqual(stream.getvalue(),'abc')
 def test_machine_transport_is_file_only(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'machine.json';write_machine_payload(p,{'x':1});self.assertEqual(json.loads(p.read_text())['x'],1)
   for bad in ('-','stdout','stderr','/dev/stdout','/dev/stderr'):
    with self.assertRaises(PermissionError):write_machine_payload(bad,{'x':1})
 def test_canonical_source_has_no_versioned_entrypoint(self):
  root=Path(__file__).parents[1];main=(root/'ikant'/'__main__.py').read_text();cli=(root/'ikant'/'app_cli.py').read_text();self.assertIn('app_cli',main);self.assertNotIn('IKANT_MACHINE_CHANNEL',cli);self.assertNotIn('dashboard_v05',cli);self.assertNotIn('host_v05',cli)
 def test_legacy_modules_are_shims(self):
  root=Path(__file__).parents[1]
  for name,target in [('v05_cli.py','app_cli'),('host_v05.py','runtime_host'),('cognitive_v05.py','cognitive_runtime'),('dashboard_v05.py','human_dashboard')]:self.assertIn(target,(root/'ikant'/name).read_text())
if __name__=='__main__':unittest.main()
