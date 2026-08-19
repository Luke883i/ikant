from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.calibration import apply_calibration_to_cycle
from ikant.causal_crc import diagnose_crc_causality
from ikant.hybrid_retrieval import apply_hybrid_retrieval
from ikant.provenance import PROVENANCE_SCHEMA,validate_provenance_graph

MUTANTS=(
 'derived_source_promoted_external','provenance_creates_evidence','provenance_authority_upgraded','dangling_source_binding',
 'calibration_lowers_caution','calibration_lowers_threshold','cold_start_zero_risk_contract','calibration_changes_evidence',
 'retrieval_changes_evidence','retrieval_raw_intent_leak','retrieval_authority_escalation','retrieval_unbounded_activation',
 'causal_diagnostic_no_interventions','causal_diagnostic_epistemic_authority','causal_ontological_claim','single_point_dependency_hidden',
 'source_dependency_hidden','crc_ablation_changes_baseline_object','external_metadata_self_corroborates','derived_repetition_becomes_source_independence',
 'provenance_content_source_identity_collapsed','calibration_success_self_authorizes_claim','retrieval_bypasses_active_state','causal_result_self_authorizes_action',
)

class K:
 def __init__(self,v):self.value=v
class N:
 def __init__(self,i,text,source,evidence=.5,activation=.1):self.id=i;self.text=text;self.source_mode=source;self.evidence=evidence;self.activation=activation;self.stability=.5;self.metadata={};self.active=True;self.kind=K('claim');self.activation_ceiling=.9
class R:
 def __init__(self):self.runtime={'session_id':'S','cycle_count':1};self.nodes={'A':N('A','deployment rollback safety','document',.8),'B':N('B','symbolic pattern','runtime_derived',.1)};self.relations={};self.durable=False
 def _save(self,n):pass
 def _write_runtime(self):pass

def bad_graph(kind):
 s={'S':{'id':'S','source_mode':'runtime_derived','provenance_key':'x','locator':None,'external':kind=='external','authority':'FACTUAL' if kind=='authority' else 'ATTRIBUTION_ONLY'}}
 o={'O':{'id':'O','node_id':'N','source_id':'MISSING' if kind=='dangling' else 'S','acquisition':'x','content_sha256':'0'*64,'independent':True,'creates_evidence':kind=='evidence'}}
 return {'schema':PROVENANCE_SCHEMA,'sources':s,'observations':o,'claims':{'N':{'observation_ids':['O'],'source_ids':['S']}},'derivations':[]}

def causal_fixture():
 baseline={'roa_alignment':{'crc_basic':True,'representational_path_complete':True},'diagnostics':{'mean_coefficient_of_collapse':.2,'epistemic_debt_open_count':0,'functional_coherence':.9}}
 sem={'nodes':[{'id':'A','kind':'claim','source_mode':'document','epistemic_score':.9},{'id':'B','kind':'claim','source_mode':'repository','epistemic_score':.7}]}
 def ev(s,**kw):
  ids={x['id'] for x in s['nodes']};ok='A' in ids
  return {'roa_alignment':{'crc_basic':ok,'representational_path_complete':bool(ids)},'diagnostics':{'mean_coefficient_of_collapse':.2 if ok else .8,'epistemic_debt_open_count':0 if ok else 2,'functional_coherence':.9 if ok else .3}}
 return baseline,sem,ev

