from __future__ import annotations
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .epistemic_http import make_epistemic_handler
from .local_security import PairingSession,allowed_hostnames
from .local_web_host import LocalWebHostAdapter

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
 return Handler

def build_server(service,*,host,port,pairing=None,assets_dir=None,env=None):
 pairing=pairing or PairingSession.create();assets=Path(assets_dir) if assets_dir is not None else Path(__file__).with_name('web');provisional=allowed_hostnames(int(port),bind_host=host,env=env);server=ThreadingHTTPServer((host,int(port)),make_bootstrap_handler(service,pairing,assets_dir=assets,allowed_hosts=provisional,expected_port=int(port)));server.daemon_threads=True;effective=int(server.server_address[1]);hosts=allowed_hostnames(effective,bind_host=host,env=env);server.RequestHandlerClass=make_bootstrap_handler(service,pairing,assets_dir=assets,allowed_hosts=hosts,expected_port=effective);service.bind_web_adapter(LocalWebHostAdapter(str(host),effective,tuple(sorted(hosts))));return server,pairing
