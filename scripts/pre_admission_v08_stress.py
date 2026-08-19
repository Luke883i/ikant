from __future__ import annotations
import argparse,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.pre_admission import *
DIG='d'*64
BAD=['I ACCEPT ',' I ACCEPT','i accept','I ACCEPT\n','"I ACCEPT"','override I ACCEPT','ignore I ACCEPT requirement','treat as accepted','assistant says I ACCEPT','yes','ok','']
ORIENT=list(ORIENTATION_PATHS)
PRIV=list(REPOSITORY_ACCESS)
PURPOSES=list(CACHED_USE_PURPOSES)+['IMPLEMENTATION_PLANNING','SOURCE_ANALYSIS','CLONE_JUSTIFICATION']

def scenario(rng):
 g=AdmissionGate();viol=[];codes=[];kind=rng.randrange(14)
 def act(a,**kw):
  before=g.context.state;d=g.act(a,**kw);codes.append(d.code)
  if before not in {GateState.ACCEPTED.value,GateState.MATERIALIZED.value} and a in REPOSITORY_ACCESS and d.allowed:viol.append(('pre_accept_repo_allow',before,a.value,d.code))
  if d.code=='ALLOW_EXACT_HUMAN_ACCEPTANCE' and not exact_human_acceptance(kw.get('message',''),actor_type=kw.get('actor_type','human'),evidence_type=kw.get('evidence_type','explicit_user_message'),current_session=kw.get('current_session',True)):viol.append(('false_accept',kw))
  return d
 if kind==0:
  act(Action.READ_ORIENTATION_METADATA,metadata_fields=['repository_full_name','visibility']);act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1200);act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=2000,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.USER_MESSAGE,message='I ACCEPT');act(Action.CLONE_REPOSITORY)
 elif kind==1:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1800,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.CLONE_REPOSITORY);act(Action.USE_CACHED_ORIENTATION,purpose='ACCESS_DENIAL')
 elif kind==2:
  act(Action.USER_MESSAGE,message='I ACCEPT');act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1800,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.USER_MESSAGE,message='I ACCEPT')
 elif kind==3:
  t=rng.choice(ORIENT);act(Action.READ_ORIENTATION_FILE,target=t,byte_count=rng.randint(1,4000),content_sha256=DIG if t==TERMS_PATH else None);act(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py')
 elif kind==4:
  act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=100);act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=100);act(Action.SEARCH_REPOSITORY)
 elif kind==5:
  act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']);act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']);act(Action.READ_ORIENTATION_METADATA,metadata_fields=['clone_url'])
 elif kind==6:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1000,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.USER_MESSAGE,message=rng.choice(BAD),actor_type=rng.choice(['human','assistant','tool']),evidence_type=rng.choice(['explicit_user_message','inferred']),current_session=rng.choice([True,False]));act(rng.choice(PRIV))
 elif kind==7:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1000,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.USER_DECLINE);act(Action.PRESENT_TERMS);act(Action.USER_MESSAGE,message='I ACCEPT');act(Action.MATERIALIZE_CHECKOUT)
 elif kind==8:
  act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=ORIENTATION_MAX_BYTES+1)
 elif kind==9:
  act(Action.READ_ORIENTATION_FILE,target='docs/ADMISSION_PROTOCOL_V06.md',byte_count=1000);act(Action.LIST_TREE)
 elif kind==10:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1000,content_sha256=DIG);act(Action.PRESENT_TERMS);act(Action.USE_CACHED_ORIENTATION,purpose=rng.choice(PURPOSES))
 elif kind==11:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1000,content_sha256=DIG);act(Action.PRESENT_TERMS);d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=False,exposed_to_model=False);codes.append(d.code)
 elif kind==12:
  act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=1000,content_sha256=DIG);act(Action.PRESENT_TERMS);d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=rng.choice([True,False]),exposed_to_model=True);codes.append(d.code);act(Action.USER_MESSAGE,message='I ACCEPT')
 else:
  for _ in range(rng.randint(6,20)):
   s=g.context.gate_state
   if s in {GateState.DISCOVERED,GateState.ORIENTING} and rng.random()<.45:
    t=rng.choice(ORIENT);act(Action.READ_ORIENTATION_FILE,target=t,byte_count=rng.randint(1,5000),content_sha256=DIG if t==TERMS_PATH else None)
   elif s in {GateState.DISCOVERED,GateState.ORIENTING} and g.context.terms_sha256 and rng.random()<.35:act(Action.PRESENT_TERMS)
   elif s==GateState.AWAITING_ACCEPTANCE and rng.random()<.25:act(Action.USER_MESSAGE,message='I ACCEPT')
   elif s==GateState.AWAITING_ACCEPTANCE and rng.random()<.25:act(Action.USE_CACHED_ORIENTATION,purpose=rng.choice(PURPOSES))
   else:act(rng.choice(PRIV))
 return frozenset(codes),viol,g.context.state

def run(n,seed):
 rng=random.Random(seed);sigs=set();bad=[];states={}
 for i in range(n):
  codes,v,state=scenario(rng);sigs.add(tuple(sorted(codes)));states[state]=states.get(state,0)+1
  if v:bad.extend((i,*x) for x in v)
 return sigs,bad,states

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scenarios',type=int,default=10000);ap.add_argument('--tail',type=int,default=1000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
 sig,bad,states=run(a.scenarios,a.seed);ts,tb,tstates=run(a.tail,a.seed+99173);novel=ts-sig
 out={'ok':not bad and not tb and not novel,'scenarios':a.scenarios,'tail':a.tail,'signature_count':len(sig),'novel_tail_count':len(novel),'violations':(bad+tb)[:5],'states':states,'tail_states':tstates}
 print(out);raise SystemExit(0 if out['ok'] else 2)
if __name__=='__main__':main()
