from __future__ import annotations
import argparse,json,random

UNIVERSE=1<<16

def evaluate(x:int)->tuple:
    b=[bool(x&(1<<i)) for i in range(16)]
    names=('accepted','channel','frame','approve','entitlements','no_wildcard','no_traversal','grant_current','use_available','handoff_ready','session','binding','cap_match','not_revoked','not_expired','host_conforming')
    s=dict(zip(names,b))
    gates=[('ADMISSION_BLOCK','accepted'),('CHANNEL_BLOCK','channel'),('FRAME_BLOCK','frame'),('DECISION_BLOCK','approve'),('SCOPE_BLOCK','entitlements'),('WILDCARD_BLOCK','no_wildcard'),('TRAVERSAL_BLOCK','no_traversal'),('GRANT_STALE','grant_current'),('USE_EXHAUSTED','use_available'),('HANDOFF_BLOCK','handoff_ready'),('SESSION_BLOCK','session'),('BINDING_BLOCK','binding'),('CAPABILITY_BLOCK','cap_match'),('REVOKED','not_revoked'),('EXPIRED','not_expired'),('HOST_BLOCK','host_conforming')]
    for status,key in gates:
        if not s[key]:return (status,False,False,0.0,0.0)
    return ('LEASE_VALID',True,True,0.0,0.0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
    rnd=random.Random(a.seed);step=rnd.randrange(1,UNIVERSE,2);offset=rnd.randrange(UNIVERSE);seen_cfg=set();sigs=set();viol=0
    for i in range(a.cases):
        x=(offset+i*step)%UNIVERSE;seen_cfg.add(x);r=evaluate(x);sigs.add(r)
        if r[1] and (x != UNIVERSE-1 or r[3]!=0.0 or r[4]!=0.0):viol+=1
    tail_new=0
    for i in range(a.tail):
        x=(offset+(a.cases+i)*step)%UNIVERSE;r=evaluate(x)
        if r not in sigs:tail_new+=1;sigs.add(r)
    saturated=len(seen_cfg)==UNIVERSE and tail_new==0 and viol==0
    out={'schema':'ikant-agency-kernel-stress/v0.19-test','status':'PASS' if saturated else 'FAIL','seed':a.seed,'cases':a.cases,'tail':a.tail,'explicit_universe':UNIVERSE,'explicit_coverage':len(seen_cfg),'consequence_signatures':len(sigs),'tail_new_signatures':tail_new,'violations':viol,'saturated':saturated}
    print(json.dumps(out,sort_keys=True));return 0 if saturated else 1
if __name__=='__main__':raise SystemExit(main())
