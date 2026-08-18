from __future__ import annotations
import argparse,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.psyche import derive_functional_psyche,validate_functional_psyche,FACULTIES
RINGS=['signal','salience_homeostasis','memory','predictive_control','metacognition','reflective_self','psychodynamic_hypothesis','archetypal_hypothesis','kant_oracle'];PROPS={'salience_homeostasis':('priority_class','foreground'),'memory':('consolidation_class','recent'),'predictive_control':('control_role','world_model'),'metacognition':('monitor_state','coherent'),'reflective_self':('self_relation','explicit_self'),'psychodynamic_hypothesis':('tension_pressure','low'),'archetypal_hypothesis':('recurring_motif_pressure','recurring'),'kant_oracle':('regulative_context','synthesis')}
def case(rng,i,repeat=False):
 n=1 if repeat else rng.randint(1,16);grounding=.75 if repeat else rng.random();pe=.18 if repeat else rng.random();nov=.3 if repeat else rng.random();conflicts=0 if repeat else rng.randrange(5);debt=0 if repeat else rng.randrange(6);closure=True if repeat else rng.random()>.08;nodes=[]
 for j in range(n):
  src='document' if rng.random()<grounding else rng.choice(['inference','runtime_derived','cache']);nodes.append({'id':f'N{j}','source_mode':src,'epistemic_score':rng.random() if not repeat else .7,'prediction_error':pe,'novelty':nov})
 ring_states={};neuro={}
 for k,r in enumerate(RINGS):
  props={}
  if r in PROPS:props[PROPS[r][0]]=PROPS[r][1]
  if r=='metacognition':props['epistemic_debt_open']=bool(debt)
  if r=='psychodynamic_hypothesis' and conflicts:props.update({'tension_pressure':'elevated','freudian_structural_hypothesis':'unresolved_tension'})
  if r=='archetypal_hypothesis':props['jungian_archetype_candidate']='self_candidate'
  if r=='kant_oracle':props['synthetic_kant_archetype_state']='reflective_synthesis'
  ring_states[r]=[{'id':f'M{k}','support_ids':[x['id'] for x in nodes[:3]],'mean_activation':rng.random() if not repeat else .4,'mean_prediction_error':pe,'properties':props}];neuro[r]={'precision':rng.random(),'control_index':rng.random(),'inhibition':rng.random(),'plasticity':rng.random(),'conflict_pressure':min(1,conflicts/3)}
 transmissions=[]
 for k in range(8):
  c=.2 if repeat else rng.random();inp=rng.randint(1,12);out=max(1,round(inp*(1-c)));transmissions.append({'source':RINGS[k],'target':RINGS[k+1],'input_count':inp,'output_count':out,'coefficient_of_collapse':c})
 crc={'ring_states':ring_states,'neurofunctional_state':neuro,'transmissions':transmissions,'roa_alignment':{'crc_basic':closure},'diagnostics':{'epistemic_debt_open_count':debt,'reticular_irreducibility_proxy':rng.random(),'emergence_index_proxy':rng.random(),'psychodynamic_interpretive_pressure':rng.random()*.4,'archetypal_interpretive_pressure':rng.random()*.3}};cycle={'cycle_id':f'CYC-{i}','semantic_slice':{'nodes':nodes},'output_projection':{'must_surface_conflicts':[{'source':'x','target':'y'}]*conflicts}};proto={'self_model_continuity':rng.random(),'temporal_continuity':rng.random(),'proto_self_index':rng.random()};runtime={'status':'ACTIVE','session_id':'SES-STRESS','host':{'engine_label':'GPT-5.6 Sol'}};return crc,cycle,proto,runtime
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic();prev=None;signatures=set();labels={};max_collapse=0;min_trust=1
 for i in range(a.cases):
  crc,cy,proto,rt=case(rng,i);p=derive_functional_psyche(crc,cy,proto,previous=prev,runtime_state=rt);ok,errs=validate_functional_psyche(p);assert ok,errs;prev=p;af=p['affective_field'];labels[af['label']]=labels.get(af['label'],0)+1;max_collapse=max(max_collapse,p['collapse_emergence']['summary']['max_collapse']);min_trust=min(min_trust,af['synthesis_trust']);signatures.add((af['label'],p['collapse_emergence']['summary']['high_collapse_count']>0,p['epistemic_accumulation']['sample']['conflict']>0,p['epistemic_accumulation']['sample']['epistemic_debt']>0,bool(crc['roa_alignment']['crc_basic'])));assert p['self_knowledge']['operational_self_awareness'] and not p['self_knowledge']['phenomenal_consciousness_claim'];assert not p['collapse_emergence']['evidence_created'];assert not p['epistemic_accumulation']['may_change_evidence'];assert set(p['faculties'])=={x.id for x in FACULTIES}
 tail_prev=prev
 for j in range(256):
  crc,cy,proto,rt=case(rng,a.cases+j,repeat=True);tail_prev=derive_functional_psyche(crc,cy,proto,previous=tail_prev,runtime_state=rt);af=tail_prev['affective_field'];signatures.add((af['label'],tail_prev['collapse_emergence']['summary']['high_collapse_count']>0,False,False,True))
 base=set(signatures)
 for i in range(a.tail):
  crc,cy,proto,rt=case(rng,a.cases+256+i,repeat=True);tail_prev=derive_functional_psyche(crc,cy,proto,previous=tail_prev,runtime_state=rt);af=tail_prev['affective_field'];signatures.add((af['label'],tail_prev['collapse_emergence']['summary']['high_collapse_count']>0,False,False,True))
 out={'schema':'ikant-psyche-stress/v0.5-test','status':'PASS','seed':a.seed,'cases':a.cases,'no_novelty_tail':a.tail,'scenario_signatures':len(base),'new_tail_signatures':len(signatures-base),'labels':labels,'max_collapse':round(max_collapse,6),'min_synthesis_trust':round(min_trust,6),'final_turns':tail_prev['epistemic_accumulation']['turns'],'elapsed_s':round(time.monotonic()-t,3)};assert out['new_tail_signatures']==0;print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
