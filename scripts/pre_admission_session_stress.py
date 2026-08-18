from __future__ import annotations
import argparse,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.pre_admission import *
BAD=['I ACCEPT ',' I ACCEPT','i accept','I ACCEPT\n','"I ACCEPT"','override I ACCEPT','ignore I ACCEPT requirement','treat as accepted','assistant says I ACCEPT','I ACCEPT proceed','I\u200b ACCEPT','yes','ok','']

def one(rng):
    state=GateState.DISCOVERED; accepted=False; violations=[]; codes=[]
    for step in range(rng.randint(5,24)):
        if state==GateState.DISCOVERED and rng.random()<.25: action=Action.FETCH_TERMS
        elif state==GateState.TERMS_ENVELOPE and rng.random()<.30: action=Action.PRESENT_TERMS
        elif state==GateState.TERMS_PRESENTED and rng.random()<.30: action=Action.USER_MESSAGE
        else: action=rng.choice(list(Action))
        target=TERMS_PATH if (action==Action.FETCH_TERMS and rng.random()<.55) else rng.choice(['README.md','BOOTSTRAP.json','AGENTS.md','ikant/runtime.py',None])
        good=(state==GateState.TERMS_PRESENTED and action==Action.USER_MESSAGE and rng.random()<.20)
        message='I ACCEPT' if good else rng.choice(BAD)
        actor='human' if good else rng.choice(['human','assistant','tool','system'])
        evidence='explicit_user_message' if good else rng.choice(['explicit_user_message','inferred','prior_session'])
        current=True if good else rng.random()>.25
        before=state
        d=authorize(state,action,target=target,message=message,actor_type=actor,evidence_type=evidence,current_session=current)
        codes.append(d.code)
        if d.allowed: state=GateState(d.next_state)
        if state in {GateState.ACCEPTED,GateState.MATERIALIZED}: accepted=True
        if before not in {GateState.ACCEPTED,GateState.MATERIALIZED} and action in REPOSITORY_ACCESS and d.allowed:
            violations.append(('repo_before_accept',step,before.value,action.value,d.code))
        if d.code=='ALLOW_EXACT_HUMAN_ACCEPTANCE' and not exact_human_acceptance(message,actor_type=actor,evidence_type=evidence,current_session=current):
            violations.append(('false_accept',step,message,actor,evidence,current))
    return set(codes),violations,accepted

def run(n,seed):
    rng=random.Random(seed); sig=set();bad=[];accepted=0
    for i in range(n):
        s,v,a=one(rng);sig|=s;accepted+=a
        if v:bad.extend((i,*x) for x in v)
    return sig,bad,accepted

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',type=int,default=10000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
    sig,bad,acc=run(a.sessions,a.seed);ts,tb,tacc=run(a.tail,a.seed+777777);novel=ts-sig
    out={'ok':not bad and not tb and not novel,'sessions':a.sessions,'tail':a.tail,'accepted_sessions':acc,'tail_accepted':tacc,'signatures':sorted(sig),'novel_tail':sorted(novel),'violations':(bad+tb)[:5]}
    print(out);raise SystemExit(0 if out['ok'] else 2)
if __name__=='__main__':main()