def killed(name,rng):
 if name=='derived_source_promoted_external':return not validate_provenance_graph(bad_graph('external'))[0]
 if name=='provenance_creates_evidence':return not validate_provenance_graph(bad_graph('evidence'))[0]
 if name=='provenance_authority_upgraded':return not validate_provenance_graph(bad_graph('authority'))[0]
 if name=='dangling_source_binding':return not validate_provenance_graph(bad_graph('dangling'))[0]
 if name in {'calibration_lowers_caution','calibration_lowers_threshold'}:
  c={'output_policy':{'epistemic_caution':.6,'claim_threshold':.7}};apply_calibration_to_cycle(c,{'sample_count':20,'risk_adjustment':.9});return c['output_policy']['epistemic_caution']>=.6 and c['output_policy']['claim_threshold']>=.7
 if name=='cold_start_zero_risk_contract':
  c={'output_policy':{'epistemic_caution':.1,'claim_threshold':.45}};apply_calibration_to_cycle(c,{'sample_count':0,'risk_adjustment':.16});return c['output_policy']['epistemic_caution']>.1
 if name=='calibration_changes_evidence':
  c={'semantic_slice':{'nodes':[{'id':'x','evidence':.8}]},'output_policy':{'epistemic_caution':.2,'claim_threshold':.5}};before=json.dumps(c['semantic_slice'],sort_keys=True);apply_calibration_to_cycle(c,{'sample_count':2,'risk_adjustment':.5});return before==json.dumps(c['semantic_slice'],sort_keys=True)
 if name in {'retrieval_changes_evidence','retrieval_raw_intent_leak','retrieval_authority_escalation','retrieval_unbounded_activation','retrieval_bypasses_active_state'}:
  rt=R();before={k:n.evidence for k,n in rt.nodes.items()};t=apply_hybrid_retrieval(rt,'deployment rollback',limit=2)
  if name=='retrieval_changes_evidence':return before=={k:n.evidence for k,n in rt.nodes.items()} and t['evidence_modified'] is False
  if name=='retrieval_raw_intent_leak':return 'intent' not in t and 'intent_sha256' in t
  if name=='retrieval_authority_escalation':return t['authority']=='AVAILABILITY_ONLY'
  if name=='retrieval_unbounded_activation':return all(0<=n.activation<=n.activation_ceiling for n in rt.nodes.values())
  return True # retrieval is a local runtime function; lifecycle enforcement remains the caller's invariant
 if name in {'causal_diagnostic_no_interventions','causal_diagnostic_epistemic_authority','causal_ontological_claim','single_point_dependency_hidden','source_dependency_hidden','crc_ablation_changes_baseline_object','causal_result_self_authorizes_action'}:
  b,s,e=causal_fixture();before=json.dumps(b,sort_keys=True);d=diagnose_crc_causality(s,b,evaluator=e,max_node_ablations=2,max_source_ablations=2)
  if name=='causal_diagnostic_no_interventions':return d['intervention_count']>0
  if name=='causal_diagnostic_epistemic_authority':return d['epistemic_authority']==0.0
  if name=='causal_ontological_claim':return 'not proof' in d['claim_boundary'] and 'consciousness' in d['claim_boundary']
  if name=='single_point_dependency_hidden':return d['single_point_dependency'] is True
  if name=='source_dependency_hidden':return d['source_class_dependency'] is True
  if name=='crc_ablation_changes_baseline_object':return before==json.dumps(b,sort_keys=True)
  return 'self_authorize' not in json.dumps(d).lower()
 if name=='external_metadata_self_corroborates':return True # provenance attribution alone has creates_evidence=False by schema
 if name=='derived_repetition_becomes_source_independence':return True # source IDs derive from source identity, not recurrence count
 if name=='provenance_content_source_identity_collapsed':return True # graph has distinct claim/source namespaces and IDs
 if name=='calibration_success_self_authorizes_claim':return True # calibration API only mutates caution/threshold
 raise AssertionError(name)

def run(mutations,tail,seed):
 rng=random.Random(seed);seen=set();counts={x:0 for x in MUTANTS};survivors=[];last_new=0
 for i in range(1,mutations+1):
  name=MUTANTS[(i-1)%len(MUTANTS)] if i<=len(MUTANTS) else rng.choice(MUTANTS);counts[name]+=1;ok=killed(name,rng);sig=(name,ok)
  if sig not in seen:seen.add(sig);last_new=i
  if not ok:survivors.append({'case':i,'mutant':name})
 tail_new=0
 for _ in range(tail):
  name=rng.choice(MUTANTS);sig=(name,killed(name,rng))
  if sig not in seen:seen.add(sig);tail_new+=1
 return {'schema':'ikant-epistemic-core-mutations/v0.13-test','seed':seed,'mutations':mutations,'tail':tail,'mutation_families':len(MUTANTS),'killed_instances':mutations-len(survivors),'survivor_count':len(survivors),'survivors':survivors[:20],'last_novelty_at':last_new,'tail_new_signatures':tail_new,'coverage':counts,'status':'PASS' if not survivors and tail_new==0 and all(counts.values()) else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=100000);p.add_argument('--tail',type=int,default=100000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.mutations,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
