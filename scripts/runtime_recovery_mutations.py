from __future__ import annotations
import argparse,json
from runtime_recovery_falsify import run

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=5106034144745002672);a=ap.parse_args();out=run('mutations',a.mutations,a.tail,a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
