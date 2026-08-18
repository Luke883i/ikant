from __future__ import annotations
import argparse,json,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def cmd(args,timeout=45):
 p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout);return p
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--output');a=ap.parse_args();g={};t=time.monotonic()
 p=cmd([sys.executable,'-m','compileall','-q','ikant','tests','scripts']);g['compile']={'ok':p.returncode==0}
 p=cmd([sys.executable,'-m','unittest','discover','-s','tests','-q']);g['unit']={'ok':p.returncode==0,'tail':(p.stderr or p.stdout)[-600:]}
 p=cmd([sys.executable,'scripts/stress.py','--cases','1000' if a.quick else '10000','--novelty-tail','100' if a.quick else '1000']);g['static_stress']={'ok':p.returncode==0,'result':json.loads(p.stdout) if p.returncode==0 else {}}
 seeds=[883] if a.quick else [883,17,2026];runs=[]
 for seed in seeds:
  p=cmd([sys.executable,'scripts/dynamic_stress.py','--operations','1500' if a.quick else '10000','--novelty-tail','100' if a.quick else '1000','--seed',str(seed)],timeout=45);runs.append(json.loads(p.stdout) if p.returncode==0 else {'status':'FAIL','seed':seed})
 g['dynamic_stress']={'ok':all(x.get('status')=='PASS' and x.get('max_mean_activation_ceiling_fraction_sampled',1)<=.5 and x.get('max_activation_saturation_share_85_sampled',1)<=.05 for x in runs),'runs':runs}
 p=cmd([sys.executable,'scripts/tune_dynamics.py']);tu=json.loads(p.stdout) if p.returncode==0 else {};g['tuning']={'ok':tu.get('hard_invariants_passed') and tu.get('fitness',0)>=95,'result':tu}
 passed=sum(bool(x['ok']) for x in g.values());out={'schema':'ikant-release-gate/v0.1','mode':'quick' if a.quick else 'full','gates':g,'passed':passed,'total':len(g),'gate_pass_rate':100*passed/len(g),'release_candidate':passed==len(g),'elapsed_s':round(time.monotonic()-t,3),'note':'engineering coverage, not statistical or neuroscientific confidence'}
 if a.output:Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,indent=2,sort_keys=True));return 0 if out['release_candidate'] else 1
if __name__=='__main__':raise SystemExit(main())
