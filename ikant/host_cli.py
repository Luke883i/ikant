from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from . import cli as legacy
from .admission import state_dir
from .runtime import Runtime
from .host import conforming_turn,emit_conforming_surface_a

def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if not argv:return legacy.main(argv)
    command=argv[0]
    if command not in {'turn','emit-surface-a'}:
        return legacy.main(argv)
    if command=='turn':
        p=argparse.ArgumentParser(prog='ikant turn');p.add_argument('--intent',required=True);p.add_argument('--limit',type=int,default=12);p.add_argument('--atoms-json');p.add_argument('--surface-b-path');p.add_argument('--host-engine');a=p.parse_args(argv[1:])
        atoms=None
        if a.atoms_json:
            data=json.loads(Path(a.atoms_json).read_text(encoding='utf-8'));atoms=data.get('atoms',[]) if isinstance(data,dict) else data
        rt=Runtime(state_dir(Path.cwd()))
        try:
            out=conforming_turn(rt,a.intent,engine_label=a.host_engine,limit=a.limit,atoms=atoms,docx_path=a.surface_b_path)
            emit({'schema':'ikant-host-turn/v0.3-test','cycle_id':out['cycle']['cycle_id'],'intention_node_id':out.get('intention_node_id'),'host_binding':rt.runtime.get('host',{}),'interaction_contract':out['interaction_contract'],'surface_a_contract':out['surface_a_contract'],'central_oracle':out['central_oracle'],'central_projection':out['central_projection'],'surface_b_json':out.get('surface_b_json'),'surface_b_docx':out.get('surface_b_docx')})
            return 0
        finally:rt.close()
    p=argparse.ArgumentParser(prog='ikant emit-surface-a');p.add_argument('--cycle-id',required=True);p.add_argument('--text',required=True);p.add_argument('--intention-node-id');a=p.parse_args(argv[1:])
    rt=Runtime(state_dir(Path.cwd()))
    try:emit(emit_conforming_surface_a(rt,a.cycle_id,a.text,intention_node_id=a.intention_node_id));return 0
    finally:rt.close()
