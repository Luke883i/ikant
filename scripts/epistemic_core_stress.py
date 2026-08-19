from __future__ import annotations
import argparse,itertools,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.calibration import apply_calibration_to_cycle
from ikant.causal_crc import diagnose_crc_causality
from ikant.provenance import PROVENANCE_SCHEMA,validate_provenance_graph

# Fourteen binary pressures => 16,384 explicit semantic configurations, then random replay.
NAMES=('external','derived','multi_source','bad_calibration','cold_start','high_confidence','semantic_disconnect','graph_link','conflict','stale','node_dependency','source_dependency','horizon_pressure','privacy_pressure')
UNIVERSE=list(itertools.product((False,True),repeat=len(NAMES)))

def scenario(bits):
 d=dict(zip(NAMES,bits)); errors=[]
 sources={};observations={};claims={'N':{'observation_ids':[],'source_ids':[]}}
 def add_source(sid,mode,external):
  sources[sid]={'id':sid,'source_mode':mode,'provenance_key':sid,'locator':None,'external':external,'authority':'ATTRIBUTION_ONLY'}
  oid='O'+sid;observations[oid]={'id':oid,'node_id':'N','source_id':sid,'acquisition':'stress','content_sha256':'0'*64,'independent':True,'creates_evidence':False};claims['N']['observation_ids'].append(oid);claims['N']['source_ids'].append(sid)
 if d['external']:add_source('E','document',True)
 if d['derived']:add_source('D','runtime_derived',False)
 if d['multi_source']:add_source('R','repository',True)
 graph={'schema':PROVENANCE_SCHEMA,'sources':sources,'observations':observations,'claims':claims,'derivations':[]}
 ok,perr=validate_provenance_graph(graph)
 if not ok:errors.extend(perr)
 base=.18 if d['cold_start'] else (.2 if d['bad_calibration'] else .08); risk=min(1.,base+(.12 if d['high_confidence'] and d['bad_calibration'] else 0))
 cycle={'output_policy':{'epistemic_caution':.25,'claim_threshold':.52}}
 apply_calibration_to_cycle(cycle,{'sample_count':0 if d['cold_start'] else 12,'risk_adjustment':risk})
 if cycle['output_policy']['epistemic_caution']<.25 or cycle['output_policy']['claim_threshold']<.52:errors.append('calibration_relaxed')
 baseline={'roa_alignment':{'crc_basic':not d['horizon_pressure'],'representational_path_complete':True},'diagnostics':{'mean_coefficient_of_collapse':.2,'epistemic_debt_open_count':0,'functional_coherence':.8}}
 sem={'nodes':[{'id':'N1','kind':'claim','source_mode':'document','epistemic_score':.9},{'id':'N2','kind':'claim','source_mode':'repository','epistemic_score':.7}]}
 def evaluator(slice_,**kwargs):
  ids={x['id'] for x in slice_['nodes']};ok0=not d['horizon_pressure']
  if d['node_dependency'] and 'N1' not in ids:ok0=False
  if d['source_dependency'] and not any(x.get('source_mode')=='document' for x in slice_['nodes']):ok0=False
  return {'roa_alignment':{'crc_basic':ok0,'representational_path_complete':bool(ids)},'diagnostics':{'mean_coefficient_of_collapse':.2 if ok0 else .7,'epistemic_debt_open_count':0 if ok0 else 1,'functional_coherence':.8 if ok0 else .4}}
 causal=diagnose_crc_causality(sem,baseline,evaluator=evaluator,max_node_ablations=2,max_source_ablations=2)
 if d['node_dependency'] and not d['horizon_pressure'] and not causal['single_point_dependency']:errors.append('node_dependency_missed')
 if d['source_dependency'] and not d['horizon_pressure'] and not causal['source_class_dependency']:errors.append('source_dependency_missed')
 if causal['epistemic_authority']!=0.0:errors.append('causal_authority')
 signature=(tuple(sorted(k for k,v in d.items() if v)),ok,round(cycle['output_policy']['epistemic_caution'],3),causal['single_point_dependency'],causal['source_class_dependency'],bool(errors))
 return signature,errors

def run(cases,tail,seed):
 rng=random.Random(seed);seen=set();last_new=0;errors=[]
 for i in range(1,cases+1):
  bits=UNIVERSE[(i-1)%len(UNIVERSE)] if i<=len(UNIVERSE) else rng.choice(UNIVERSE);sig,bad=scenario(bits)
  if sig not in seen:seen.add(sig);last_new=i
  if bad:errors.append({'case':i,'errors':bad,'bits':bits})
 tail_new=0
 for _ in range(tail):
  sig,bad=scenario(rng.choice(UNIVERSE));
  if sig not in seen:seen.add(sig);tail_new+=1
  if bad:errors.append({'tail':True,'errors':bad})
 return {'schema':'ikant-epistemic-core-stress/v0.13-test','seed':seed,'M':cases,'M_plus_tail':cases+tail,'semantic_universe':len(UNIVERSE),'causal_signatures':len(seen),'last_novelty_at':last_new,'tail_new_signatures':tail_new,'error_count':len(errors),'errors':errors[:20],'status':'PASS' if not errors and tail_new==0 else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=100000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.cases,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
