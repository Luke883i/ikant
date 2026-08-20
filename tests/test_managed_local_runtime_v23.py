from __future__ import annotations
import copy,hashlib,io,json,os,stat,tarfile,tempfile,unittest
from pathlib import Path
from ikant.component_manifest import ComponentManifestError,load_manifest,platform_key,validate_manifest
from ikant.component_store import ComponentStoreError,safe_extract_tar,tree_digest
from ikant.download_manager import DownloadError,download_verified
from ikant.engine_supervisor import EngineSupervisor,build_server_command,scrubbed_environment
from ikant.managed_runtime import ManagedLocalRuntime
from ikant.model_broker import LocalModelBroker
ROOT=Path(__file__).resolve().parents[1]
class FakeResponse:
 def __init__(self,payload,status=200):self.status=status;self.raw=payload if isinstance(payload,bytes) else json.dumps(payload).encode();self.pos=0
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self,n=-1):
  if n<0:n=len(self.raw)-self.pos
  out=self.raw[self.pos:self.pos+n];self.pos+=len(out);return out
class ManifestTests(unittest.TestCase):
 def test_repository_manifest_is_fully_pinned_and_zero_authority(self):
  d=load_manifest(ROOT/'MODEL_RUNTIME.json');self.assertEqual(validate_manifest(d),[]);self.assertRegex(d['engine']['release_tag'],r'^b\d+$');self.assertRegex(d['model']['revision'],r'^[0-9a-f]{40}$');self.assertEqual(d['authority']['epistemic_authority'],0.0);self.assertEqual(d['authority']['execution_authority'],0.0)
 def test_floating_or_remote_contract_mutations_fail(self):
  base=load_manifest(ROOT/'MODEL_RUNTIME.json');cases=[]
  m=copy.deepcopy(base);m['model']['url']=m['model']['url'].replace(m['model']['revision'],'main');cases.append(m)
  m=copy.deepcopy(base);m['model']['revision']='main';cases.append(m)
  m=copy.deepcopy(base);m['engine']['release_tag']='latest';cases.append(m)
  m=copy.deepcopy(base);m['engine']['server_contract']['host']='0.0.0.0';cases.append(m)
  m=copy.deepcopy(base);m['engine']['server_contract']['webui_enabled']=True;cases.append(m)
  m=copy.deepcopy(base);m['engine']['server_contract']['agent_mode_enabled']=True;cases.append(m)
  m=copy.deepcopy(base);m['engine']['server_contract']['builtin_tools_enabled']=True;cases.append(m)
  m=copy.deepcopy(base);m['authority']['runtime_readiness_is_authority']=True;cases.append(m)
  for mutated in cases:
   with self.subTest(mutated=mutated):self.assertTrue(validate_manifest(mutated))
 def test_platform_normalization_and_fail_closed(self):
  self.assertEqual(platform_key('Darwin','arm64'),'darwin-arm64');self.assertEqual(platform_key('Linux','amd64'),'linux-x86_64')
  with self.assertRaises(ComponentManifestError):platform_key('Windows','AMD64')
