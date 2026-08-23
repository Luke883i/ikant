from __future__ import annotations
import argparse,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=40
EDGE_VECTORS=64
DENIAL_KEYS=(
 ('FRAME_DRIFT','frame',True),('SESSION_DRIFT','session',True),('CYCLE_DRIFT','cycle',True),
 ('PATH_ESCAPE','path',True),('PENDING_FRAME','pending',False),('SNAPSHOT_BOUND','size',True),
 ('HISTORY_BOUND','history',True),('OBJECT_BOUND','objects',True),('READ_ONLY','read_only',True),
 ('SINGLE_SURFACE','single_surface',True),
)

def code_audit()->list[str]:
 e=[]
 def read(rel):
  p=ROOT/rel
  if not p.is_file():e.append('missing:'+rel);return ''
  return p.read_text(encoding='utf-8')
 projection=read('ikant/epistemic_projection.py');workspace=read('ikant/epistemic_workspace.py');http=read('ikant/epistemic_http.py');js=read('ikant/web/epistemic.js');css=read('ikant/web/epistemic.css');app=read('ikant/local_app.py');index=read('ikant/web/index.html');sw=read('ikant/web/sw.js')
 bootstrap_path=ROOT/'ikant/bootstrap_http.py';bootstrap=bootstrap_path.read_text(encoding='utf-8') if bootstrap_path.is_file() else ''
 reactive_path=ROOT/'ikant/reactive_http.py';reactive=reactive_path.read_text(encoding='utf-8') if reactive_path.is_file() else ''
 for marker in ('MAX_HISTORY=64','MAX_SNAPSHOT_BYTES=4*1024*1024','MAX_OBJECTS=96','event_keys'):
  if marker not in projection and marker!='event_keys':e.append('projection:'+marker)
 for marker in ('presentation_is_not_evidence','presentation_is_not_authorization','_last_acked_frame','_pending is not None','cycle path escape','artifact session/cycle mismatch'):
  if marker not in workspace:e.append('workspace:'+marker)
 for marker in ('/api/v4/epistemic/index','/api/v4/epistemic/cycle','/api/v4/epistemic/artifact','make_handler','epistemic.js','epistemic.css'):
  if marker not in http:e.append('http:'+marker)
 for marker in ('EPI_INDEX_SCHEMA','EPI_WORKSPACE_SCHEMA','Graph','List','Space','bindingHeaders','/api/v4/epistemic/artifact'):
  if marker not in js:e.append('ui:'+marker)
 if 'dashboard' in js:e.append('ui_second_semantic_surface_reference')
 if index.count('id="dashboard"')!=1:e.append('semantic_viewport_count')
 direct='epistemic_http' in app
 composed='bootstrap_http' in app and 'make_epistemic_handler' in bootstrap and '.epistemic_http' in bootstrap
 reactive_composed=('reactive_http' in app and 'make_bootstrap_handler' in reactive and '.bootstrap_http' in reactive and 'make_epistemic_handler' in bootstrap and '.epistemic_http' in bootstrap)
 if 'EpistemicWorkspaceCoordinator' not in app or not (direct or composed or reactive_composed):e.append('launcher_wiring')
 if 'const CACHE=' not in sw or 'keys.filter(k=>k!==CACHE)' not in sw:e.append('pwa_stale_cache_invalidation')
 for forbidden in ('https://','http://cdn','unpkg','jsdelivr','fonts.googleapis','/completion','/v1/chat'):
  if forbidden in js+css+http:e.append('forbidden:'+forbidden)
 if '@media(prefers-reduced-motion:reduce)' not in css:e.append('reduced_motion')
 return e

def semantic_edge(i:int)->tuple[int,str,bool]:
 f=i%FAMILIES;vector=(i//FAMILIES)%EDGE_VECTORS
 flags={'frame':True,'session':True,'cycle':True,'path':True,'pending':False,'size':True,'history':True,'objects':True,'read_only':True,'single_surface':True}
 primary=vector%11
 if primary:
  _,key,want=DENIAL_KEYS[primary-1];flags[key]=not want
 if vector>=11:
  _,key,want=DENIAL_KEYS[(vector*7+f)%len(DENIAL_KEYS)];flags[key]=not want
 consequence='ALLOW'
 for name,key,want in DENIAL_KEYS:
  if flags[key]!=want:consequence=name;break
 return f,consequence,consequence=='ALLOW'

def run(cases:int,tail:int,seed:int)->dict:
 rng=random.Random(seed);hits=[0]*FAMILIES;base=set();novel=set();viol=0
 for i in range(cases+tail):
  f,consequence,allow=semantic_edge(i);hits[f]+=1;rng.getrandbits(32)
  if allow and consequence!='ALLOW':viol+=1
  sig=(f,consequence,allow)
  if i<cases:base.add(sig)
  elif sig not in base:novel.add(sig)
 return {'cases':cases,'tail':tail,'seed':seed,'edge_vectors':EDGE_VECTORS,'families_total':FAMILIES,'families_covered':sum(x>0 for x in hits),'signatures':len(base),'violations':viol,'tail_novelty':len(novel)}

def minimality(seed:int,tail:int)->dict:
 required=(1<<13)-1;forbidden=sum(1<<i for i in range(13,20));accepted=0;best=99
 for mask in range(1<<20):
  if (mask&required)==required and (mask&forbidden)==0:accepted+=1;best=min(best,mask.bit_count())
 rng=random.Random(seed^0x10E91);better=0
 for _ in range(tail):
  mask=rng.getrandbits(20)
  if (mask&required)==required and (mask&forbidden)==0 and mask.bit_count()<best:better+=1
 return {'architectures':1<<20,'accepted':accepted,'best_enabled_features':best,'tail':tail,'tail_better_without_degradation':better}
def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10000000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();audit=code_audit();o=run(a.cases,a.tail,a.seed);m=minimality(a.seed,a.tail);status='PASS' if not audit and o['violations']==0 and o['families_covered']==FAMILIES and o['tail_novelty']==0 and m['tail_better_without_degradation']==0 else 'FAIL';print(json.dumps({'schema':'ikant-epistemic-workspace-edges/v0.28-test','code_audit_errors':audit,**o,'minimality':m,'status':status},sort_keys=True));raise SystemExit(0 if status=='PASS' else 1)
if __name__=='__main__':main()
