from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.causal_ledger import begin_turn, causal_projection, reconcile_restart
from ikant.runtime import Runtime
from tests.helpers import active_runtime

def child(base:Path)->None:
    rt=active_runtime(base,durable=True);begin_turn(rt);rt.runtime['s18_process_crash_probe']='uncommitted';rt._write_runtime();os._exit(33)

def parent()->int:
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);p=subprocess.run([sys.executable,__file__,'--child',str(base)],cwd=ROOT)
        if p.returncode!=33:raise SystemExit(f'child did not crash at injected boundary: {p.returncode}')
        sd=base/'repo'/'.ikant';rt=Runtime(sd);result=reconcile_restart(rt);rt.close();reopened=Runtime(sd);projection=causal_projection(reopened);ok=result.get('state')=='ROLLED_BACK_PREPARE' and 's18_process_crash_probe' not in reopened.runtime and projection.get('last_terminal',{}).get('event')=='TURN_ABORTED';reopened.close()
        print(json.dumps({'schema':'ikant-s18-process-crash-oracle/v1-test','status':'PASS' if ok else 'FAIL','child_exit':33,'rollback_state':result.get('state'),'uncommitted_runtime_effect_survived':not ok,'model_reexecuted':False,'planner_reexecuted':False,'material_driver_reexecuted':False},sort_keys=True));return 0 if ok else 1
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--child');a=ap.parse_args();child(Path(a.child)) if a.child else sys.exit(parent())