class DownloadTests(unittest.TestCase):
 def test_resume_range_is_exact_and_atomic(self):
  data=b'abcdef0123456789';expected=hashlib.sha256(data).hexdigest()
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/'model.gguf';partial=Path(str(target)+'.partial');partial.write_bytes(data[:5]);seen={}
   def opener(req,timeout=None):seen['range']=req.headers.get('Range');return FakeResponse(data[5:],206)
   out=download_verified('https://fixture.test/model.gguf',target,expected,opener=opener,chunk_size=3);self.assertEqual(seen['range'],'bytes=5-');self.assertEqual(out.read_bytes(),data);self.assertFalse(partial.exists())
 def test_server_ignoring_range_restarts_safely(self):
  data=b'canonical'
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/'x';Path(str(target)+'.partial').write_bytes(b'poison');out=download_verified('https://fixture.test/x',target,hashlib.sha256(data).hexdigest(),opener=lambda *a,**k:FakeResponse(data,200));self.assertEqual(out.read_bytes(),data)
 def test_digest_mismatch_never_installs(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/'x'
   with self.assertRaises(DownloadError):download_verified('https://fixture.test/x',target,'0'*64,opener=lambda *a,**k:FakeResponse(b'bad',200))
   self.assertFalse(target.exists());self.assertFalse(Path(str(target)+'.partial').exists())
 def test_non_https_download_rejected(self):
  with tempfile.TemporaryDirectory() as td,self.assertRaises(DownloadError):download_verified('http://fixture.test/x',Path(td)/'x','0'*64)
 def test_download_bound_prevents_disk_amplification(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/'x'
   with self.assertRaises(DownloadError):download_verified('https://fixture.test/x',target,hashlib.sha256(b'abcdef').hexdigest(),opener=lambda *a,**k:FakeResponse(b'abcdef',200),max_bytes=5)
   self.assertFalse(target.exists());self.assertFalse(Path(str(target)+'.partial').exists())
class ArchiveTests(unittest.TestCase):
 def _archive(self,path,*,name='./llama-server',kind='file'):
  with tarfile.open(path,'w:gz') as tf:
   info=tarfile.TarInfo(name);info.mode=0o755
   if kind=='symlink':info.type=tarfile.SYMTYPE;info.linkname='/tmp/escape';tf.addfile(info)
   else:raw=b'binary';info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
 def test_regular_archive_extracts_without_following_links(self):
  with tempfile.TemporaryDirectory() as td:
   archive=Path(td)/'a.tar.gz';self._archive(archive);out=safe_extract_tar(archive,Path(td)/'engine')/'llama-server';self.assertTrue(out.is_file());self.assertTrue(out.stat().st_mode&stat.S_IXUSR)
 def test_traversal_and_symlink_are_rejected(self):
  for name,kind in (('../escape','file'),('link','symlink')):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as td:
    archive=Path(td)/'a.tar.gz';self._archive(archive,name=name,kind=kind)
    with self.assertRaises(ComponentStoreError):safe_extract_tar(archive,Path(td)/'engine')
 def test_installed_tree_digest_detects_post_install_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);f=root/'llama-server';f.write_bytes(b'one');first=tree_digest(root);f.write_bytes(b'two');self.assertNotEqual(first,tree_digest(root))
class FakeProcess:
 def __init__(self):self.ended=False
 def poll(self):return 0 if self.ended else None
 def terminate(self):self.ended=True
 def wait(self,timeout=None):self.ended=True;return 0
 def kill(self):self.ended=True
class SupervisorAndBrokerTests(unittest.TestCase):
 def test_command_is_loopback_private_no_shell_no_agent(self):
  cmd=build_server_command('/engine/llama-server','/model/m.gguf',32123,'/state/key');self.assertEqual(cmd[cmd.index('--host')+1],'127.0.0.1');self.assertIn('--api-key-file',cmd);self.assertIn('--no-webui',cmd);self.assertNotIn('--agent',cmd);self.assertNotIn('--tool',' '.join(cmd))
 def test_supervisor_ready_session_keeps_secret_out_of_command(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);server=root/'llama-server';model=root/'model.gguf';server.write_text('x');server.chmod(0o700);model.write_text('m');captured={};proc=FakeProcess()
   def popen(cmd,**kwargs):captured.update(cmd=cmd,kwargs=kwargs);return proc
   sup=EngineSupervisor(root/'.ikant',popen_factory=popen,readiness_probe=lambda endpoint,key:{'data':[{'id':'model'}]},port_factory=lambda:32123);binding={'manifest_sha256':'a'*64,'engine':{'path':str(server)},'model':{'path':str(model),'id':'Qwen'}};session=sup.start(binding,timeout=.2);self.assertEqual(session['status'],'READY');self.assertNotIn(session['api_key'],captured['cmd']);self.assertFalse(captured['kwargs']['shell']);self.assertEqual(captured['kwargs']['env'],scrubbed_environment());self.assertEqual(stat.S_IMODE(sup.api_key_file.stat().st_mode),0o600);sup.stop();self.assertFalse((root/'.ikant'/'runtime'/'llama-api.key').exists())
 def test_api_key_symlink_is_rejected(self):
  if not hasattr(os,'symlink'):return
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);runtime=root/'.ikant'/'runtime';runtime.mkdir(parents=True);victim=root/'victim';victim.write_text('safe');(runtime/'llama-api.key').symlink_to(victim);sup=EngineSupervisor(root/'.ikant')
   with self.assertRaises(Exception):sup._write_api_key()
   self.assertEqual(victim.read_text(),'safe')
 def test_managed_broker_authenticates_without_exposing_key(self):
  seen=[]
  def opener(req,timeout=None):
   seen.append(req.headers.get('Authorization'))
   if req.get_method()=='GET':return FakeResponse({'data':[{'id':'q'}]})
   return FakeResponse({'choices':[{'message':{'content':'valid response has enough words for validation'}}]})
  broker=LocalModelBroker('http://127.0.0.1:32123/v1/chat/completions',model='Qwen',opener=opener,api_key='secret-key',runtime_binding_digest='b'*64,managed_runtime=True);self.assertTrue(broker.health());broker.complete_surface_a({},'hi',validator=lambda x:(True,[]));self.assertTrue(all(x=='Bearer secret-key' for x in seen));status=broker.status();self.assertNotIn('secret-key',json.dumps(status));self.assertNotIn('endpoint',status);self.assertFalse(status['api_key_exposed'])
class ManagedRuntimeVerticalTests(unittest.TestCase):
 def test_ready_projection_contains_identity_not_transport_secret(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'MODEL_RUNTIME.json').write_bytes((ROOT/'MODEL_RUNTIME.json').read_bytes())
   class Manager:
    def __init__(self,manifest,component_root=None):pass
    def ensure(self,progress=None):return {'manifest_sha256':'a'*64,'engine':{'id':'llama.cpp','version':'b1','platform':'linux-x86_64','artifact_sha256':'c'*64,'path':'/engine'},'model':{'id':'Qwen','revision':'d'*40,'sha256':'e'*64,'path':'/model'}}
   class Supervisor:
    def __init__(self,state_dir):pass
    def start(self,binding,timeout=45):return {'status':'READY','endpoint':'http://127.0.0.1:31337/v1/chat/completions','api_key':'private','model_id':'Qwen','browser_model_transport':False}
    def stop(self):pass
   runtime=ManagedLocalRuntime(root,manager_factory=Manager,supervisor_factory=Supervisor);broker=runtime.start();projection=json.loads((root/'.ikant'/'model-runtime.json').read_text());self.assertEqual(projection['status'],'READY');self.assertTrue(broker.managed_runtime);raw=json.dumps(projection);self.assertNotIn('private',raw);self.assertNotIn('31337',raw);self.assertFalse(projection['api_key_persisted']);runtime.stop();self.assertEqual(json.loads((root/'.ikant'/'model-runtime.json').read_text())['status'],'STOPPED')
if __name__=='__main__':unittest.main()
