from __future__ import annotations
import json,mimetypes
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any
from .local_security import PairingSession,allowed_hostnames,is_loopback_hostname,origin_allowed
from .local_web_host import LocalWebHostAdapter
from .local_service import LOCAL_APP_SCHEMA,LocalAppError,runtime_active
from .voice_input import LocalVoiceError
_MAX_JSON=128*1024;_MAX_AUDIO=8*1024*1024

def _read_json(h,limit=_MAX_JSON):
    try:n=int(h.headers.get('Content-Length') or '0')
    except ValueError as exc:raise LocalAppError('invalid Content-Length') from exc
    if n<=0 or n>limit:raise LocalAppError('request body outside bound')
    try:x=json.loads(h.rfile.read(n).decode())
    except Exception as exc:raise LocalAppError('invalid JSON request') from exc
    if not isinstance(x,dict):raise LocalAppError('JSON request must be object')
    return x

def _split_host(raw):
    raw=str(raw or '').strip().lower()
    if not raw:return '',None
    if raw.startswith('['):
        end=raw.find(']')
        if end<0:return raw,None
        host=raw[:end+1];rest=raw[end+1:]
        if not rest:return host,None
        return (host,int(rest[1:])) if rest.startswith(':') and rest[1:].isdigit() else (host,-1)
    if ':' not in raw:return raw,None
    host,port=raw.rsplit(':',1);return (host,int(port)) if port.isdigit() else (host,-1)

def host_header_allowed(raw,allowed_hosts,expected_port):
    host,port=_split_host(raw)
    if host not in allowed_hosts:return False
    if is_loopback_hostname(host.strip('[]')):return port==int(expected_port)
    return port in {None,443}

