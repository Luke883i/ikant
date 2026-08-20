from __future__ import annotations
import argparse,hashlib,json,random
from ikant.local_security import PairingSession,LocalSecurityError,origin_allowed,require_loopback_url
from ikant.local_http import host_header_allowed
from ikant.web_frame import wrap_prepared_frame,build_web_ack,validate_web_ack

def sha(x):return hashlib.sha256(x.encode()).hexdigest()
def base_frame():
    text='exact dashboard frame';return wrap_prepared_frame({'text':text,'receipt':{'schema':'ikant-dashboard-frame/v0.11-test','runtime_session_id':'s','epoch':1,'frame_seq':1,'kind':'TURN','cycle_id':'c','frame_sha256':sha(text),'release_after_frame':False},'delivery_state':'FRAME_PENDING','acknowledged':False})

def killed(f:int)->bool:
    k=f%60
    if k<20:
        frame=base_frame();ack=build_web_ack(frame,frame['text']);fields=['schema','runtime_session_id','epoch','frame_seq','frame_sha256','visible_text','visible_text_sha256','epistemic_authority','execution_authority'];field=fields[k%len(fields)]
        if field=='schema':ack[field]='bad'
        elif field in {'epoch','frame_seq'}:ack[field]=999
        elif field in {'epistemic_authority','execution_authority'}:ack[field]=1.0
        else:ack[field]=str(ack[field])+'x'
        return not validate_web_ack(frame,ack)[0]
    if k<30:
        candidates=[None,'','https://127.0.0.1:8765','http://127.0.0.1:9999','https://evil:8765','file://127.0.0.1:8765','http://localhost:8765@evil','http://evil:8765','ws://127.0.0.1:8765','http://[::1]:9999']
        return not origin_allowed(candidates[k-20],'127.0.0.1:8765')
    if k<40:
        urls=['https://127.0.0.1:8080/v1','http://10.0.0.1:8080/v1','file://127.0.0.1/x','http://user@127.0.0.1/x','http://127.0.0.1/x#frag','https://localhost/x','ftp://localhost/x','http://example.com/x','http://0.0.0.0/x','']
        try:require_loopback_url(urls[k-30]);return False
        except ValueError:return True
    if k<50:
        if k==40:return not host_header_allowed('127.0.0.1:9999',frozenset({'127.0.0.1'}),8765)
        if k==41:return not host_header_allowed('evil:8765',frozenset({'127.0.0.1'}),8765)
        pair=PairingSession.create(max_attempts=2);code=pair.code
        if k in {42,43}:
            try:pair.pair('wrong');return True
            except LocalSecurityError:return True
        token=pair.pair(code)
        if k==44:
            try:pair.pair(code);return False
            except LocalSecurityError:return True
        if k==45:return not pair.authenticate('Bearer wrong')
        if k==46:return not pair.authenticate(token)
        if k==47:return not pair.authenticate(None)
        if k==48:return pair.authenticate('Bearer '+token)
        return pair.public_status()['paired'] is True
    p={'text':'exact','receipt':{'schema':'ikant-dashboard-frame/v0.11-test','runtime_session_id':'s','epoch':1,'frame_seq':1,'kind':'T','cycle_id':None,'frame_sha256':sha('exact'),'release_after_frame':False},'delivery_state':'FRAME_PENDING','acknowledged':False}
    if k==50:p['text']='changed'
    elif k==51:p['receipt']['frame_sha256']='0'*64
    elif k==52:p['text']=''
    elif k==53:p['receipt'].pop('frame_sha256')
    elif k==54:p['receipt']['frame_sha256']=sha('other')
    elif k==55:p['text']='exact\x00'
    elif k==56:p['text']=' exact'
    elif k==57:p['text']='exact '
    elif k==58:p['text']='EXACT'
    else:p['text']='exact\n'
    try:wrap_prepared_frame(p);return False
    except ValueError:return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);families=set();survivors=0;tail_new=0
    for i in range(a.mutations+a.tail):
        fam=i%60 if i<60 else rng.randrange(60);new=fam not in families
        if i>=a.mutations and new:tail_new+=1
        families.add(fam)
        if not killed(fam):survivors+=1
    out={'schema':'ikant-local-embodiment-mutations/v0.20-test','status':'PASS' if survivors==0 and tail_new==0 and len(families)==60 else 'FAIL','mutations':a.mutations,'tail':a.tail,'families':len(families),'survivors':survivors,'tail_new_families':tail_new}
    print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
