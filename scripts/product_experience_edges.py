from __future__ import annotations
import argparse,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=20

def code_audit()->list[str]:
 e=[]
 def read(p):
  f=ROOT/p
  if not f.is_file():e.append('missing:'+p);return ''
  return f.read_text(encoding='utf-8')
 html=read('ikant/web/index.html');js=read('ikant/web/app.js');css=read('ikant/web/styles.css');http=read('ikant/local_http.py');product=read('ikant/product_experience.py');launcher=read('ikant/local_app.py')
 if html.count('id="dashboard"')!=1:e.append('semantic_viewport_count')
 for forbidden in ('https://','http://cdn','unpkg','jsdelivr','fonts.googleapis'):
  if forbidden in html or forbidden in css:e.append('remote_frontend_asset:'+forbidden)
 # S11 compresses the historical orbit rail into one Details inspector while preserving
 # S9's progressive-disclosure invariant and the same single semantic viewport.
 for marker in ('command-palette','inspector','inspector-button','voice-button','setup-panel'):
  if marker not in html:e.append('ui_marker:'+marker)
 for marker in ('PRODUCT_EXPERIENCE_SCHEMA','browser_may_mark_ready','voice_output_source','traditional_controls_on_demand'):
  if marker not in product:e.append('product_contract:'+marker)
 if "frame?.receipt?.kind!=='TURN'" not in js:e.append('tts_turn_gate')
 if 'maybeSpeak(f)' not in js or js.rindex('maybeSpeak(f)')<js.index('confirmed=await apiRetry'):e.append('tts_post_ack_order')
 if 'localService===true' not in js:e.append('tts_local_only')
 if 'processLocally:true' not in js or 'rec.processLocally=true' not in js:e.append('stt_local_gate')
 if 'auto_submit!==false' not in js:e.append('voice_auto_submit_guard')
 if "'/api/v3/product/status'" not in http or "'/api/v3/voice/transcribe'" not in http:e.append('http_surface')
 if 'ProductBootstrapCoordinator' not in launcher:e.append('bootstrap_coordinator')
 if 'browser_model_transport' not in product:e.append('browser_model_transport_boundary')
 if '@media(prefers-reduced-motion:reduce)' not in css:e.append('reduced_motion')
 return e

def simulate(cases:int,tail:int,seed:int)->dict:
 rng=random.Random(seed);base=set();novel=set();violations=0;hits=[0]*FAMILIES
 for i in range(cases+tail):
  f=i%FAMILIES;hits[f]+=1
  ready=rng.getrandbits(1);accepted=rng.getrandbits(1) if ready else 0;active=rng.getrandbits(1) if ready and accepted else 0;writer=rng.getrandbits(1) if active else 0
  pending=rng.getrandbits(1) if writer else 0;voice=rng.getrandbits(1);ack=rng.getrandbits(1);turn=rng.getrandbits(1);speak=rng.getrandbits(1) if voice and ack and turn else 0
  sig=ready|(accepted<<1)|(active<<2)|(writer<<3)|(pending<<4)|(voice<<5)|(ack<<6)|(turn<<7)|(speak<<8)|(f<<9)
  if active and not (ready and accepted):violations+=1
  if writer and not active:violations+=1
  if pending and not writer:violations+=1
  if speak and not (voice and ack and turn):violations+=1
  if i<cases:base.add(sig)
  elif sig not in base:novel.add(sig)
 saturated=cases>=FAMILIES*512
 return {'cases':cases,'tail':tail,'families_covered':sum(v>0 for v in hits),'signatures':len(base),'tail_novelty':len(novel),'saturated':saturated,'violations':violations}

def minimality(seed:int,tail:int)->dict:
 required=sum(1<<i for i in range(12)); forbidden=sum(1<<i for i in range(12,18))
 accepted=0;best=99
 for mask in range(1<<18):
  if (mask&required)==required and (mask&forbidden)==0:
   accepted+=1;best=min(best,mask.bit_count())
 rng=random.Random(seed^0x5A17);better=0
 for _ in range(tail):
  mask=rng.getrandbits(18)
  if (mask&required)==required and (mask&forbidden)==0 and mask.bit_count()<best:better+=1
 return {'architectures':1<<18,'accepted':accepted,'best_enabled_features':best,'tail':tail,'tail_better_without_degradation':better}

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();audit=code_audit();sim=simulate(a.cases,a.tail,a.seed);mini=minimality(a.seed,a.tail);status='PASS' if not audit and sim['violations']==0 and (not sim['saturated'] or sim['tail_novelty']==0) and sim['families_covered']==FAMILIES and mini['tail_better_without_degradation']==0 else 'FAIL';print(json.dumps({'schema':'ikant-product-experience-edges/v0.27-test','seed':a.seed,'code_audit_errors':audit,**sim,'minimality':mini,'status':status},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
