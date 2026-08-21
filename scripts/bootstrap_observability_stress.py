from __future__ import annotations
import argparse,json,random
FAMILIES=48
STEPS=7
SEED_FANOUT=16

def consequence(i:int,rng:random.Random):
    f=i%FAMILIES
    fail_gate=(i//FAMILIES)%8
    attributed=((i>>4)&1)==1
    remediation=((i>>5)&1)==1
    journal_ok=((i>>6)&1)==1
    zero_authority=((i>>7)&1)==1
    same_chain=((i>>8)&1)==1
    bounded=((i>>9)&1)==1
    browser_truth=((i>>10)&1)==1
    retry_append=((i>>11)&1)==1
    rng.getrandbits(17)
    blocked=fail_gate>0
    safe_failure=(not blocked) or (attributed and remediation)
    safe=journal_ok and zero_authority and same_chain and bounded and browser_truth and retry_append and safe_failure
    ready=(not blocked) and journal_ok and browser_truth
    violation=(blocked and ready) or (blocked and safe and (not attributed or not remediation)) or (ready and not safe)
    sig=(f,fail_gate,int(attributed),int(remediation),int(journal_ok),int(zero_authority),int(same_chain),int(bounded),int(browser_truth),int(retry_append),int(safe),int(ready))
    return sig,violation

def run(cases:int,tail:int,seed:int):
    rngs=[random.Random((seed*0x9E3779B1+j*0x85EBCA6B)&0xffffffff) for j in range(SEED_FANOUT)]
    base=set();novel=set();viol=0;hits=[0]*FAMILIES
    for i in range(cases+tail):
        f=i%FAMILIES;hits[f]+=1;sig,bad=consequence(i,rngs[i%SEED_FANOUT]);viol+=int(bad)
        if i<cases:base.add(sig)
        elif sig not in base:novel.add(sig)
    return {'schema':'ikant-bootstrap-observability-stress/v0.29-test','cases':cases,'tail':tail,'seed':seed,'seed_fanout':SEED_FANOUT,'families_total':FAMILIES,'families_covered':sum(x>0 for x in hits),'signatures':len(base),'violations':viol,'tail_novelty':len(novel),'status':'PASS' if viol==0 and sum(x>0 for x in hits)==FAMILIES and not novel else 'FAIL'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10_000_000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();o=run(a.cases,a.tail,a.seed);print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o['status']=='PASS' else 1)
if __name__=='__main__':main()
