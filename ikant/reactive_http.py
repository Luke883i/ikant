from __future__ import annotations
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .bootstrap_http import make_bootstrap_handler,transport_diagnostic
from .foundation import load_experiment_config
from .local_security import PairingSession,allowed_hostnames
from .local_http import _read_json
from .local_web_host import LocalWebHostAdapter
from .reactive_hybrid import active_session,store_for_root
from .surface_contract import record_config_effect,surface_snapshot


def _turn_text(body):
 if not isinstance(body,dict) or str(body.get('op') or '').upper()!='TURN':return None
 payload=body.get('payload')
 if not isinstance(payload,dict) or set(payload)!={'text'} or not isinstance(payload.get('text'),str):return None
 return payload['text'] if payload['text'].strip() else None

def _cycle(out):
 frame=out.get('frame') if isinstance(out,dict) else None;receipt=frame.get('receipt') if isinstance(frame,dict) else None
 return str(receipt.get('cycle_id') or '') if isinstance(receipt,dict) else ''

def _has_frame(out):
 return isinstance(out,dict) and isinstance(out.get('frame'),dict)

def make_reactive_handler(service,pairing,*,assets_dir:Path,allowed_hosts:frozenset[str],expected_port:int):
 Base=make_bootstrap_handler(service,pairing,assets_dir=assets_dir,allowed_hosts=allowed_hosts,expected_port=expected_port)
 class Handler(Base):
  def _composed_asset(self,name):
   if name not in {'app.js','styles.css'}:return super()._composed_asset(name)
   if not self._guard(auth=False):return True
   if name=='app.js':files=(assets_dir/'app.js',assets_dir/'epistemic.js',assets_dir/'bootstrap.js',assets_dir/'surface-contract.js',assets_dir/'reactive-hybrid.js')
   else:files=(assets_dir/'styles.css',assets_dir/'epistemic.css',assets_dir/'bootstrap.css',assets_dir/'reactive-hybrid.css')
   if any(not p.is_file() for p in files):self._error(404,'asset missing');return True
   raw=b'\n'.join(p.read_bytes() for p in files);ctype='text/javascript; charset=utf-8' if name.endswith('.js') else 'text/css; charset=utf-8';self.send_response(200);self._headers(ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush();return True
  def do_GET(self):
   path=urlsplit(self.path).path
   if path in {'/api/v9/work/current','/api/v10/surface'}:
    if not self._guard():return
    try:
     session=active_session(service.root);work=store_for_root(service.root).projection(session)
     if path=='/api/v9/work/current':self._json(200,work)
     else:self._json(200,surface_snapshot(service,work=work))
    except Exception as exc:self._json(409,transport_diagnostic(path,exc))
    return
   return super().do_GET()
  def do_POST(self):
   path=urlsplit(self.path).path
   if path not in {'/api/v2/shell/command','/api/v2/shell/ack'}:return super().do_POST()
   if not self._guard(origin=True):return
   store=None;wid=None;session=None;canonical_frame=False
   try:
    body=_read_json(self);session=active_session(service.root);store=store_for_root(service.root)
    if path=='/api/v2/shell/command':
     text=_turn_text(body)
     if text is not None and not store.active(session):wid,_=store.begin(session,text)
     out=service.shell_command(body)
     if wid:
      canonical_frame=_has_frame(out)
      if canonical_frame:
       store.seal_from_canonical(wid,_cycle(out))
       # The delegate TURN lock spans generation and frame sealing; while the frame is pending,
       # S12 configuration mutation is rejected. Reading here therefore binds the revision that
       # could actually have been consumed by this cycle, rather than a racy pre-TURN observation.
       try:record_config_effect(service.root,config=load_experiment_config(service.root),frame=out['frame'])
       except Exception:pass
      else:store.fail(wid)
    else:
     out=service.shell_ack(body)
     if isinstance(out,dict) and out.get('acknowledged') is True:store.deliver_current(session)
    self._json(200,out)
   except Exception as exc:
    # Once the canonical shell has produced a frame, projection/HTTP failures may not rewrite
    # that already-materialized semantic result as FAILED. Exact ACK remains the terminal owner.
    if wid and store and not canonical_frame:
     try:store.fail(wid)
     except Exception:pass
    try:self._json(409,transport_diagnostic(path,exc))
    except Exception:pass
 return Handler

def build_server(service,*,host,port,pairing=None,assets_dir=None,env=None):
 pairing=pairing or PairingSession.create();assets=Path(assets_dir) if assets_dir is not None else Path(__file__).with_name('web');provisional=allowed_hostnames(int(port),bind_host=host,env=env);server=ThreadingHTTPServer((host,int(port)),make_reactive_handler(service,pairing,assets_dir=assets,allowed_hosts=provisional,expected_port=int(port)));server.daemon_threads=True;effective=int(server.server_address[1]);hosts=allowed_hostnames(effective,bind_host=host,env=env);server.RequestHandlerClass=make_reactive_handler(service,pairing,assets_dir=assets,allowed_hosts=hosts,expected_port=effective);service.bind_web_adapter(LocalWebHostAdapter(str(host),effective,tuple(sorted(hosts))));return server,pairing
