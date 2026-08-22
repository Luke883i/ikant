from __future__ import annotations
import json,os,secrets,socket,stat,subprocess,time
from pathlib import Path
from typing import Any,Callable
from urllib.request import Request,urlopen
from .engine_exit_diagnostics import BoundedStderrCapture,EngineExitDiagnostic
ENGINE_SESSION_SCHEMA='ikant-managed-engine-session/v0.23-test'
class EngineSupervisorError(RuntimeError):
 def __init__(self,message:str,*,process_exit:dict[str,object]|None=None):
  super().__init__(message)
  if process_exit is not None:self.process_exit=process_exit
def reserve_loopback_port()->int:
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:sock.bind(('127.0.0.1',0));return int(sock.getsockname()[1])
def scrubbed_environment(source:dict[str,str]|None=None)->dict[str,str]:
 src=os.environ if source is None else source;allow=('HOME','PATH','TMPDIR','TEMP','TMP','LANG','LC_ALL','LC_CTYPE');return {key:str(src[key]) for key in allow if src.get(key)}
def build_server_command(server:str|Path,model:str|Path,port:int,api_key_file:str|Path)->list[str]:
 if not (1<=int(port)<=65535):raise EngineSupervisorError('invalid llama-server port')
 return [str(server),'-m',str(model),'--host','127.0.0.1','--port',str(int(port)),'--api-key-file',str(api_key_file),'--no-webui']
def _default_probe(endpoint:str,api_key:str,*,timeout:float=1.5)->dict[str,Any]|None:
 url=endpoint.rsplit('/v1/chat/completions',1)[0]+'/v1/models';req=Request(url,method='GET',headers={'Accept':'application/json','Authorization':'Bearer '+api_key})
 try:
  with urlopen(req,timeout=timeout) as response:
   if not (200<=int(getattr(response,'status',200))<300):return None
   raw=response.read(1024*1024+1)
 except Exception:return None
 if len(raw)>1024*1024:return None
 try:value=json.loads(raw.decode('utf-8'))
 except Exception:return None
 return value if isinstance(value,dict) else None
class EngineSupervisor:
 def __init__(self,state_dir:str|Path,*,popen_factory:Callable[...,Any]=subprocess.Popen,readiness_probe:Callable[[str,str],dict[str,Any]|None]|None=None,port_factory:Callable[[],int]=reserve_loopback_port):self.state_dir=Path(state_dir).resolve();self.popen_factory=popen_factory;self.readiness_probe=readiness_probe or _default_probe;self.port_factory=port_factory;self.process=None;self.stderr_capture=None;self.api_key_file=None;self.api_key=None;self.endpoint=None;self.progress=None
 def _emit(self,phase:str,target:str,detail:str)->None:
  if callable(self.progress):self.progress({'phase':phase,'component':'ENGINE_PROCESS' if phase=='ENGINE_STARTING' else 'ENGINE_READINESS','target':target,'bytes':0,'detail':detail})
 def _write_api_key(self)->tuple[Path,str]:
  runtime_dir=self.state_dir/'runtime';runtime_dir.mkdir(parents=True,exist_ok=True)
  if runtime_dir.is_symlink():raise EngineSupervisorError('runtime key directory may not be a symlink')
  key=secrets.token_urlsafe(32);path=runtime_dir/'llama-api.key'
  if path.exists() or path.is_symlink():
   st=path.lstat()
   if not stat.S_ISREG(st.st_mode) or path.is_symlink():raise EngineSupervisorError('runtime key path is not a regular file')
   path.unlink()
  flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
  if hasattr(os,'O_NOFOLLOW'):flags|=os.O_NOFOLLOW
  fd=os.open(path,flags,0o600)
  try:os.write(fd,(key+'\n').encode());os.fsync(fd)
  finally:os.close(fd)
  return path,key
 def _exit_diagnostic(self)->EngineExitDiagnostic:
  proc=self.process;capture=self.stderr_capture
  if capture is not None:capture.finish(timeout=1.0)
  return EngineExitDiagnostic.capture(proc.poll() if proc is not None else None,capture.snapshot() if capture is not None else b'')
 def start(self,binding:dict[str,Any],*,timeout:float=45.0)->dict[str,Any]:
  self._emit('ENGINE_STARTING','llama-server','preflighting and starting verified local engine process')
  if self.process is not None:raise EngineSupervisorError('llama-server already supervised')
  server=Path(binding['engine']['path']);model=Path(binding['model']['path'])
  if not server.is_file() or not os.access(server,os.X_OK) or not model.is_file():raise EngineSupervisorError('verified engine/model paths unavailable')
  key_file=None
  try:
   port=self.port_factory();key_file,key=self._write_api_key();command=build_server_command(server,model,port,key_file);self.process=self.popen_factory(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=str(server.parent),env=scrubbed_environment(),shell=False);capture=BoundedStderrCapture();capture.start(getattr(self.process,'stderr',None));self.stderr_capture=capture
  except EngineSupervisorError:
   if key_file is not None:key_file.unlink(missing_ok=True)
   raise
  except Exception as exc:
   if key_file is not None:key_file.unlink(missing_ok=True)
   raise EngineSupervisorError('llama-server process start failed') from exc
  self.api_key_file,self.api_key=key_file,key;self.endpoint=f'http://127.0.0.1:{port}/v1/chat/completions';self._emit('ENGINE_PROBING','llama-server','process started; waiting for constrained loopback readiness');deadline=time.monotonic()+float(timeout)
  while time.monotonic()<deadline:
   if self.process.poll() is not None:
    diagnostic=self._exit_diagnostic();error=EngineSupervisorError('llama-server exited before readiness',process_exit=diagnostic.as_dict());self.stop();raise error
   try:ready=self.readiness_probe(self.endpoint,key)
   except Exception as exc:self.stop();raise EngineSupervisorError('llama-server readiness probe failed') from exc
   if ready is not None:self._emit('ENGINE_READY','llama-server','constrained loopback readiness probe passed');return {'schema':ENGINE_SESSION_SCHEMA,'status':'READY','endpoint':self.endpoint,'api_key':key,'model_id':binding['model']['id'],'manifest_sha256':binding['manifest_sha256'],'browser_model_transport':False,'builtin_tools_enabled':False,'agent_mode_enabled':False,'webui_enabled':False,'model_output_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
   time.sleep(.1)
  self.stop();raise EngineSupervisorError('llama-server readiness timeout')
 def stop(self)->None:
  proc,self.process=self.process,None;capture,self.stderr_capture=self.stderr_capture,None
  if proc is not None:
   try:
    if proc.poll() is None:
     proc.terminate()
     try:proc.wait(timeout=5)
     except Exception:proc.kill();proc.wait(timeout=2)
   except Exception:pass
  if capture is not None:capture.finish(timeout=1.0)
  if self.api_key_file is not None:self.api_key_file.unlink(missing_ok=True)
  self.api_key_file=None;self.api_key=None;self.endpoint=None
