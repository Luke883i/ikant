from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from ikant.bootstrap_observability import BootstrapJournal,classify_failure,safe_text
from ikant.bootstrap_runtime import ObservableProductBootstrapCoordinator
from ikant.download_manager import DownloadError
from ikant.engine_supervisor import EngineSupervisor,EngineSupervisorError
from ikant.model_manager import ModelManager
ROOT=Path(__file__).resolve().parents[1]
class BootstrapObservabilityV29Tests(unittest.TestCase):
 def test_journal_is_hash_chained_redacted_and_zero_authority(self):
  with tempfile.TemporaryDirectory() as td:
   j=BootstrapJournal(td);aid='ATT-0000000000001-test';e=j.append(attempt_id=aid,attempt=1,step='MODEL_COMPONENT',outcome='FAIL',code='NETWORK_DOWNLOAD_FAILED',detail='Authorization: Bearer secret https://x.test/a?token=secret',remediation={'id':'CHECK_NETWORK_AND_RETRY','label':'retry','action':'retry'});raw=j.raw_bytes().decode();self.assertNotIn('secret',raw);self.assertEqual(e['epistemic_authority'],0.0);self.assertEqual(e['execution_authority'],0.0);self.assertEqual(j.status(attempt_id=aid,attempt=1)['overall'],'BLOCKED')
 def test_tampered_journal_fails_integrity(self):
  with tempfile.TemporaryDirectory() as td:
   j=BootstrapJournal(td);aid='ATT-0000000000001-test';j.append(attempt_id=aid,attempt=1,step='WEB_APP',outcome='PASS',code='LOCAL_WEB_AVAILABLE');p=Path(td)/'.ikant'/'bootstrap-events.jsonl';p.write_text(p.read_text().replace('LOCAL_WEB_AVAILABLE','LOCAL_WEB_CHANGED'));self.assertEqual(BootstrapJournal(td).state.integrity,'CORRUPT')
 def test_corrupt_journal_blocks_before_runtime_side_effect(self):
  class Runtime:
   called=False
   def start(self,**kwargs):self.called=True;raise AssertionError('must not start')
   def stop(self):pass
  with tempfile.TemporaryDirectory() as td:
   j=BootstrapJournal(td);aid='ATT-0000000000001-test';j.append(attempt_id=aid,attempt=1,step='WEB_APP',outcome='PASS',code='LOCAL_WEB_AVAILABLE');p=Path(td)/'.ikant'/'bootstrap-events.jsonl';p.write_text(p.read_text().replace('LOCAL_WEB_AVAILABLE','LOCAL_WEB_CHANGED'));r=Runtime();c=ObservableProductBootstrapCoordinator(td,runtime=r);out=c.start_async();self.assertFalse(r.called);self.assertEqual(out['stage'],'BLOCKED');self.assertEqual(out['diagnostics']['bootstrap_observability']['fallback_failure']['code'],'BOOTSTRAP_DIAGNOSTICS_CORRUPT')
 def test_network_failure_has_stable_remediation(self):
  try:raise OSError('Temporary failure in name resolution')
  except OSError as cause:
   try:raise DownloadError('component download failed') from cause
   except DownloadError as exc:code,remediation=classify_failure('MODEL_COMPONENT',exc)
  self.assertEqual(code,'NETWORK_DOWNLOAD_FAILED');self.assertEqual(remediation['id'],'CHECK_NETWORK_AND_RETRY')
 def test_model_marker_precedes_downloader_failure(self):
  manifest=json.loads((ROOT/'MODEL_RUNTIME.json').read_text());events=[]
  def fail(*a,**k):raise DownloadError('component download failed')
  with tempfile.TemporaryDirectory() as td:
   manager=ModelManager(manifest,component_root=td,platform='linux-x86_64',downloader=fail)
   with self.assertRaises(DownloadError):manager.ensure_model(progress=events.append)
  self.assertEqual(events[0]['phase'],'CHECKING');self.assertEqual(events[0]['component'],'MODEL_COMPONENT')
 def test_spawn_oserror_is_typed_and_key_removed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);server=root/'llama-server';model=root/'m.gguf';server.write_text('x');server.chmod(0o700);model.write_text('m');sup=EngineSupervisor(root/'.ikant',popen_factory=lambda *a,**k:(_ for _ in ()).throw(OSError('spawn denied')),port_factory=lambda:31337);binding={'manifest_sha256':'a'*64,'engine':{'path':str(server)},'model':{'path':str(model),'id':'Qwen'}}
   with self.assertRaises(EngineSupervisorError):sup.start(binding,timeout=.1)
   self.assertFalse((root/'.ikant'/'runtime'/'llama-api.key').exists())
 def test_raw_redaction_handles_credentials_and_query(self):
  s=safe_text('api_key=abc token=def password=ghi https://host/a?q=secret');self.assertNotIn('abc',s);self.assertNotIn('def',s);self.assertNotIn('ghi',s);self.assertNotIn('secret',s)
if __name__=='__main__':unittest.main()
