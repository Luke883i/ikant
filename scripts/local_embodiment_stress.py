from __future__ import annotations
import argparse,json,random

def consequence(mask:int)->tuple:
    bits=[bool(mask&(1<<i)) for i in range(16)]
    paired,auth,host,origin,active,pending,verbatim,visible_exact,frame_digest,model_local,voice_local,voice_input_only,tts_off,zero_ep,zero_exec,host_conforming=bits
    gate_pair=paired and auth
    gate_transport=gate_pair and host and origin
    gate_frame=gate_transport and active and pending and verbatim and visible_exact and frame_digest
    gate_model=(not active) or model_local
    gate_voice=(not voice_local) or voice_input_only
    authority=gate_frame and gate_model and gate_voice and tts_off and zero_ep and zero_exec and host_conforming
    return (gate_pair,gate_transport,gate_frame,gate_model,gate_voice,authority)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed)
    seen=set();viol=0;tail_new=0;universe=set()
    total=a.cases+a.tail
    for i in range(total):
        mask=i%65536 if i<65536 else rng.randrange(65536);universe.add(mask);sig=consequence(mask)
        bits=[bool(mask&(1<<j)) for j in range(16)]
        if sig[-1] and not all(bits[j] for j in (0,1,2,3,4,5,6,7,8,11,12,13,14,15)):viol+=1
        if i<a.cases:seen.add(sig)
        elif sig not in seen:tail_new+=1;seen.add(sig)
    out={'schema':'ikant-local-embodiment-stress/v0.20-test','status':'PASS' if viol==0 and tail_new==0 else 'FAIL','cases':a.cases,'tail':a.tail,'explicit_universe_seen':len(universe),'explicit_universe':65536,'consequence_signatures':len(seen),'violations':viol,'tail_novelty':tail_new}
    print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
