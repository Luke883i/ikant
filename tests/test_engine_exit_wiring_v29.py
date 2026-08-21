from __future__ import annotations
import json,os,signal,subprocess,sys,tempfile,unittest
from pathlib import Path
from ikant.bootstrap_observability import BootstrapJournal,exception_chain
from ikant.engine_exit_diagnostics import MAX_STDERR_CAPTURE_BYTES,MAX_STDERR_TAIL_BYTES,EngineExitDiagnostic,bounded_stderr_tail
from ikant.engine_supervisor import EngineSupervisor,EngineSupervisorError

class WiringTests(unittest.TestCase):
 def binding(self,root):
  server=root/'llama-server';model=root/'model.gguf';server.write_text('x');server.chmod(0o700);model.write_text('m')
  return {'manifest_sha256':'a'*64,'engine':{'path':str(server)},'model':{'path':str(model),'id':'Qwen'}}
 def test_real_process_exit_is_captured_before_stop(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   def popen(_cmd,**kwargs):return subprocess.Popen([sys.executable,'-c',"import os;os.write(2,b'loader failed\\n');raise SystemExit(127)"],**kwargs)
   sup=EngineSupervisor(root/'.ikant',popen_factory=popen,readiness_probe=lambda *a:None,port_factory=lambda:31337)
   with self.assertRaises(EngineSupervisorError) as cm:sup.start(self.binding(root),timeout=2)
   d=cm.exception.process_exit;self.assertEqual(d['kind'],'EXIT_STATUS');self.assertEqual(d['returncode'],127);self.assertIsNone(d['signal']);self.assertIn('loader failed',d['stderr_tail']);self.assertIsNone(sup.process);self.assertIsNone(sup.stderr_capture)
 def test_real_process_large_stderr_does_not_deadlock(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);n=MAX_STDERR_CAPTURE_BYTES*8
   def popen(_cmd,**kwargs):
    code=f"import os;os.write(2,b'x'*{n});os.write(2,b'\\nTAIL-MARKER\\n');raise SystemExit(23)";return subprocess.Popen([sys.executable,'-c',code],**kwargs)
   sup=EngineSupervisor(root/'.ikant',popen_factory=popen,readiness_probe=lambda *a:None,port_factory=lambda:31337)
   with self.assertRaises(EngineSupervisorError) as cm:sup.start(self.binding(root),timeout=3)
   d=cm.exception.process_exit;self.assertEqual(d['returncode'],23);self.assertIn('TAIL-MARKER',d['stderr_tail']);self.assertLessEqual(len(d['stderr_tail'].encode()),MAX_STDERR_TAIL_BYTES)
 def test_signal_is_preserved_mechanically(self):
  if os.name=='nt':self.skipTest('POSIX')
  d=EngineExitDiagnostic.capture(-signal.SIGTERM,b'killed');self.assertEqual((d.kind,d.returncode,d.signal),('SIGNAL',-signal.SIGTERM,signal.SIGTERM))
 def test_exception_chain_and_journal_preserve_process_exit(self):
  d=EngineExitDiagnostic.capture(127,b'token=secret loader failed')
  try:
   try:raise EngineSupervisorError('llama-server exited before readiness',process_exit=d.as_dict())
   except EngineSupervisorError as inner:raise RuntimeError('managed local runtime failed closed') from inner
  except RuntimeError as outer:chain=exception_chain(outer)
  self.assertIn('process_exit',chain[1]);self.assertNotIn('secret',json.dumps(chain))
  with tempfile.TemporaryDirectory() as td:
   j=BootstrapJournal(td);aid='ATT-0000000000001-hotfix2';e=j.append(attempt_id=aid,attempt=1,step='ENGINE_READINESS',outcome='FAIL',code='ENGINE_EXITED_EARLY',detail='llama-server exited before readiness',cause_chain=chain)
   p=e['cause_chain'][1]['process_exit'];self.assertEqual(p['returncode'],127);self.assertIn('loader failed',p['stderr_tail']);self.assertNotIn('secret',json.dumps(e));self.assertLess(len(j.raw_bytes()),16*1024)
   row=next(x for x in j.status(attempt_id=aid,attempt=1)['steps'] if x['id']=='ENGINE_READINESS');self.assertEqual(row['cause_chain'][1]['process_exit']['returncode'],127)
 def test_long_secret_marker_is_redacted_before_public_tail_slice(self):
  raw=b'token='+b'A'*6000+b' end';out=bounded_stderr_tail(raw);self.assertNotIn('AAAA',out);self.assertLessEqual(len(out.encode()),MAX_STDERR_TAIL_BYTES)

if __name__=='__main__':unittest.main()
