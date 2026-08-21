from __future__ import annotations
import json,mimetypes
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .local_http import make_handler
from .local_security import PairingSession,allowed_hostnames
from .local_web_host import LocalWebHostAdapter


def make_epistemic_handler(service,pairing,*,assets_dir:Path,allowed_hosts:frozenset[str],expected_port:int):
 Base=make_handler(service,pairing,assets_dir=assets_dir,allowed_hosts=allowed_hosts,expected_port=expected_port)
 class Handler(Base):
  def _epistemic_binding(self):
   try:epoch=int(self.headers.get('X-iKant-Frame-Epoch') or '0');seq=int(self.headers.get('X-iKant-Frame-Seq') or '0')
   except ValueError:raise PermissionError('invalid epistemic frame binding')
   return {'shell_id':self.headers.get('X-iKant-Shell-Id'),'client_id':self.headers.get('X-iKant-Client-Id'),'frame':{'runtime_session_id':self.headers.get('X-iKant-Frame-Session'),'epoch':epoch,'frame_seq':seq,'frame_sha256':self.headers.get('X-iKant-Frame-SHA256')}}
  def _bytes(self,status,raw,ctype,*,name=None,sha256=None):
   self.send_response(status);self._headers(ctype)
   if name:self.send_header('Content-Disposition','attachment; filename="'+str(name).replace('"','')+'"')
   if sha256:self.send_header('X-iKant-Artifact-SHA256',str(sha256))
   self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush()
  def _composed_asset(self,name):
   if name not in {'app.js','styles.css'}:return False
   if not self._guard(auth=False):return True
   base=assets_dir/name;extra=assets_dir/('epistemic.js' if name=='app.js' else 'epistemic.css')
   if not base.is_file() or not extra.is_file():self._error(404,'asset missing');return True
   raw=base.read_bytes()+b'\n'+extra.read_bytes();ctype='text/javascript; charset=utf-8' if name.endswith('.js') else 'text/css; charset=utf-8'
   self.send_response(200);self._headers(ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush();return True
  def do_GET(self):
   split=urlsplit(self.path);path=split.path
   if path in {'/app.js','/styles.css'} and self._composed_asset(path.lstrip('/')):return
   if not path.startswith('/api/v4/epistemic/'):return super().do_GET()
   if not self._guard():return
   query=parse_qs(split.query,keep_blank_values=False)
   try:
    b=self._epistemic_binding();cycle=(query.get('cycle_id') or [None])[0]
    if path=='/api/v4/epistemic/index':self._json(200,service.epistemic_index(b['shell_id'],b['client_id'],b['frame']))
    elif path=='/api/v4/epistemic/cycle':self._json(200,service.epistemic_cycle(cycle,b['shell_id'],b['client_id'],b['frame']))
    elif path=='/api/v4/epistemic/artifact':
     kind=(query.get('kind') or [None])[0];meta,raw,ctype=service.epistemic_artifact(cycle,kind,b['shell_id'],b['client_id'],b['frame']);self._bytes(200,raw,ctype,name=meta.get('name'),sha256=meta.get('sha256'))
    else:self._empty(404)
   except Exception:self._empty(409)
 return Handler


def build_server(service,*,host,port,pairing=None,assets_dir=None,env=None):
 pairing=pairing or PairingSession.create();assets=Path(assets_dir) if assets_dir is not None else Path(__file__).with_name('web')
 provisional=allowed_hostnames(int(port),bind_host=host,env=env);server=ThreadingHTTPServer((host,int(port)),make_epistemic_handler(service,pairing,assets_dir=assets,allowed_hosts=provisional,expected_port=int(port)));server.daemon_threads=True
 effective=int(server.server_address[1]);hosts=allowed_hostnames(effective,bind_host=host,env=env);server.RequestHandlerClass=make_epistemic_handler(service,pairing,assets_dir=assets,allowed_hosts=hosts,expected_port=effective);service.bind_web_adapter(LocalWebHostAdapter(str(host),effective,tuple(sorted(hosts))))
 return server,pairing
