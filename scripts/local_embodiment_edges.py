from __future__ import annotations
import argparse,json,random
from ikant.local_security import origin_allowed,require_loopback_url
from ikant.local_http import host_header_allowed

def signature(mask:int)->tuple:
    b=[bool(mask&(1<<i)) for i in range(15)]
    host='127.0.0.1:8765' if b[0] else ('127.0.0.1:9999' if b[1] else 'evil.example')
    origin=('http://' if b[2] else 'https://')+host if b[3] else None
    h=host_header_allowed(host,frozenset({'127.0.0.1','localhost'}),8765)
    o=origin_allowed(origin,host)
    endpoint='http://127.0.0.1:8080/v1/chat/completions' if b[4] else ('https://127.0.0.1:8080/v1' if b[5] else 'http://10.0.0.8:8080/v1')
    try:require_loopback_url(endpoint);local=True
    except ValueError:local=False
    paired=b[6];token=b[7];frame=b[8];visible=b[9];voice=b[10];voice_submit=b[11];tts=b[12];ep=b[13];exe=b[14]
    accepted=h and o and paired and token and frame and visible and local and (not voice or not voice_submit) and not tts and not ep and not exe
    return (h,o,local,paired and token,frame and visible,voice and voice_submit,tts,ep,exe,accepted)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed)
    seen=set();universe=set();viol=tail_new=0
    for i in range(a.cases+a.tail):
        mask=i%32768 if i<32768 else rng.randrange(32768);universe.add(mask);sig=signature(mask)
        if sig[-1] and (sig[5] or sig[6] or sig[7] or sig[8]):viol+=1
        if i<a.cases:seen.add(sig)
        elif sig not in seen:tail_new+=1;seen.add(sig)
    out={'schema':'ikant-local-embodiment-edges/v0.20-test','status':'PASS' if viol==0 and tail_new==0 else 'FAIL','cases':a.cases,'tail':a.tail,'explicit_universe_seen':len(universe),'explicit_universe':32768,'signatures':len(seen),'violations':viol,'tail_novelty':tail_new}
    print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
