from __future__ import annotations
import argparse,os,webbrowser
from pathlib import Path
from .local_http import build_server
from .local_service import LocalEmbodimentService,LocalAppError,operational_fallback
from .local_security import PairingSession
from .model_broker import LocalModelBroker
from .voice_input import LocalVoiceInputBroker
_operational_fallback=operational_fallback

def main(argv=None):
    ap=argparse.ArgumentParser(prog='ikant-web');ap.add_argument('--host');ap.add_argument('--port',type=int,default=int(os.environ.get('IKANT_PORT','8765')));ap.add_argument('--no-open',action='store_true');a=ap.parse_args(argv)
    codespaces=str(os.environ.get('CODESPACES') or '').lower()=='true';host=a.host or ('0.0.0.0' if codespaces else '127.0.0.1');root=Path.cwd()
    from .store import acquire_writer_lock
    lock=acquire_writer_lock(root/'.ikant'/'local-app.writer.lock')
    server=None
    try:
        model=LocalModelBroker(os.environ.get('IKANT_MODEL_ENDPOINT','http://127.0.0.1:8080/v1/chat/completions'),model=os.environ.get('IKANT_MODEL_NAME','Qwen3.5-0.8B'))
        voice=LocalVoiceInputBroker(os.environ.get('IKANT_STT_ENDPOINT'));service=LocalEmbodimentService(root,model=model,voice=voice);server,pairing=build_server(service,host=host,port=a.port)
        port=int(server.server_address[1]);url=f'http://localhost:{port}/';print(f'iKant Local Embodiment: {url}',flush=True);print(f'Pairing code: {pairing.code}',flush=True)
        if codespaces:print('Codespaces: keep the forwarded port private and enter the one-time pairing code.',flush=True)
        elif not a.no_open:webbrowser.open(url+'#pair='+pairing.code,new=2)
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        if server is not None:server.server_close()
        lock.release()
    return 0
if __name__=='__main__':raise SystemExit(main())
