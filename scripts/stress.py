from __future__ import annotations
import argparse,json,random,tempfile
from pathlib import Path
import sys
if __package__ in {None,''}:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.helpers import active_runtime
from ikant.model import *
def run(cases=10000,novelty_tail=1000,seed=883):
 rng=random.Random(seed)
 with tempfile.TemporaryDirectory() as td:
  rt=active_runtime(Path(td)); ids=[]
  for i in range(cases):
   n=rt.ingest(kind=NodeKind.CLAIM,layer=list(Layer)[i%len(Layer)],text=f'case {i} token {i%97}',confidence=rng.random(),evidence=rng.random(),source_mode='repository');ids.append(n.id)
   if i%7==0 and len(ids)>1:rt.relate(ids[-2],ids[-1],RelationKind.ASSOCIATES,rng.random())
  before=len(rt.nodes);s=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='no novelty sentinel',confidence=.5,evidence=.4,source_mode='user');e=s.evidence;first=len(rt.nodes)
  for _ in range(novelty_tail):rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='no novelty sentinel',confidence=1,evidence=1,source_mode='user')
  if len(rt.nodes)!=first or rt.nodes[s.id].evidence!=e:raise AssertionError('no-novelty invariant')
  return {'schema':'ikant-static-stress/v0.1','cases':cases,'novelty_tail':novelty_tail,'nodes':len(rt.nodes),'relations':len(rt.relations),'events':rt.graph['seq'],'status':'PASS'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10000);p.add_argument('--novelty-tail',type=int,default=1000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();print(json.dumps(run(a.cases,a.novelty_tail,a.seed),indent=2,sort_keys=True))
