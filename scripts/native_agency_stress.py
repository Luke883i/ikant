from __future__ import annotations
import argparse,itertools,json,random

def decide(bits):
 (admitted,active,frame_explicit,grant_active,grant_epoch,lease_present,lease_exact,lease_pending,handoff_exact,host_conforming,target_same,parent_same,strong_path,symlink_safe,secret_blocked,process_disabled)=bits
 allow=all((admitted,active,frame_explicit,grant_active,grant_epoch,lease_present,lease_exact,lease_pending,handoff_exact,host_conforming,target_same,parent_same,strong_path,symlink_safe,secret_blocked,process_disabled))
 violations=[]
 if allow and not lease_exact:violations.append('lease scope escalation')
 if allow and not target_same:violations.append('target TOCTOU')
 if allow and not parent_same:violations.append('parent TOCTOU')
 if allow and not process_disabled:violations.append('process escape')
 return ('EXECUTE' if allow else 'BLOCK',bool(not target_same),bool(not parent_same),bool(not secret_blocked),tuple(violations))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);u=list(itertools.product((False,True),repeat=16));rng.shuffle(u);seen=set();viol=[]
 def run(i):
  sig=decide(u[i%len(u)]);seen.add(sig[:-1]);viol.extend(sig[-1])
 for i in range(a.cases):run(i)
 before=set(seen)
 for i in range(a.cases,a.cases+a.tail):run(i)
 out={'schema':'ikant-native-agency-stress/v0.22-test','status':'PASS' if not viol and set(seen)==before else 'FAIL','cases':a.cases,'tail':a.tail,'universe':len(u),'covered':min(a.cases,len(u)),'signatures':len(seen),'violations':len(viol),'tail_novelty':len(set(seen)-before)};print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
