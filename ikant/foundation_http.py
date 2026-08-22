from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
from typing import Any
from .bootstrap_http import build_server as _build_server

FOUNDATION_HTTP_SCHEMA='ikant-foundation-http/v1-test'

def _bundle(assets:Path,name:str)->bytes:
    if name=='app.js':parts=('app.js','epistemic.js','bootstrap.js','foundation.js')
    elif name=='styles.css':parts=('styles.css','epistemic.css','bootstrap.css','foundation.css')
    else:raise ValueError('unsupported foundation bundle')
    return ('\n'.join((assets/p).read_text(encoding='utf-8') for p in parts)+'\n').encode('utf-8')

def build_foundation_server(service:Any,*,token:str,origin:str):
    server=_build_server(service,token=token,origin=origin);Base=server.RequestHandlerClass;assets=Path(__file__).resolve().parent/'web'
    class FoundationHandler(Base):
        def _foundation_asset(self,name,content_type):
            try:data=_bundle(assets,name)
            except Exception as exc:self._json(500,{'schema':FOUNDATION_HTTP_SCHEMA,'error':type(exc).__name__});return
            self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/app.js':self._foundation_asset('app.js','text/javascript; charset=utf-8');return
            if path=='/styles.css':self._foundation_asset('styles.css','text/css; charset=utf-8');return
            if path=='/api/v7/foundation':
                if not self._guard():return
                try:self._json(200,service.foundation_manifest())
                except Exception as exc:self._json(409,{'schema':FOUNDATION_HTTP_SCHEMA,'error':str(exc)[:240]})
                return
            return super().do_GET()
        def do_POST(self):
            path=urlparse(self.path).path
            if path=='/api/v7/foundation/settings':
                if not self._guard(origin=True):return
                try:self._json(200,service.update_foundation_settings(self._read_json()))
                except Exception as exc:self._json(409,{'schema':FOUNDATION_HTTP_SCHEMA,'error':str(exc)[:240]})
                return
            return super().do_POST()
    server.RequestHandlerClass=FoundationHandler
    return server
