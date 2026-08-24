from __future__ import annotations

import argparse
import json

MASK64=(1<<64)-1
CAMPAIGNS={
 'hardening':{'families':64,'phases':8,'contexts':4,'mutation_classes':4,'seed':202608240101,'tail_seed':202608240111,'declared_open_families':22,'meaning':'repository-bound foundation, provenance, state and control-plane fault vocabulary'},
 'hypothetical':{'families':72,'phases':8,'contexts':4,'mutation_classes':4,'seed':202608240102,'tail_seed':202608240112,'declared_open_families':30,'meaning':'future-slice dependency, supply-chain, adversarial and edge-case vocabulary'},
 'usage':{'families':48,'phases':10,'contexts':4,'mutation_classes':6,'seed':202608240103,'tail_seed':202608240113,'declared_open_families':18,'meaning':'normal, typical, recovery, accessibility, stress and user-control vocabulary'},
}

def splitmix64(value:int)->int:
 value=(value+0x9E3779B97F4A7C15)&MASK64
 value=((value^(value>>30))*0xBF58476D1CE4E5B9)&MASK64
 value=((value^(value>>27))*0x94D049BB133111EB)&MASK64
 return value^(value>>31)

def signature(word:int,cfg:dict)->tuple[int,int]:
 f=cfg['families'];p=cfg['phases'];c=cfg['contexts'];m=cfg['mutation_classes']
 family=word%f;word//=f;phase=word%p;word//=p;context=word%c;word//=c;mutation=word%m
 idx=family+f*(phase+p*(context+c*mutation));return int(idx),int(family)

def run(name:str,cases:int,tail:int,seed:int|None=None)->dict:
 cfg=CAMPAIGNS[name];base_seed=int(cfg['seed'] if seed is None else seed);space=cfg['families']*cfg['phases']*cfg['contexts']*cfg['mutation_classes'];seen=bytearray(space);counts=[0]*cfg['families'];gap_hits=0
 for i in range(max(0,int(cases))):
  idx,family=signature(splitmix64(base_seed+i),cfg);seen[idx]=1;counts[family]+=1;gap_hits+=int(family<cfg['declared_open_families'])
 before=sum(seen);new_tail=0
 for i in range(max(0,int(tail))):
  idx,_=signature(splitmix64(int(cfg['tail_seed'])+i),cfg)
  if not seen[idx]:seen[idx]=1;new_tail+=1
 return {'schema':'ikant-development-continuity-model/v1-test','campaign':name,'meaning':cfg['meaning'],'cases':int(cases),'seed':base_seed,'dimensions':{'families':cfg['families'],'phases':cfg['phases'],'contexts':cfg['contexts'],'mutation_classes':cfg['mutation_classes']},'signature_space':space,'signatures_observed':before,'coverage_complete':before==space,'declared_open_family_occurrences':gap_hits,'family_hit_min':min(counts) if counts else 0,'family_hit_max':max(counts) if counts else 0,'tail':int(tail),'tail_seed':cfg['tail_seed'],'tail_new_signatures':new_tail,'model_results_are_production_reliability_estimates':False,'interpretation':'deterministic coverage of the declared engineering vocabulary; executable browser/OS/provider oracles remain separate'}

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--campaign',choices=tuple(CAMPAIGNS),required=True);ap.add_argument('--cases',type=int,default=10000000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int);a=ap.parse_args();out=run(a.campaign,a.cases,a.tail,a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['coverage_complete'] and out['tail_new_signatures']==0 else 2
if __name__=='__main__':raise SystemExit(main())
