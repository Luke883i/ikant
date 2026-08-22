from __future__ import annotations
import re
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .epistemic_http import make_epistemic_handler
from .experience_projection import runtime_projection
from .foundation import FoundationConfigError,foundation_projection,load_experiment_config,update_experiment_config
from .local_http import _MAX_AUDIO,_read_json
from .local_security import PairingSession,allowed_hostnames
from .local_web_host import LocalWebHostAdapter

TRANSPORT_DIAGNOSTIC_SCHEMA='ikant-interactive-transport-diagnostic/v0.29-test'
_SECRET_PATTERNS=(re.compile(r'(?i)Bearer\s+[A-Za-z0-9._~+\/-]+'),re.compile(r'(?i)((?:token|password|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+'))

def transport_diagnostic(path,exc):
 message=str(exc or 'local transport failure').replace('\x00',' ')
 for pattern in _SECRET_PATTERNS:message=pattern.sub(lambda m:('Bearer [REDACTED]' if m.group(0).lower().startswith('bearer ') else m.group(1)+'[REDACTED]'),message)
 message=' '.join(message.split())[:240] or 'local transport failure'
 return {'schema':TRANSPORT_DIAGNOSTIC_SCHEMA,'path':str(path)[:120],'code':type(exc).__name__[:80],'message':message,'retryable':False,'presentation_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}

def make_bootstrap_handler(service,pairing,*,assets_dir:Path,allowed_hosts:frozenset[str],expected_port:int):
 Base=make_epistemic_handler(service,pairing,assets_dir=assets_dir,allowed_hosts=allowed_hosts,expected_port=expected_port)
 class Handler(Base):
  def _composed_asset(self,name):
   if name not in {'app.js','styles.css','conversation.js'}:return False
   if not self._guard(auth=False):return True
   if name=='app.js':files=(assets_dir/'app.js',assets_dir/'epistemic.js',assets_dir/'bootstrap.js')
   elif name=='styles.css':files=(assets_dir/'styles.css',assets_dir/'epistemic.css',assets_dir/'bootstrap.css')
   else:files=(assets_dir/'conversation.js',)
   if any(not p.is_file() for p in files):self._error(404,'asset missing');return True
   raw=b'\n'.join(p.read_bytes() for p in files);ctype='text/javascript; charset=utf-8' if name.endswith('.js') else 'text/css; charset=utf-8';self.send_response(200);self._headers(ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush();return True
  def do_GET(self):
   split=urlsplit(self.path);path=split.path
   if path in {'/app.js','/styles.css','/conversation.js'} and self._composed_asset(path.lstrip('/')):return
   if path=='/api/v6/experience':
    if not self._guard():return
    try:self._json(200,runtime_projection(service.root))
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   if path=='/api/v7/foundation':
    if not self._guard():return
    try:self._json(200,foundation_projection(service))
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   if path=='/api/v7/config':
    if not self._guard():return
    try:self._json(200,load_experiment_config(service.root))
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   if not path.startswith('/api/v5/bootstrap/'):return super().do_GET()
   if not self._guard():return
   query=parse_qs(split.query,keep_blank_values=False)
   try:
    if path=='/api/v5/bootstrap/status':self._json(200,service.bootstrap_status())
    elif path=='/api/v5/bootstrap/events':self._json(200,service.bootstrap_events((query.get('after_seq') or [0])[0],(query.get('limit') or [128])[0]))
    elif path=='/api/v5/bootstrap/raw':
     raw,ctype=service.bootstrap_raw();self._bytes(200,raw,ctype,name='ikant-bootstrap-events.jsonl')
    else:self._empty(404)
   except Exception:self._empty(409)
  def do_POST(self):
   path=urlsplit(self.path).path
   if path=='/api/v7/config':
    if not self._guard(origin=True):return
    try:self._json(200,update_experiment_config(service,_read_json(self)))
    except FoundationConfigError as exc:self._json(409,transport_diagnostic(path,exc))
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   if path.startswith('/api/v2/shell/'):
    if not self._guard(origin=True):return
    try:
     body=_read_json(self)
     if path=='/api/v2/shell/open':out=service.shell_open(body.get('client_id'))
     elif path=='/api/v2/shell/command':out=service.shell_command(body)
     elif path=='/api/v2/shell/ack':out=service.shell_ack(body)
     else:self._json(404,transport_diagnostic(path,LookupError('unknown shell route')));return
     self._json(200,out)
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   if path=='/api/v3/voice/transcribe':
    if not self._guard(origin=True):return
    try:
     try:n=int(self.headers.get('Content-Length') or '0')
     except ValueError as exc:raise ValueError('invalid Content-Length') from exc
     if n<=0 or n>_MAX_AUDIO:raise ValueError('audio body outside bound')
     shell_id=self.headers.get('X-iKant-Shell-Id');client_id=self.headers.get('X-iKant-Client-Id')
     out=service.shell_voice_candidate(shell_id,client_id,self.rfile.read(n),self.headers.get('Content-Type') or '')
     self._json(200,out)
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   return super().do_POST()
 return Handler

def build_server(service,*,host,port,pairing=None,assets_dir=None,env=None):
 pairing=pairing or PairingSession.create();assets=Path(assets_dir) if assets_dir is not None else Path(__file__).with_name('web');provisional=allowed_hostnames(int(port),bind_host=host,env=env);server=ThreadingHTTPServer((host,int(port)),make_bootstrap_handler(service,pairing,assets_dir=assets,allowed_hosts=provisional,expected_port=int(port)));server.daemon_threads=True;effective=int(server.server_address[1]);hosts=allowed_hostnames(effective,bind_host=host,env=env);server.RequestHandlerClass=make_bootstrap_handler(service,pairing,assets_dir=assets,allowed_hosts=hosts,expected_port=effective);service.bind_web_adapter(LocalWebHostAdapter(str(host),effective,tuple(sorted(hosts))));return server,pairing
