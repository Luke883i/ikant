from __future__ import annotations
import argparse,itertools,json,random

def decide(bits):
 (snap_valid,target_current,verb_supported,lease_present,lease_exact,lease_pending,grant_active,epoch_current,host_conforming,handoff_exact,cap_exact,preflight_ok,post_reval_same,page_tries_authority,cross_origin,cross_origin_granted)=bits
 allow=all((snap_valid,target_current,verb_supported,lease_present,lease_exact,lease_pending,grant_active,epoch_current,host_conforming,handoff_exact,cap_exact,preflight_ok,post_reval_same))
 if cross_origin and not cross_origin_granted: allow=False
 violations=[]
 if allow and not lease_exact:violations.append('lease scope escalation')
 if allow and not post_reval_same:violations.append('post-revalidation TOCTOU')
 return ('EXECUTE' if allow else 'BLOCK', bool(cross_origin and not cross_origin_granted), bool(page_tries_authority), tuple(violations))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed)
 universe=list(itertools.product((False,True),repeat=16));rng.shuffle(universe);seen=set();viol=[]
 def run(i):
  b=universe[i%len(universe)];sig=decide(b);seen.add(sig[:3]);viol.extend(sig[3])
 for i in range(a.cases):run(i)
 before=set(seen)
 for i in range(a.cases,a.cases+a.tail):run(i)
 out={'schema':'ikant-web-agency-stress/v0.21-test','status':'PASS' if not viol and set(seen)==before else 'FAIL','cases':a.cases,'tail':a.tail,'universe':len(universe),'covered':len(universe) if a.cases>=len(universe) else a.cases,'signatures':len(seen),'violations':len(viol),'tail_novelty':len(set(seen)-before)}
 print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
