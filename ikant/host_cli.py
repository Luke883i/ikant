from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from . import cli as legacy
from .admission import state_dir
from .runtime import Runtime
from .chat_session import ChatController,ChatLog
from .dashboard import persist_dashboard,render_dashboard_ascii


def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))


def _runtime():return Runtime(state_dir(Path.cwd()))


def _chat_log(rt):return ChatLog(Path(rt.state_dir)/'chat'/'transcript.jsonl',runtime_session_id=rt.runtime.get('session_id'))


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if not argv:return legacy.main(argv)
    command=argv[0]
    handled={'turn','emit-surface-a','dashboard','history','shell','integrity'}
    if command not in handled:return legacy.main(argv)
    if command=='turn':
        p=argparse.ArgumentParser(prog='ikant turn');p.add_argument('--intent',required=True);p.add_argument('--limit',type=int,default=12);p.add_argument('--atoms-json');p.add_argument('--surface-b-path');p.add_argument('--host-engine');a=p.parse_args(argv[1:])
        atoms=None
        if a.atoms_json:
            data=json.loads(Path(a.atoms_json).read_text(encoding='utf-8'));atoms=data.get('atoms',[]) if isinstance(data,dict) else data
        rt=_runtime()
        try:
            controller=ChatController(rt);out=controller.begin(a.intent,engine_label=a.host_engine,limit=a.limit,atoms=atoms,docx_path=a.surface_b_path)
            emit({'schema':'ikant-host-turn/v0.4-test','cycle_id':out['cycle']['cycle_id'],'intention_node_id':out.get('intention_node_id'),'chat':out.get('chat',{}),'shell_prompt':'> iKant:','host_binding':rt.runtime.get('host',{}),'interaction_contract':out['interaction_contract'],'surface_a_contract':out['surface_a_contract'],'central_oracle':out['central_oracle'],'central_projection':out['central_projection'],'surface_b_json':out.get('surface_b_json'),'surface_b_docx':out.get('surface_b_docx'),'dashboard':out.get('chat',{}).get('dashboard')})
            return 0
        finally:rt.close()
    if command=='emit-surface-a':
        p=argparse.ArgumentParser(prog='ikant emit-surface-a');p.add_argument('--cycle-id',required=True);p.add_argument('--text',required=True);p.add_argument('--intention-node-id');a=p.parse_args(argv[1:])
        rt=_runtime()
        try:
            rec=ChatController(rt).close(a.cycle_id,a.text,intention_node_id=a.intention_node_id);emit(rec);return 0
        finally:rt.close()
    if command=='dashboard':
        p=argparse.ArgumentParser(prog='ikant dashboard');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:])
        rt=_runtime()
        try:
            dash=persist_dashboard(rt)
            if a.json:emit(dash)
            else:print(render_dashboard_ascii(dash,width=a.width))
            return 0
        finally:rt.close()
    if command in {'history','shell'}:
        p=argparse.ArgumentParser(prog=f'ikant {command}');p.add_argument('--limit',type=int,default=20);p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:])
        rt=_runtime()
        try:
            log=_chat_log(rt);log.verify()
            if command=='shell':
                dash=render_dashboard_ascii(persist_dashboard(rt),width=a.width)
                if dash.endswith('\n> iKant:'):dash=dash[:-len('\n> iKant:')]
                print(dash+'\n\n'+log.render(limit=a.limit,width=a.width))
            else:print(log.render(limit=a.limit,width=a.width))
            return 0
        finally:rt.close()
    rt=_runtime()
    try:
        core=rt.integrity();chat=_chat_log(rt).verify();out={'schema':'ikant-host-integrity/v0.4-test','ok':bool(core.get('ok')) and bool(chat.get('ok')),'runtime':core,'chat':chat};emit(out);return 0 if out['ok'] else 3
    finally:rt.close()
