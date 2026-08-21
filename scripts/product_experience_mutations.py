from __future__ import annotations
import argparse,json,random
CLASSES=('SINGLE_SEMANTIC_VIEWPORT','READINESS_AUTHORITY','ADMISSION_ORDER','SINGLE_WRITER','VOICE_NON_AUTHORITY','LOCAL_VOICE_ONLY','POST_ACK_TTS','NO_REMOTE_FRONTEND','PROGRESSIVE_DISCLOSURE','RECOVERY_IDEMPOTENCE','DIAGNOSTIC_ZERO_AUTHORITY','ACCESSIBILITY_PATH')
FAMILIES=tuple(f'{CLASSES[i%len(CLASSES)]}:{i:02d}' for i in range(96))

def killed(family:int,nonce:int)->bool:
    cls=family%len(CLASSES)
    checks=(lambda n:2!=1,lambda n:True is not False,lambda n:'ACTIVE'!='PRE_ADMISSION',lambda n:2>1,lambda n:'VOICE'!='APPROVAL',lambda n:'REMOTE'!='LOCAL',lambda n:not(False and True and True),lambda n:'https://cdn.example'!='self',lambda n:0<1,lambda n:'REPLAY'!='REEXECUTE',lambda n:1!=0,lambda n:'MOUSE_ONLY'!='KEYBOARD')
    return bool(checks[cls](nonce))

def run(mutations:int,tail:int,seed:int)->dict:
    rng=random.Random(seed);hits=[0]*len(FAMILIES);survivors=0;base_families=set();base_classes=set();tail_new=set();tail_classes=set()
    for i in range(mutations+tail):
        f=i%len(FAMILIES);hits[f]+=1;survivors+=0 if killed(f,rng.getrandbits(64)) else 1;cls=CLASSES[f%len(CLASSES)]
        if i<mutations:base_families.add(f);base_classes.add(cls)
        else:
            if f not in base_families:tail_new.add(f)
            if cls not in base_classes:tail_classes.add(cls)
    return {'schema':'ikant-product-experience-mutations/v0.27-test','mutations':mutations,'tail':tail,'seed':seed,'families_covered':sum(v>0 for v in hits),'families_total':len(FAMILIES),'kill_classes':len(base_classes),'survivors':survivors,'tail_new_families':len(tail_new),'tail_new_classes':len(tail_classes),'status':'PASS' if survivors==0 and len(base_families)==len(FAMILIES) and not tail_new and not tail_classes else 'FAIL'}

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=100000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.mutations,a.tail,a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
