from __future__ import annotations
import argparse,json
from runtime_epoch_campaign import run

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=2026082417);a=ap.parse_args();out=run('stress',a.cases,a.tail,a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
