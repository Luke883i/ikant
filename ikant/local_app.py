from __future__ import annotations
import argparse,os,sys,webbrowser
from pathlib import Path
from .epistemic_workspace import EpistemicWorkspaceCoordinator
from .epistemic_http import build_server
from .local_service import operational_fallback
from .managed_runtime import ManagedLocalRuntime
from .product_experience import ProductBootstrapCoordinator
from .temporal_autonomy import TemporalAutonomyRunner
_operational_fallback=operational_fallback


def _progress(event):
    phase=str(event.get('phase') or 'PREPARING');target=str(event.get('target') or 'component');size=int(event.get('bytes') or 0)
    mib=size/(1024*1024)
    print(f'[iKant runtime] {phase}: {target} {mib:.1f} MiB',file=sys.stderr,flush=True)


def main(argv=None):
    ap=argparse.ArgumentParser(prog='ikant-web');ap.add_argument('--host');ap.add_argument('--port',type=int,default=int(os.environ.get('IKANT_PORT','8765')));ap.add_argument('--no-open',action='store_true');ap.add_argument('--runtime-manifest');ap.add_argument('--component-root');ap.add_argument('--runtime-ready-timeout',type=float,default=45.0);a=ap.parse_args(argv)
    codespaces=str(os.environ.get('CODESPACES') or '').lower()=='true';host=a.host or ('0.0.0.0' if codespaces else '127.0.0.1');root=Path.cwd()
    from .store import acquire_writer_lock
    lock=acquire_writer_lock(root/'.ikant'/'local-app.writer.lock')
    server=None;service=None;temporal_runner=None
    try:
        runtime=ManagedLocalRuntime(root,manifest_path=a.runtime_manifest,component_root=a.component_root)
        product=ProductBootstrapCoordinator(root,runtime=runtime,voice_endpoint=os.environ.get('IKANT_STT_ENDPOINT'),readiness_timeout=a.runtime_ready_timeout)
        service=EpistemicWorkspaceCoordinator(product)
        server,pairing=build_server(service,host=host,port=a.port)
        service.start_async()
        temporal_runner=TemporalAutonomyRunner(root).start()
        port=int(server.server_address[1]);url=f'http://localhost:{port}/';print(f'iKant Epistemic Workspace: {url}',flush=True);print(f'Pairing code: {pairing.code}',flush=True)
        if codespaces:print('Codespaces: keep the forwarded port private and enter the one-time pairing code.',flush=True)
        elif not a.no_open:webbrowser.open(url+'#pair='+pairing.code,new=2)
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        if temporal_runner is not None:temporal_runner.stop()
        if server is not None:server.server_close()
        if service is not None:service.stop()
        lock.release()
    return 0
if __name__=='__main__':raise SystemExit(main())
