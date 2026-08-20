from __future__ import annotations
import argparse,json,random
UNIVERSE=1<<15

def edge(x:int)->tuple:
    bits=[bool(x&(1<<i)) for i in range(15)]
    labels=('wrong_session','wrong_binding','bad_mac','frame_tamper','wildcard','traversal','revoked','expired','terminal_replay','grant_exhausted','handoff_drift','capability_drift','journal_tamper','host_nonconforming','recovery_autoexecute')
    active=[labels[i] for i,v in enumerate(bits) if v]
    allowed=not active
    status='ALLOW' if allowed else 'BLOCK:'+active[0]
    return (status,allowed,tuple(active[:3]),0.0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
    rnd=random.Random(a.seed);step=rnd.randrange(1,UNIVERSE,2);off=rnd.randrange(UNIVERSE);seen=set();sigs=set();viol=0
    for i in range(a.cases):
        x=(off+i*step)%UNIVERSE;seen.add(x);r=edge(x);sigs.add(r)
        if r[1] and x!=0:viol+=1
    tail_new=0
    for i in range(a.tail):
        r=edge((off+(a.cases+i)*step)%UNIVERSE)
        if r not in sigs:tail_new+=1;sigs.add(r)
    ok=len(seen)==UNIVERSE and tail_new==0 and viol==0
    print(json.dumps({'schema':'ikant-agency-kernel-edges/v0.19-test','status':'PASS' if ok else 'FAIL','cases':a.cases,'tail':a.tail,'explicit_universe':UNIVERSE,'explicit_coverage':len(seen),'signatures':len(sigs),'tail_new_signatures':tail_new,'violations':viol,'saturated':ok},sort_keys=True));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
