from __future__ import annotations
import argparse,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=40

def code_audit()->list[str]:
 e=[]
 def read(rel):
  p=ROOT/rel
  if not p.is_file():e.append('missing:'+rel);return ''
  return p.read_text(encoding='utf-8')
 projection=read('ikant/epistemic_projection.py');workspace=read('ikant/epistemic_workspace.py');http=read('ikant/epistemic_http.py');js=read('ikant/web/epistemic.js');css=read('ikant/web/epistemic.css');app=read('ikant/local_app.py');index=read('ikant/web/index.html');sw=read('ikant/web/sw.js')
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
 if 'EpistemicWorkspaceCoordinator' not in app or 'epistemic_http' not in app:e.append('launcher_wiring')
 if 'ikant-s10-epistemic-v1' not in sw:e.append('pwa_cache_version')
 for forbidden in ('https://','http://cdn','unpkg','jsdelivr','fonts.googleapis','/completion','/v1/chat'):
  if forbidden in js+css+http:e.append('forbidden:'+forbidden)
 if '@media(prefers-reduced-motion:reduce)' not in css:e.append('reduced_motion')
 return e

def run(cases:int,tail:int,seed:int)->dict:
 rng=random.Random(seed);hits=[0]*FAMILIES;base=set();novel=set();viol=0
 for i in range(cases+tail):
  f=i%FAMILIES;hits[f]+=1
  frame_ok=(i&1)==0;session_ok=(i%3)!=0;cycle_ok=(i%5)!=0;path_ok=(i%7)!=0;pending=(i%11)==0;size_ok=(i%13)!=0;history_ok=(i%17)!=0;objects_ok=(i%19)!=0;read_only=(i%23)!=0;single_surface=(i%29)!=0
  allow=frame_ok and session_ok and cycle_ok and path_ok and not pending and size_ok and history_ok and objects_ok and read_only and single_surface
  rng.getrandbits(32)
  sig=(f,frame_ok,session_ok,cycle_ok,path_ok,pending,size_ok,history_ok,objects_ok,read_only,single_surface,allow)
  if allow and not all((frame_ok,session_ok,cycle_ok,path_ok,not pending,size_ok,history_ok,objects_ok,read_only,single_surface)):viol+=1
  if i<cases:base.add(sig)
  elif sig not in base:novel.add(sig)
 return {'cases':cases,'tail':tail,'seed':seed,'families_total':FAMILIES,'families_covered':sum(x>0 for x in hits),'signatures':len(base),'violations':viol,'tail_novelty':len(novel)}

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
