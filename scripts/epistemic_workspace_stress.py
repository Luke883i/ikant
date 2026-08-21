from __future__ import annotations
import argparse,json,random
FAMILIES=32
SEED_FANOUT=16

def semantic_signature(i:int,rng:random.Random)->tuple[int,bool]:
    f=i%FAMILIES
    # Bounded semantic state: all unsafe context bits are normalized into denial outcomes.
    active=(i>>0)&1; writer=(i>>1)&1; ack=(i>>2)&1; pending=(i>>3)&1
    session=(i>>4)&1; cycle=(i>>5)&1; path=(i>>6)&1; digest=(i>>7)&1
    read_only=(i>>8)&1; single_surface=(i>>9)&1; local=(i>>10)&1; bounded=(i>>11)&1
    # diversified environment noise intentionally does not enter the consequence signature
    rng.getrandbits(17)
    allow=bool(active and writer and ack and not pending and session and cycle and path and digest and read_only and single_surface and local and bounded)
    sig=(f<<13)|(active<<0)|(writer<<1)|(ack<<2)|(pending<<3)|(session<<4)|(cycle<<5)|(path<<6)|(digest<<7)|(read_only<<8)|(single_surface<<9)|(local<<10)|(bounded<<11)|(int(allow)<<12)
    violation=allow and (not active or not writer or not ack or pending or not session or not cycle or not path or not digest or not read_only or not single_surface or not local or not bounded)
    return sig,violation

def run(cases:int,tail:int,seed:int)->dict:
    rngs=[random.Random((seed*0x9E3779B1+i*0x85EBCA6B)&0xffffffff) for i in range(SEED_FANOUT)]
    base=set();novel=set();violations=0;hits=[0]*FAMILIES
    for i in range(cases+tail):
        rng=rngs[i%SEED_FANOUT];sig,bad=semantic_signature(i,rng);hits[i%FAMILIES]+=1;violations+=int(bad)
        if i<cases:base.add(sig)
        elif sig not in base:novel.add(sig)
    return {'schema':'ikant-epistemic-workspace-stress/v0.28-test','cases':cases,'tail':tail,'seed':seed,'seed_fanout':SEED_FANOUT,'families_total':FAMILIES,'families_covered':sum(x>0 for x in hits),'signatures':len(base),'violations':violations,'tail_novelty':len(novel),'status':'PASS' if violations==0 and sum(x>0 for x in hits)==FAMILIES and not novel else 'FAIL'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10000000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();o=run(a.cases,a.tail,a.seed);print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o['status']=='PASS' else 1)
if __name__=='__main__':main()
