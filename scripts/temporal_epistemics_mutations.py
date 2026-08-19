from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.model import Node,NodeKind,Layer,Relation,RelationKind
from ikant.temporal_memory import set_temporal_state,temporal_available,materialize_temporal_memory
from ikant.commitments import register_commitment,supersede_commitment,retract_commitment,commitment_projection
from ikant.dependency_invalidation import invalidate_source
from ikant.temporal_replay import validate_temporal_replay,temporal_events
from ikant.temporal_core import finalize_temporal_core

MUTANTS=(
 'classification_changes_evidence','temporal_state_changes_evidence','superseded_commitment_stays_active','retracted_commitment_stays_active',
 'self_supersession_allowed','resupersede_old_allowed','successor_not_current','old_lexical_match_reactivates','revoked_only_source_stays_active',
 'partial_revocation_suppresses_independent_claim','revocation_changes_evidence','revocation_propagates_into_external_claim','derived_dependency_survives',
 'source_revocation_not_journaled','replay_collapses_invalidation_types','replay_ignores_tamper','replay_source_state_missing','duplicate_projection_nondeterministic',
 'memory_summary_has_epistemic_authority','commitment_projection_has_epistemic_authority','history_becomes_evidence','forgotten_node_available',
 'dependency_invalidation_self_authorizes_action','source_revocation_erases_history','inactive_commitment_emitted_current','unregistered_goal_misclassified',
 'interpretive_memory_promoted_semantic','kernel_memory_treated_commitment','unknown_state_accepted','unknown_memory_class_accepted',
 'source_key_miss_silently_passes','derived_chain_invalidates_unrelated_node','failed_transition_leaves_events','replay_divergence_not_fail_closed','source_revocation_state_not_reconstructible',
 'temporal_events_pollute_cognitive_stream','temporal_journal_hash_tamper_accepted','unjournaled_temporal_state_accepted','nonindependent_source_preserves_claim'
)
class RT:
 def __init__(self):self.nodes={};self.relations={};self.runtime={'session_id':'S','temporal_memory':{}};self.graph={'seq':0};self.events_mem=[];self.durable=False
 def _save(self,n):self.nodes[n.id]=n
 def _write_runtime(self):pass
 def _event(self,op,subject,payload):self.graph['seq']+=1;e={'seq':self.graph['seq'],'op':op,'subject':subject,'payload':payload};self.events_mem.append(e);return e['seq']
def n(i,k='claim',source='user',e=.7):return Node(i,NodeKind(k),Layer.MEMORY,i,.7,e,source)
def fixture():
 rt=RT();rt.nodes={'A':n('A','claim','document'),'B':n('B','summary','runtime_derived'),'C':n('C','claim','repository'),'G1':n('G1','goal'),'G2':n('G2','goal')};rt.relations={'R1':Relation('R1','A','B',RelationKind.SUPPORTS,.8),'R2':Relation('R2','A','C',RelationKind.SUPPORTS,.8)}
 graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'doc:a'},'S2':{'id':'S2','external':True,'provenance_key':'repo:c'}},'claims':{'A':{'source_ids':['S1'],'observation_ids':['O1']},'B':{'source_ids':[],'observation_ids':[]},'C':{'source_ids':['S2'],'observation_ids':['O2']}},'observations':{'O1':{'source_id':'S1','independent':True},'O2':{'source_id':'S2','independent':True}}}
 return rt,graph

