from __future__ import annotations
import argparse,json,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def cmd(args,timeout=60): return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
def run_many(commands,timeout=60):
    with ThreadPoolExecutor(max_workers=len(commands)) as ex:
        fut=[ex.submit(cmd,c,timeout) for c in commands]
        return [parsed(f.result()) for f in fut]

def parsed(p):
    if p.returncode:return {'status':'FAIL','stderr':p.stderr[-800:],'stdout':p.stdout[-800:]}
    try:return json.loads(p.stdout)
    except json.JSONDecodeError:return {'status':'PASS','stdout':p.stdout[-800:]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--receipts-dir');ap.add_argument('--output');a=ap.parse_args();
    if not a.quick:
        if not a.receipts_dir:
            out={'schema':'ikant-release-gate/v0.2','status':'RECEIPTS_REQUIRED','release_candidate':False,'note':'Full validation is fault-isolated. Run the documented matrix jobs separately, then call --receipts-dir.'};print(json.dumps(out,indent=2,sort_keys=True));return 2
        argv=[sys.executable,'scripts/aggregate_validation.py','--dir',a.receipts_dir]
        if a.output:argv += ['--output',a.output]
        p=subprocess.run(argv,cwd=ROOT,text=True);return p.returncode
    g={};t=time.monotonic()
    p=cmd([sys.executable,'-m','compileall','-q','ikant','tests','scripts']);g['compile']={'ok':p.returncode==0}
    p=cmd([sys.executable,'-W','error::ResourceWarning','-m','unittest','discover','-s','tests','-q']);g['unit']={'ok':p.returncode==0,'tail':(p.stderr or p.stdout)[-700:]}
    p=cmd([sys.executable,'scripts/stress.py','--cases','1000','--novelty-tail','100']);r=parsed(p);g['static_stress']={'ok':r.get('status')=='PASS','result':r}
    seeds=[883]
    dynamic_cmds=[[sys.executable,'scripts/dynamic_stress.py','--operations','1200','--novelty-tail','100','--seed',str(seed)] for seed in seeds]
    runs=run_many(dynamic_cmds,timeout=90)
    g['dynamic_stress']={'ok':all(x.get('status')=='PASS' and x.get('max_mean_activation_ceiling_fraction_sampled',1)<=.5 and x.get('max_activation_saturation_share_85_sampled',1)<=.05 for x in runs),'runs':runs}
    crc_cmds=[[sys.executable,'scripts/crc_stress.py','--cases','750','--seed',str(seed)] for seed in seeds]
    crc_runs=run_many(crc_cmds,timeout=90)
    g['crc_stress']={'ok':all(x.get('status')=='PASS' for x in crc_runs),'runs':crc_runs}
    p=cmd([sys.executable,'scripts/surface_a_stress.py','--cases','1500','--seed','883']);r=parsed(p);g['surface_a_stress']={'ok':r.get('status')=='PASS','result':r}
    p=cmd([sys.executable,'scripts/edge_stress.py','--cases','1200','--seed','1']);r=parsed(p);g['edge_stress']={'ok':r.get('status')=='PASS','result':r}
    p=cmd([sys.executable,'scripts/central_stress.py','--cases','1200','--seed','1']);r=parsed(p);g['central_stress']={'ok':r.get('status')=='PASS' and r.get('all_modes_reached'),'result':r}
    p=cmd([sys.executable,'scripts/dialogue_smoke.py']);r=parsed(p);g['dialogue_smoke']={'ok':r.get('status')=='PASS' and r.get('all_responses_zero_evidence') and r.get('all_surface_b'),'result':r}
    cog_cmds=[[sys.executable,'scripts/cognitive_stress.py','--turns','120','--novelty-tail','30','--seed',str(seed)] for seed in seeds]
    cog=run_many(cog_cmds,timeout=90)
    g['cognitive_stress']={'ok':all(x.get('status')=='PASS' and x.get('max_mean_activation_ceiling_fraction',1)<.70 and x.get('sentinel_evidence_unchanged') for x in cog),'runs':cog}
    p=cmd([sys.executable,'scripts/tune_dynamics.py']);tu=parsed(p);g['tuning']={'ok':bool(tu.get('hard_invariants_passed')) and bool(tu.get('near_best')),'result':tu}
    passed=sum(bool(x['ok']) for x in g.values());out={'schema':'ikant-release-gate/v0.2','mode':'quick','gates':g,'passed':passed,'total':len(g),'gate_pass_rate':round(100*passed/len(g),3),'release_candidate':passed==len(g),'elapsed_s':round(time.monotonic()-t,3),'note':'engineering coverage and functional CRC validation; not statistical neuroscientific confidence or evidence of consciousness'}
    if a.output:Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if out['release_candidate'] else 1
if __name__=='__main__':raise SystemExit(main())
