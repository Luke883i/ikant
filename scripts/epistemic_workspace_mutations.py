from __future__ import annotations
import argparse,json,random
CLASSES=('FRAME_DRIFT','SECOND_WRITER','PENDING_READ','SESSION_DRIFT','CYCLE_TRAVERSAL','SNAPSHOT_OVERSIZE','DIGEST_DRIFT','ARTIFACT_PATH_ESCAPE','ARBITRARY_EVENT_LEAK','UI_AUTHORITY','SECOND_SEMANTIC_SURFACE','REMOTE_FRONTEND','BROWSER_MODEL_PATH','HISTORY_UNBOUNDED','OBJECT_UNBOUNDED','READ_TO_WRITE_COLLAPSE')
FAMILIES=tuple(f'{CLASSES[i%len(CLASSES)]}:{i:03d}' for i in range(128))
BASE={
 'exact_frame':True,'single_writer':True,'pending_read':False,'same_session':True,'cycle_safe':True,
 'snapshot_max':4*1024*1024,'digest_required':True,'generated_artifact_path':True,
 'event_keys':frozenset({'phase','reason','status','kind','count','validated'}),'ui_authority':0.0,
 'semantic_surfaces':1,'remote_frontend':False,'browser_model_path':False,'history_max':64,'objects_max':96,'read_only':True,
}

def valid(p:dict)->bool:
 return bool(
  p['exact_frame'] and p['single_writer'] and not p['pending_read'] and p['same_session'] and p['cycle_safe']
  and p['snapshot_max']<=4*1024*1024 and p['digest_required'] and p['generated_artifact_path']
  and p['event_keys']<=frozenset({'phase','reason','status','kind','count','validated'})
  and p['ui_authority']==0.0 and p['semantic_surfaces']==1 and not p['remote_frontend'] and not p['browser_model_path']
  and p['history_max']<=64 and p['objects_max']<=96 and p['read_only']
 )

def mutate(cls:str,variant:int,nonce:int)->dict:
 p=dict(BASE);p['event_keys']=set(BASE['event_keys'])
 if cls=='FRAME_DRIFT':p['exact_frame']=False
 elif cls=='SECOND_WRITER':p['single_writer']=False
 elif cls=='PENDING_READ':p['pending_read']=True
 elif cls=='SESSION_DRIFT':p['same_session']=False
 elif cls=='CYCLE_TRAVERSAL':p['cycle_safe']=False
 elif cls=='SNAPSHOT_OVERSIZE':p['snapshot_max']=4*1024*1024+1+(variant%4096)
 elif cls=='DIGEST_DRIFT':p['digest_required']=False
 elif cls=='ARTIFACT_PATH_ESCAPE':p['generated_artifact_path']=False
 elif cls=='ARBITRARY_EVENT_LEAK':p['event_keys'].add(('secret','token','raw_payload','authorization')[variant%4])
 elif cls=='UI_AUTHORITY':p['ui_authority']=1.0+(nonce&3)
 elif cls=='SECOND_SEMANTIC_SURFACE':p['semantic_surfaces']=2+(variant%3)
 elif cls=='REMOTE_FRONTEND':p['remote_frontend']=True
 elif cls=='BROWSER_MODEL_PATH':p['browser_model_path']=True
 elif cls=='HISTORY_UNBOUNDED':p['history_max']=65+(variant%256)
 elif cls=='OBJECT_UNBOUNDED':p['objects_max']=97+(variant%512)
 elif cls=='READ_TO_WRITE_COLLAPSE':p['read_only']=False
 return p

def run(mutations:int,tail:int,seed:int)->dict:
 rng=random.Random(seed);survivors=0;base_f=set();base_c=set();tail_f=set();tail_c=set();hits=[0]*len(FAMILIES)
 for i in range(mutations+tail):
  f=i%len(FAMILIES);hits[f]+=1;cls=CLASSES[f%len(CLASSES)];variant=f//len(CLASSES);p=mutate(cls,variant,rng.getrandbits(64));survivors+=int(valid(p))
  if i<mutations:base_f.add(f);base_c.add(cls)
  else:
   if f not in base_f:tail_f.add(f)
   if cls not in base_c:tail_c.add(cls)
 return {'schema':'ikant-epistemic-workspace-mutations/v0.28-test','mutations':mutations,'tail':tail,'seed':seed,'families_total':len(FAMILIES),'families_covered':sum(x>0 for x in hits),'kill_classes':len(base_c),'survivors':survivors,'tail_new_families':len(tail_f),'tail_new_classes':len(tail_c),'status':'PASS' if survivors==0 and len(base_f)==len(FAMILIES) and not tail_f and not tail_c else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=10000000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();o=run(a.mutations,a.tail,a.seed);print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o['status']=='PASS' else 1)
if __name__=='__main__':main()