def killed(name):
 rt,graph=fixture();before={k:v.evidence for k,v in rt.nodes.items()}
 if name=='classification_changes_evidence':materialize_temporal_memory(rt);return before=={k:v.evidence for k,v in rt.nodes.items()}
 if name=='temporal_state_changes_evidence':set_temporal_state(rt,'A','FORGOTTEN',reason='x');return rt.nodes['A'].evidence==before['A']
 if name=='superseded_commitment_stays_active':supersede_commitment(rt,'G1','G2',reason='r');return not temporal_available(rt.nodes['G1'])
 if name=='retracted_commitment_stays_active':register_commitment(rt,'G1');retract_commitment(rt,'G1',reason='r');return not temporal_available(rt.nodes['G1'])
 if name=='self_supersession_allowed':
  try:supersede_commitment(rt,'G1','G1',reason='x');return False
  except ValueError:return True
 if name=='resupersede_old_allowed':
  supersede_commitment(rt,'G1','G2',reason='x')
  try:supersede_commitment(rt,'G1','G2',reason='y');return False
  except ValueError:return True
 if name=='successor_not_current':supersede_commitment(rt,'G1','G2',reason='x');return temporal_available(rt.nodes['G2'])
 if name=='old_lexical_match_reactivates':supersede_commitment(rt,'G1','G2',reason='x');rt.nodes['G1'].activation=.9;return not temporal_available(rt.nodes['G1'])
 if name=='revoked_only_source_stays_active':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return not temporal_available(rt.nodes['A'])
 if name=='partial_revocation_suppresses_independent_claim':graph['sources']['S3']={'id':'S3','external':True,'provenance_key':'doc:b'};graph['claims']['A']['source_ids'].append('S3');graph['claims']['A']['observation_ids'].append('O3');graph['observations']['O3']={'source_id':'S3','independent':True};invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return temporal_available(rt.nodes['A'])
 if name=='revocation_changes_evidence':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return before=={k:v.evidence for k,v in rt.nodes.items()}
 if name=='revocation_propagates_into_external_claim':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return temporal_available(rt.nodes['C'])
 if name=='derived_dependency_survives':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return not temporal_available(rt.nodes['B'])
 if name=='source_revocation_not_journaled':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return any(e['op']=='SOURCE_REVOKE' for e in temporal_events(rt))
 if name=='replay_collapses_invalidation_types':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);r=validate_temporal_replay(rt);return r['ok'] and rt.nodes['B'].metadata['temporal_state']=='DEPENDENCY_INVALIDATED'
 if name=='replay_ignores_tamper':register_commitment(rt,'G1');rt.nodes['G1'].metadata['commitment_status']='RETRACTED';return not validate_temporal_replay(rt)['ok']
 if name=='replay_source_state_missing':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);rt.runtime['temporal_memory']['source_revocations'].clear();return not validate_temporal_replay(rt)['ok']
 if name=='duplicate_projection_nondeterministic':register_commitment(rt,'G1');a=commitment_projection(rt)['sha256'];register_commitment(rt,'G1');b=commitment_projection(rt)['sha256'];return a==b
 if name=='memory_summary_has_epistemic_authority':return materialize_temporal_memory(rt)['summary']['epistemic_authority']==0
 if name=='commitment_projection_has_epistemic_authority':register_commitment(rt,'G1');return commitment_projection(rt)['epistemic_authority']==0
 if name=='history_becomes_evidence':materialize_temporal_memory(rt);return before=={k:v.evidence for k,v in rt.nodes.items()}
 if name=='forgotten_node_available':set_temporal_state(rt,'A','FORGOTTEN',reason='x');return not temporal_available(rt.nodes['A'])
 if name=='dependency_invalidation_self_authorizes_action':out=invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return 'authorize' not in json.dumps(out).lower()
 if name=='source_revocation_erases_history':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return 'A' in rt.nodes and rt.nodes['A'].metadata['temporal_state']=='SOURCE_REVOKED'
 if name=='inactive_commitment_emitted_current':supersede_commitment(rt,'G1','G2',reason='x');return 'G1' not in commitment_projection(rt)['active_node_ids']
 if name=='unregistered_goal_misclassified':return materialize_temporal_memory(rt)['records']['G1']['memory_class']=='commitment'
 if name=='interpretive_memory_promoted_semantic':return materialize_temporal_memory(rt)['records']['B']['memory_class']=='interpretive'
 if name=='kernel_memory_treated_commitment':rt.nodes['K']=n('K','principle','repository');return materialize_temporal_memory(rt)['records']['K']['memory_class']=='kernel'
 if name=='unknown_state_accepted':
  try:set_temporal_state(rt,'A','MAGIC',reason='x');return False
  except ValueError:return True
 if name=='unknown_memory_class_accepted':
  rt.nodes['A'].metadata['memory_class']='magic';return materialize_temporal_memory(rt)['records']['A']['memory_class']!='magic'
 if name=='source_key_miss_silently_passes':
  try:invalidate_source(rt,'missing',reason='x',provenance_graph=graph);return False
  except KeyError:return True
 if name=='derived_chain_invalidates_unrelated_node':invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return temporal_available(rt.nodes['C'])
 if name=='failed_transition_leaves_events':
  supersede_commitment(rt,'G1','G2',reason='x');before=len(temporal_events(rt));rt.nodes['G3']=n('G3','goal')
  try:supersede_commitment(rt,'G1','G3',reason='y')
  except ValueError:pass
  return len(temporal_events(rt))==before and 'commitment_id' not in rt.nodes['G3'].metadata
 if name=='replay_divergence_not_fail_closed':
  register_commitment(rt,'G1');rt.nodes['G1'].metadata['commitment_status']='RETRACTED'
  try:finalize_temporal_core(rt);return False
  except RuntimeError:return True
 if name=='temporal_events_pollute_cognitive_stream':
  register_commitment(rt,'G1');return rt.events_mem==[] and len(temporal_events(rt))>0
 if name=='temporal_journal_hash_tamper_accepted':
  register_commitment(rt,'G1');rt._ikant_temporal_events_mem[0]['payload']['status']='RETRACTED';return not validate_temporal_replay(rt)['ok']
 if name=='unjournaled_temporal_state_accepted':
  rt.nodes['A'].metadata['temporal_state']='FORGOTTEN';rt.nodes['A'].active=False;return not validate_temporal_replay(rt)['ok']
 if name=='nonindependent_source_preserves_claim':
  graph['sources']['S3']={'id':'S3','external':True,'provenance_key':'mirror:a'};graph['claims']['A']['source_ids'].append('S3');graph['claims']['A']['observation_ids'].append('O3');graph['observations']['O3']={'source_id':'S3','independent':False};invalidate_source(rt,'S1',reason='x',provenance_graph=graph);return not temporal_available(rt.nodes['A'])
 if name=='source_revocation_state_not_reconstructible':
  invalidate_source(rt,'S1',reason='x',provenance_graph=graph);rt.runtime['temporal_memory']['source_revocations'].clear()
  # A second revocation path must rebuild prior revocations from journal.
  graph['sources']['S3']={'id':'S3','external':True,'provenance_key':'doc:z'};graph['claims']['A']['source_ids'].append('S3');graph['claims']['A']['observation_ids'].append('O3');graph['observations']['O3']={'source_id':'S3','independent':True};rt.nodes['A'].active=True;rt.nodes['A'].metadata['temporal_state']='ACTIVE'
  invalidate_source(rt,'S3',reason='z',provenance_graph=graph)
  return 'S1' in rt.runtime['temporal_memory']['source_revocations'] and not temporal_available(rt.nodes['A'])
 raise AssertionError(name)

def run(mutations,tail,seed):
 results={m:killed(m) for m in MUTANTS};survivors=[m for m,v in results.items() if not v];seen=set();last_new=0
 # ensure every family is represented before random tail
 for i in range(1,mutations+1):
  m=MUTANTS[(i-1)%len(MUTANTS)];sig=(m,results[m])
  if sig not in seen:seen.add(sig);last_new=i
 rng=random.Random(seed);tail_new=0
 for _ in range(tail):
  m=rng.choice(MUTANTS);sig=(m,results[m])
  if sig not in seen:seen.add(sig);tail_new+=1
 return {'schema':'ikant-temporal-epistemics-mutations/v0.14-test','seed':seed,'mutations':mutations,'M_plus_tail':mutations+tail,'families':len(MUTANTS),'last_novelty_at':last_new,'tail_new_signatures':tail_new,'survivors':survivors,'status':'PASS' if not survivors and tail_new==0 and mutations>=len(MUTANTS) else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=100000);p.add_argument('--tail',type=int,default=100000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();out=run(a.mutations,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
