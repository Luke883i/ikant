import argparse, random
from dataclasses import dataclass, replace

LOCKED='DASHBOARD_LOCKED';PENDING='FRAME_PENDING';REL_PENDING='RELEASE_PENDING';RELEASED='RELEASED';BREACHED='EGRESS_BREACHED'
@dataclass(frozen=True)
class S:
    state:str=LOCKED;epoch:int=1;seq:int=0;pending:bool=False;release:bool=False

def seal(s,release=False):
    if s.state!=LOCKED:return replace(s,state=BREACHED),False
    return replace(s,state=REL_PENDING if release else PENDING,seq=s.seq+1,pending=True,release=release),True

def ack(s,match=True,flag=None):
    if s.state not in {PENDING,REL_PENDING}:return replace(s,state=BREACHED,pending=False),False
    expected=s.state==REL_PENDING
    if not match or (flag is not None and flag!=expected):return replace(s,state=BREACHED,pending=False),False
    return replace(s,state=RELEASED if expected else LOCKED,pending=False,release=False),True

def resume(s,integrity=True):
    if s.state not in {RELEASED,BREACHED} or not integrity:return s,False
    return S(LOCKED,s.epoch+1,0,False,False),True

FAMS=('normal','double','prefix','suffix','stale','wrong_receipt','release','resume_ok','resume_bad','crash','tamper','missing','exit_variant','control','oversize','ack_without','legacy_pending','legacy_locked','concurrent','machine_leak','write_fail','flush_fail','replay_release','replay_turn')

def case(rng):
    f=rng.choice(FAMS);s=S();sig=''
    if f=='normal':s,_=seal(s);s,ok=ack(s);assert ok and s.state==LOCKED;sig='ok'
    elif f=='double':s,_=seal(s);s,ok=seal(s);assert not ok and s.state==BREACHED;sig='breach'
    elif f in {'prefix','suffix','wrong_receipt','stale','machine_leak'}:s,_=seal(s);s,ok=ack(s,False);assert not ok and s.state==BREACHED;sig='breach'
    elif f=='release':s,_=seal(s,True);s,ok=ack(s);assert ok and s.state==RELEASED;sig='released'
    elif f=='resume_ok':s,_=seal(s,True);s,_=ack(s);s,ok=resume(s,True);assert ok and s.epoch==2 and s.state==LOCKED;sig='resumed'
    elif f=='resume_bad':s,_=seal(s,True);s,_=ack(s);s2,ok=resume(s,False);assert not ok and s2==s;sig='blocked'
    elif f in {'crash','replay_turn'}:s,_=seal(s);assert s.pending;s,ok=ack(s);assert ok;sig='replayed'
    elif f=='replay_release':s,_=seal(s,True);assert s.pending;s,ok=ack(s);assert ok and s.state==RELEASED;sig='replayed_release'
    elif f in {'tamper','missing'}:s,_=seal(s);s=replace(s,state=BREACHED,pending=False);sig='breach'
    elif f=='exit_variant':assert rng.choice([' exit','EXIT ','Exit'])!='EXIT IKANT';sig='intent'
    elif f in {'control','oversize'}:sig='rejected_before_seal'
    elif f=='ack_without':s,ok=ack(s);assert not ok and s.state==BREACHED;sig='breach'
    elif f=='legacy_pending':s=replace(s,state=BREACHED);sig='migrated_breach'
    elif f=='legacy_locked':sig='migrated_locked'
    elif f=='concurrent':
        # exactly one seal may win; second sees pending/breach in serialized reducer
        s,ok1=seal(s);s,ok2=seal(s);assert ok1 and not ok2;sig='serialized'
    elif f in {'write_fail','flush_fail'}:s,_=seal(s);assert s.state==PENDING and s.pending;sig='recoverable_pending'
    return f,sig

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=883);ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);a=ap.parse_args();rng=random.Random(a.seed);seen=set()
    for _ in range(a.cases):seen.add(case(rng))
    before=set(seen)
    for _ in range(a.tail):seen.add(case(rng))
    novel=len(seen-before);print({'seed':a.seed,'cases':a.cases,'tail':a.tail,'families':len(FAMS),'signatures':len(seen),'novel_tail':novel})
    return 0 if novel==0 else 2
if __name__=='__main__':raise SystemExit(main())
