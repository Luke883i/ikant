from __future__ import annotations
import argparse,itertools,json,random


def decide(bits):
    (snapshot_valid,target_current,verb_safe,bound_lease,lease_pending,grant_active,epoch_current,host_conforming,handoff_exact,cap_exact,preflight_ok,post_revalidation_same,browser_secure,network_guarded,page_tries_authority,cross_origin)=bits
    allow=all((snapshot_valid,target_current,verb_safe,bound_lease,lease_pending,grant_active,epoch_current,host_conforming,handoff_exact,cap_exact,preflight_ok,post_revalidation_same,browser_secure,network_guarded))
    violations=[]
    if allow and not bound_lease:violations.append('unbound lease')
    if allow and not post_revalidation_same:violations.append('post-revalidation TOCTOU')
    if allow and not browser_secure:violations.append('browser sandbox bypass')
    if allow and not network_guarded:violations.append('network side channel')
    return ('EXECUTE' if allow else 'BLOCK',bool(page_tries_authority),bool(cross_origin),tuple(violations))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed)
    universe=list(itertools.product((False,True),repeat=16));rng.shuffle(universe);seen=set();viol=[]
    def run(i):
        sig=decide(universe[i%len(universe)]);seen.add(sig[:3]);viol.extend(sig[3])
    for i in range(a.cases):run(i)
    before=set(seen)
    for i in range(a.cases,a.cases+a.tail):run(i)
    out={'schema':'ikant-web-agency-stress/v0.21-test','status':'PASS' if not viol and set(seen)==before else 'FAIL','cases':a.cases,'tail':a.tail,'universe':len(universe),'covered':min(a.cases,len(universe)),'signatures':len(seen),'violations':len(viol),'tail_novelty':len(set(seen)-before)}
    print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
