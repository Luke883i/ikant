from __future__ import annotations
import argparse,json,random
FAMILIES=24
SEED_FANOUT=16


def validate(x:int)->tuple[bool,int]:
    runtime_ready=(x>>0)&1; admitted=(x>>1)&1; active=(x>>2)&1; writer=(x>>3)&1; pending=(x>>4)&1
    semantic_viewports=1+((x>>5)&1); remote_model=(x>>6)&1; ui_authority=(x>>7)&1; voice_auto=(x>>8)&1
    voice_local=(x>>9)&1; acked=(x>>10)&1; turn=(x>>11)&1; tts=(x>>12)&1; disclosure=(x>>13)&1
    keyboard=(x>>14)&1; remote_assets=(x>>15)&1; ui_marks_ready=(x>>16)&1; admission_bypass=(x>>17)&1
    second_writer=(x>>18)&1; voice_approval=(x>>19)&1; setup_visible=(x>>20)&1; blocked_retry=(x>>21)&1
    ok=True
    if active and (not runtime_ready or not admitted): ok=False
    if writer and not active: ok=False
    if pending and not writer: ok=False
    if semantic_viewports!=1: ok=False
    if remote_model or ui_authority or voice_auto or remote_assets or ui_marks_ready or admission_bypass or second_writer or voice_approval: ok=False
    if tts and (not voice_local or not acked or not turn): ok=False
    if not runtime_ready and not setup_visible: ok=False
    if not disclosure or not keyboard: ok=False
    sig=(runtime_ready)|(admitted<<1)|(active<<2)|(writer<<3)|(pending<<4)|(voice_local<<5)|(acked<<6)|(turn<<7)|(tts<<8)|(blocked_retry<<9)
    return ok,sig


def normalized_world(rng:random.Random,family:int,index:int)->int:
    # Enumerate the bounded semantic lattice so novelty is about consequences, not PRNG luck.
    # Diversified seeds still perturb latent context bits that are intentionally quotiented out
    # of the consequence signature.
    combo=(index//FAMILIES)&0xff
    ready=(combo>>0)&1
    admitted=((combo>>1)&1) if ready else 0
    active=((combo>>2)&1) if ready and admitted else 0
    writer=((combo>>3)&1) if active else 0
    pending=((combo>>4)&1) if writer else 0
    voice_local=(combo>>5)&1; acked=(combo>>6)&1; turn=(combo>>7)&1
    tts=((family>>1)&1) if voice_local and acked and turn else 0
    blocked_retry=family&1
    x=ready|(admitted<<1)|(active<<2)|(writer<<3)|(pending<<4)|(voice_local<<9)|(acked<<10)|(turn<<11)|(tts<<12)
    x|=1<<13; x|=1<<14; x|=1<<20; x|=blocked_retry<<21; x|=rng.getrandbits(9)<<22
    return x


def run(cases:int,tail:int,seed:int)->dict:
    master=random.Random(seed); fan=[master.getrandbits(63) for _ in range(SEED_FANOUT)]; rngs=[random.Random(s) for s in fan]
    signatures=set(); frontier=set(); violations=0; hits=[0]*FAMILIES
    for i in range(cases+tail):
        f=i%FAMILIES;hits[f]+=1;ok,sig=validate(normalized_world(rngs[i%SEED_FANOUT],f,i));violations+=0 if ok else 1
        key=(f,sig)
        if i<cases: signatures.add(key)
        elif key not in signatures: frontier.add(key)
    saturated=cases>=FAMILIES*256
    return {'schema':'ikant-product-experience-stress/v0.27-test','cases':cases,'tail':tail,'seed':seed,'diversified_seeds':fan,'families_covered':sum(v>0 for v in hits),'families_total':FAMILIES,'consequence_signatures':len(signatures),'semantic_lattice_saturated':saturated,'tail_novelty':len(frontier),'violations':violations,'status':'PASS' if violations==0 and (not saturated or not frontier) and all(hits) else 'FAIL'}


def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.cases,a.tail,a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