def make_handler(service,pairing,*,assets_dir:Path,allowed_hosts:frozenset[str],expected_port:int):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,format,*args):return
        def _headers(self,ctype='application/json; charset=utf-8'):
            for k,v in (
                ('Content-Type',ctype),('Cache-Control','no-store'),('Referrer-Policy','no-referrer'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Cross-Origin-Resource-Policy','same-origin'),
                ('Content-Security-Policy',"default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'none'")):
                self.send_header(k,v)
        def _json(self,status,payload):
            raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();self.send_response(status);self._headers();self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush()
        def _empty(self,status):
            self.send_response(status);self._headers();self.send_header('Content-Length','0');self.end_headers();self.wfile.flush()
        def _error(self,status,message):self._empty(status) if runtime_active(service.root) else self._json(status,{'schema':LOCAL_APP_SCHEMA,'error':str(message)})
        def _guard(self,auth=True,origin=False):
            host=str(self.headers.get('Host') or '').strip().lower()
            if not host_header_allowed(host,allowed_hosts,expected_port):self._error(421,'host not allowed');return False
            if origin and not origin_allowed(self.headers.get('Origin'),host):self._error(403,'origin not allowed');return False
            if auth and not pairing.authenticate(self.headers.get('Authorization')):self._error(401,'pairing authentication required');return False
            return True
        def _shell_claimed(self):
            check=getattr(service,'shell_claimed',None)
            try:return bool(check()) if callable(check) else False
            except Exception:return True
        def _legacy_active_blocked(self,path):
            return runtime_active(service.root) and self._shell_claimed() and path in {'/api/v1/frame','/api/v1/frame/ack','/api/v1/turn','/api/v1/resume','/api/v1/initialize','/api/v1/voice/transcribe'}
        def do_GET(self):
            path=self.path.split('?',1)[0]
            if path.startswith('/api/'):
                if path=='/api/v1/public':
                    if self._guard(auth=False):self._json(200,pairing.public_status())
                    return
                if not self._guard():return
                if self._legacy_active_blocked(path):self._empty(409);return
                try:
                    if path=='/api/v1/state':out=service.lifecycle()
                    elif path=='/api/v1/admission':out=service.admission_view()
                    elif path=='/api/v1/frame':out=service.frame()
                    else:self._error(404,'unknown API route');return
                    self._json(200,out)
                except PermissionError as exc:self._error(403,str(exc))
                except Exception as exc:self._error(409,str(exc))
                return
            if not self._guard(auth=False):return
            name='index.html' if path in {'','/'} else path.lstrip('/')
            if name not in {'index.html','app.js','styles.css','manifest.webmanifest','sw.js'}:self._error(404,'asset not found');return
            file=assets_dir/name
            if not file.is_file():self._error(404,'asset missing');return
            raw=file.read_bytes();ctype=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            if name.endswith('.js'):ctype='text/javascript; charset=utf-8'
            elif name.endswith('.html'):ctype='text/html; charset=utf-8'
            elif name.endswith('.css'):ctype='text/css; charset=utf-8'
            elif name.endswith('.webmanifest'):ctype='application/manifest+json; charset=utf-8'
            self.send_response(200);self._headers(ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush()
        def do_POST(self):
            path=self.path.split('?',1)[0]
            if path=='/api/v1/pair':
                if not self._guard(auth=False,origin=True):return
                try:self._json(200,{'schema':LOCAL_APP_SCHEMA,'paired':True,'bearer_token':pairing.pair(str(_read_json(self).get('code') or ''))})
                except PermissionError as exc:self._error(403,str(exc))
                except Exception as exc:self._error(400,str(exc))
                return
            if not self._guard(origin=True):return
            if path.startswith('/api/v2/shell/'):
                try:
                    body=_read_json(self)
                    if path=='/api/v2/shell/open':out=service.shell_open(body.get('client_id'))
                    elif path=='/api/v2/shell/command':out=service.shell_command(body)
                    elif path=='/api/v2/shell/ack':out=service.shell_ack(body)
                    else:self._empty(404);return
                    self._json(200,out)
                except Exception:self._empty(409)
                return
            if self._legacy_active_blocked(path):self._empty(409);return
            try:
                if path=='/api/v1/voice/transcribe':
                    try:n=int(self.headers.get('Content-Length') or '0')
                    except ValueError as exc:raise LocalAppError('invalid Content-Length') from exc
                    if n<=0 or n>_MAX_AUDIO:raise LocalAppError('audio body outside bound')
                    self._json(200,service.transcribe(self.rfile.read(n),self.headers.get('Content-Type') or ''));return
                body=_read_json(self)
                if path=='/api/v1/accept':out=service.accept(str(body.get('phrase') or ''),str(body.get('presented_terms_sha256') or ''))
                elif path=='/api/v1/probe':out=service.probe()
                elif path=='/api/v1/initialize':out=service.initialize()
                elif path=='/api/v1/frame/ack':out=service.acknowledge(body)
                elif path=='/api/v1/turn':out=service.turn(str(body.get('text') or ''))
                elif path=='/api/v1/resume':out=service.resume(str(body.get('text') or ''))
                else:self._error(404,'unknown API route');return
                self._json(200,out)
            except (PermissionError,LocalVoiceError) as exc:self._active_notice_or_error(exc,403,'LOCAL_INPUT_ERROR')
            except Exception as exc:self._active_notice_or_error(exc,409,'LOCAL_RUNTIME_ERROR')
        def _active_notice_or_error(self,exc,status,kind):
            if runtime_active(service.root):
                try:self._json(200,service.notice(str(exc),kind=kind))
                except Exception:self._error(status,'local runtime unavailable')
            else:self._error(status,str(exc))
    return Handler

def build_server(service,*,host,port,pairing=None,assets_dir=None,env=None):
    pairing=pairing or PairingSession.create();assets=Path(assets_dir) if assets_dir is not None else Path(__file__).with_name('web')
    provisional=allowed_hostnames(int(port),bind_host=host,env=env)
    server=ThreadingHTTPServer((host,int(port)),make_handler(service,pairing,assets_dir=assets,allowed_hosts=provisional,expected_port=int(port)));server.daemon_threads=True
    effective=int(server.server_address[1]);hosts=allowed_hostnames(effective,bind_host=host,env=env)
    server.RequestHandlerClass=make_handler(service,pairing,assets_dir=assets,allowed_hosts=hosts,expected_port=effective)
    service.bind_web_adapter(LocalWebHostAdapter(str(host),effective,tuple(sorted(hosts))))
    return server,pairing
