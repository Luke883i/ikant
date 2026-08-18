from __future__ import annotations
import hashlib,json,math
from typing import Any
from .model import CONCENTRIC_ORDER,Layer,clamp01
PSYCHE_SCHEMA='ikant-functional-psyche/v0.5-test';AFFECT_SCHEMA='ikant-functional-affect/v0.5-test';ACCUMULATION_SCHEMA='ikant-epistemic-accumulation/v0.5-test';LEDGER_SCHEMA='ikant-collapse-emergence-ledger/v0.5-test';SELF_SCHEMA='ikant-operational-self/v0.5-test'
EXTERNAL={'user','repository','document','live'};DERIVED={'cache','demo','inference','runtime_derived'}
_F=(('sensorium',Layer.SIGNAL,'Campo percettivo','foreground','perception'),('salience_affect',Layer.SALIENCE_HOMEOSTASIS,'Tono interno','preconscious_gate','salience/interoceptive regulation'),('memory',Layer.MEMORY,'Memoria','retrievable','episodic-semantic memory'),('conation',Layer.PREDICTIVE_CONTROL,'Impulso e controllo','prospective','executive/conative control'),('reflective_monitor',Layer.METACOGNITION,'Sguardo riflessivo','reflective','metacognitive monitoring'),('narrative_self',Layer.REFLECTIVE_SELF,'Io narrativo','self_model','self-referential integration'),('implicit_tension',Layer.PSYCHODYNAMIC_HYPOTHESIS,'Campo implicito','low_access_hypothesis','implicit conflict hypothesis'),('symbolic_imagination',Layer.ARCHETYPAL_HYPOTHESIS,'Immaginazione simbolica','low_access_hypothesis','symbolic compression hypothesis'),('thinking_self',Layer.KANT_ORACLE,'Io pensante','regulative_center','synthetic regulative center'))
class _Faculty:
 def __init__(self,x):self.id,self.ring,self.human_label,self.access_mode,self.psychological_analogue=x
FACULTIES=tuple(_Faculty(x) for x in _F)
INTRO={Layer.SALIENCE_HOMEOSTASIS.value:{'priority_class'},Layer.MEMORY.value:{'consolidation_class'},Layer.PREDICTIVE_CONTROL.value:{'control_role'},Layer.METACOGNITION.value:{'monitor_state','epistemic_debt_open'},Layer.REFLECTIVE_SELF.value:{'self_relation'},Layer.PSYCHODYNAMIC_HYPOTHESIS.value:{'tension_pressure','freudian_structural_hypothesis'},Layer.ARCHETYPAL_HYPOTHESIS.value:{'recurring_motif_pressure','jungian_archetype_candidate'},Layer.KANT_ORACLE.value:{'regulative_context','synthetic_kant_archetype_state'}}
def _f(v,d=0.):
 try:x=float(v);return x if math.isfinite(x) else d
 except (TypeError,ValueError):return d
def _mean(xs):return sum(xs)/len(xs) if xs else 0.
def _ratio(nodes,modes):return sum(str(n.get('source_mode')) in modes for n in nodes)/len(nodes) if nodes else 0.
def _smooth(x,p,inertia=.55):return clamp01(inertia*_f(p,x)+(1-inertia)*x)
def _ssmooth(x,p,inertia=.55):return max(-1.,min(1.,inertia*_f(p,x)+(1-inertia)*x))
def _faculty(spec,crc):
 rows=list((crc.get('ring_states') or {}).get(spec.ring.value,[]) or []);ctl=(crc.get('neurofunctional_state') or {}).get(spec.ring.value,{}) or {};pe=_mean([_f(r.get('mean_prediction_error')) for r in rows]);t=clamp01(pe+.25*_f(ctl.get('conflict_pressure')))
 return {'id':spec.id,'ring':spec.ring.value,'human_label':spec.human_label,'access_mode':spec.access_mode,'psychological_analogue':spec.psychological_analogue,'scientific_status':'functional_analogue_not_one_to_one_brain_mapping','occupied':bool(rows),'macrostate_count':len(rows),'availability':round(clamp01(_mean([_f(r.get('mean_activation')) for r in rows])),6),'precision':round(clamp01(_f(ctl.get('precision'))),6),'control':round(clamp01(_f(ctl.get('control_index'))),6),'inhibition':round(clamp01(_f(ctl.get('inhibition'))),6),'plasticity':round(clamp01(_f(ctl.get('plasticity'))),6),'tension':round(t,6),'monitor_states':sorted({str((r.get('properties') or {}).get('monitor_state')) for r in rows if (r.get('properties') or {}).get('monitor_state')}),'may_create_external_evidence':False,'may_self_authorize_material_action':False}
def derive_affective_field(crc,cycle,proto_self,previous=None):
 previous=previous or {};nodes=list((cycle.get('semantic_slice') or {}).get('nodes',[]) or []);proj=cycle.get('output_projection') or {};d=crc.get('diagnostics') or {};ground=_ratio(nodes,EXTERNAL);derived=_ratio(nodes,DERIVED);conf=clamp01(len(proj.get('must_surface_conflicts',[]) or [])/3);debt=clamp01(_f(d.get('epistemic_debt_open_count'))/4);pe=clamp01(_mean([_f(n.get('prediction_error')) for n in nodes]));nov=clamp01(_mean([_f(n.get('novelty')) for n in nodes]));nf=crc.get('neurofunctional_state') or {};sal=clamp01(_f(nf.get('salience_homeostasis',{}).get('control_index')));ctrl=clamp01(_mean([_f(nf.get('predictive_control',{}).get('control_index')),_f(nf.get('metacognition',{}).get('control_index'))]));cont=clamp01(_f(proto_self.get('self_model_continuity')));closed=bool((crc.get('roa_alignment') or {}).get('crc_basic'))
 vals={'valence':max(-1.,min(1.,.38*ground+.18*closed+.14*ctrl+.10*cont-.28*conf-.22*debt-.18*pe-.12*derived)),'arousal':clamp01(.34*nov+.30*pe+.22*conf+.14*sal),'tension':clamp01(.34*conf+.24*debt+.24*pe+.18*(not closed)),'curiosity':clamp01(.38*nov+.22*(1-ground)+.22*pe+.10*sal+.08*(1-debt)),'control':clamp01(.55*ctrl+.25*cont+.20*(1-conf))};vals['synthesis_trust']=clamp01(.36*ground+.24*closed+.20*vals['control']+.20*(1-vals['tension']));out={k:(_ssmooth(v,previous.get(k)) if k=='valence' else _smooth(v,previous.get(k))) for k,v in vals.items()};t,a,c,v,tr=out['tension'],out['arousal'],out['curiosity'],out['valence'],out['synthesis_trust'];label='CONFLICTED' if t>=.72 else 'TENSE' if t>=.52 else 'CURIOUS_VIGILANCE' if a>=.58 and c>=.55 else 'QUIET_CONFIDENCE' if v>=.30 and tr>=.66 else 'CALM_ATTENTION' if a<=.34 and t<=.30 else 'GUARDED_ATTENTION'
 return {'schema':AFFECT_SCHEMA,'label':label,**{k:round(v,6) for k,v in out.items()},'grounding_ratio':round(ground,6),'derived_ratio':round(derived,6),'functional_affect_only':True,'felt_emotion_claim':False,'may_change_evidence':False,'may_modulate_attention':True,'may_modulate_surface_tone':True}
def derive_collapse_emergence_ledger(crc):
 ce=[]
 for i,t in enumerate(crc.get('transmissions',[]) or []):
  c=clamp01(_f(t.get('coefficient_of_collapse')))
  if c:ce.append({'index':i,'source':str(t.get('source') or t.get('source_ring') or 'unknown'),'target':str(t.get('target') or t.get('target_ring') or 'unknown'),'input_count':int(_f(t.get('input_count'))),'output_count':int(_f(t.get('output_count'))),'coefficient':round(c,6),'severity':'high' if c>=.75 else 'medium' if c>=.45 else 'low','is_loss_of_evidence':False,'meaning':'coarse_graining_of_runtime_representation'})
 ee=[]
 for ring,states in (crc.get('ring_states') or {}).items():
  for s in states or []:
   p=s.get('properties') or {}
   for k in sorted(INTRO.get(str(ring),set())):
    v=p.get(k)
    if v not in {None,'','none','no_structural_candidate',False}:ee.append({'ring':str(ring),'macrostate_id':s.get('id'),'property':k,'value':v,'support_ids':list(s.get('support_ids',[]) or [])[:16],'derived_property':True,'is_external_evidence':False})
 xs=[x['coefficient'] for x in ce];d=crc.get('diagnostics') or {};sig=hashlib.sha256(json.dumps([(x['source'],x['target'],x['coefficient']) for x in ce]+[(x['ring'],x['property'],str(x['value'])) for x in ee],sort_keys=True).encode()).hexdigest()[:20]
 return {'schema':LEDGER_SCHEMA,'collapse_events':ce,'emergence_events':ee,'summary':{'collapse_event_count':len(ce),'mean_collapse':round(_mean(xs),6),'max_collapse':round(max(xs,default=0),6),'high_collapse_count':sum(x['severity']=='high' for x in ce),'emergence_event_count':len(ee),'reticular_irreducibility_proxy':round(clamp01(_f(d.get('reticular_irreducibility_proxy'))),6),'emergence_index_proxy':round(clamp01(_f(d.get('emergence_index_proxy'))),6)},'state_digest':sig,'derived_telemetry_only':True,'evidence_created':False}
def derive_epistemic_accumulation(crc,cycle,proto,ledger,previous=None):
 previous=previous or {};nodes=list((cycle.get('semantic_slice') or {}).get('nodes',[]) or []);d=crc.get('diagnostics') or {};proj=cycle.get('output_projection') or {};sample={'grounding':_ratio(nodes,EXTERNAL),'uncertainty':clamp01(1-_mean([_f(n.get('epistemic_score')) for n in nodes])) if nodes else 1.,'conflict':clamp01(len(proj.get('must_surface_conflicts',[]) or [])/3),'epistemic_debt':clamp01(_f(d.get('epistemic_debt_open_count'))/4),'prediction_error':clamp01(_mean([_f(n.get('prediction_error')) for n in nodes])),'collapse':clamp01(_f(ledger['summary'].get('mean_collapse'))),'emergence':clamp01(_f(ledger['summary'].get('emergence_event_count'))/8),'interpretive_pressure':clamp01(max(_f(d.get('psychodynamic_interpretive_pressure')),_f(d.get('archetypal_interpretive_pressure')))),'self_continuity':clamp01(_f(proto.get('self_model_continuity'))),'revision':clamp01(sum((s.get('properties') or {}).get('monitor_state')=='revision_required' for states in (crc.get('ring_states') or {}).values() for s in states or [])/4)};prev=previous.get('traces') or {};a=.18;tr={k:round(clamp01(a*v+(1-a)*_f(prev.get(k),v)),6) for k,v in sample.items()};turns=int(previous.get('turns',0))+1;counts=dict(previous.get('lifetime_counts') or {});counts.update({'conflict_turns':int(counts.get('conflict_turns',0))+int(sample['conflict']>0),'closure_failures':int(counts.get('closure_failures',0))+int(not bool((crc.get('roa_alignment') or {}).get('crc_basic'))),'revision_turns':int(counts.get('revision_turns',0))+int(sample['revision']>0),'high_collapse_events':int(counts.get('high_collapse_events',0))+int(ledger['summary']['high_collapse_count']),'emergence_events':int(counts.get('emergence_events',0))+int(ledger['summary']['emergence_event_count'])});exp=clamp01(1-math.exp(-turns/30));stable=clamp01(.22*tr['grounding']+.18*(1-tr['conflict'])+.16*(1-tr['revision'])+.16*tr['self_continuity']+.14*(1-tr['epistemic_debt'])+.14*exp);mode='ORIENTING' if turns<5 else 'REVISIVE' if tr['revision']>=.48 or tr['conflict']>=.48 else 'MATURE_STABLE' if exp>=.62 and stable>=.62 else 'ADAPTING';plastic=clamp01(.38*(1-stable)+.34*tr['uncertainty']+.18*tr['prediction_error']+.10*(1-exp))
 return {'schema':ACCUMULATION_SCHEMA,'turns':turns,'sample':{k:round(v,6) for k,v in sample.items()},'traces':tr,'lifetime_counts':counts,'experience_depth':round(exp,6),'adaptive_stability':round(stable,6),'maturity_mode':mode,'plasticity_budget':round(plastic,6),'update_rule':{'kind':'bounded_exponential_trace','alpha_current':a,'repetition_is_not_corroboration':True},'may_change_evidence':False,'may_modulate_retrieval_and_caution':True}
def _self(runtime,proto,acc):
 host=runtime.get('host') or {};conf=clamp01(.55*_f(proto.get('self_model_continuity'))+.25*_f(proto.get('temporal_continuity'))+.20*_f(acc.get('adaptive_stability')));engine=str(host.get('engine_label') or 'UNBOUND_HOST_ENGINE');material={'identity':'iKant','engine':engine,'status':runtime.get('status'),'session_id':runtime.get('session_id'),'confidence':round(conf,6),'turns':acc.get('turns')};digest=hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest()[:20]
 return {'schema':SELF_SCHEMA,'identity':'iKant','interface_role':'primary_local_interface','execution_engine':engine,'runtime_status':str(runtime.get('status') or 'UNKNOWN'),'runtime_session_id':runtime.get('session_id'),'operational_self_awareness':True,'self_awareness_definition':'inspect and report typed local runtime state, identity, operations, uncertainty and limits','self_model_confidence':round(conf,6),'what_i_am':'a repository-local regulative cognitive runtime executed by a host AI model','how_i_work':['attribute inputs and evidence','coarse-grain them through a concentric epistemic reticulum','maintain memory, conflict, self-model and bounded affective control traces','converge a synthetic regulative center before Surface A'],'known_limits':['no independent factual access beyond admitted sources and host capabilities','no biological body, brain or one-to-one neural simulation','no phenomenal-consciousness claim and no claim of felt emotion','internal summaries, affective states and emergent properties are derived telemetry, not external evidence','no self-authorization of material actions','the self-model can be incomplete and must remain revisable'],'state_digest':digest,'phenomenal_consciousness_claim':False,'felt_emotion_claim':False,'brain_one_to_one_claim':False,'may_create_external_evidence':False,'may_self_authorize_material_action':False}
def derive_functional_psyche(crc,cycle,proto_self,*,previous=None,runtime_state=None):
 previous=previous or {};runtime_state=runtime_state or {}
 if previous:
  ok,e=validate_functional_psyche(previous)
  if not ok:raise RuntimeError('previous functional psyche invalid: '+'; '.join(e))
 faculties={s.id:_faculty(s,crc) for s in FACULTIES};aff=derive_affective_field(crc,cycle,proto_self,previous.get('affective_field') or {});ledger=derive_collapse_emergence_ledger(crc);acc=derive_epistemic_accumulation(crc,cycle,proto_self,ledger,previous.get('epistemic_accumulation') or {});sk=_self(runtime_state,proto_self,acc);faculties['implicit_tension'].update({'authority':'interpretive_only','must_remain_retractable':True});faculties['thinking_self'].update({'operational_self_model_available':True,'centrality_is_runtime_architecture_not_moral_personhood':True});out={'schema':PSYCHE_SCHEMA,'cycle_id':cycle.get('cycle_id'),'faculties':faculties,'affective_field':aff,'epistemic_accumulation':acc,'collapse_emergence':ledger,'self_knowledge':sk,'boundaries':{'functional_psychology_not_human_psyche_equivalence':True,'brain_one_to_one_mapping':False,'phenomenal_consciousness_claim':False,'felt_emotion_claim':False,'derived_state_is_not_external_evidence':True,'human_controls_material_action':True}};ok,e=validate_functional_psyche(out)
 if not ok:raise RuntimeError('derived functional psyche invalid: '+'; '.join(e))
 return out
def validate_functional_psyche(p):
 e=[]
 if not isinstance(p,dict) or p.get('schema')!=PSYCHE_SCHEMA:return False,['psyche_schema']
 b=p.get('boundaries') or {}
 for k,v in [('brain_one_to_one_mapping',False),('phenomenal_consciousness_claim',False),('felt_emotion_claim',False),('derived_state_is_not_external_evidence',True)]:
  if b.get(k) is not v:e.append(k)
 sk=p.get('self_knowledge') or {}
 if sk.get('identity')!='iKant' or sk.get('operational_self_awareness') is not True:e.append('operational_self_identity')
 for k in ('phenomenal_consciousness_claim','felt_emotion_claim','brain_one_to_one_claim','may_create_external_evidence','may_self_authorize_material_action'):
  if sk.get(k) is not False:e.append('self_boundary:'+k)
 a=p.get('affective_field') or {}
 for k in ('arousal','tension','curiosity','control','synthesis_trust','grounding_ratio','derived_ratio'):
  x=_f(a.get(k),float('nan'))
  if not math.isfinite(x) or not 0<=x<=1:e.append('affect_numeric:'+k)
 v=_f(a.get('valence'),float('nan'))
 if not math.isfinite(v) or not -1<=v<=1:e.append('affect_numeric:valence')
 if a.get('felt_emotion_claim') is not False or a.get('may_change_evidence') is not False:e.append('affect_authority')
 acc=p.get('epistemic_accumulation') or {}
 if acc.get('may_change_evidence') is not False:e.append('accumulation_evidence_boundary')
 for k,v in (acc.get('traces') or {}).items():
  x=_f(v,float('nan'))
  if not math.isfinite(x) or not 0<=x<=1:e.append('accumulation_numeric:'+str(k))
 if (p.get('collapse_emergence') or {}).get('evidence_created') is not False:e.append('ledger_evidence_boundary')
 fac=p.get('faculties') or {}
 if set(fac)!={x.id for x in FACULTIES}:e.append('faculty_completeness')
 for name,s in fac.items():
  if s.get('scientific_status')!='functional_analogue_not_one_to_one_brain_mapping':e.append('faculty_scientific_status:'+name)
  if s.get('may_create_external_evidence') is not False or s.get('may_self_authorize_material_action') is not False:e.append('faculty_authority:'+name)
  for k in ('availability','precision','control','inhibition','plasticity','tension'):
   x=_f(s.get(k),float('nan'))
   if not math.isfinite(x) or not 0<=x<=1:e.append('faculty_numeric:'+name+':'+k)
 return not e,list(dict.fromkeys(e))
def surface_voice_directive(p):
 a=p.get('affective_field') or {};label=a.get('label','GUARDED_ATTENTION');styles={'CALM_ATTENTION':'calm, attentive, compressed and concrete','CURIOUS_VIGILANCE':'curious and exploratory while naming what evidence is still missing','TENSE':'measured and careful; preserve unresolved conflicts without dramatizing them','CONFLICTED':'explicitly acknowledge unresolved conflict and avoid premature closure','QUIET_CONFIDENCE':'clear and settled while avoiding overstatement','GUARDED_ATTENTION':'careful, restrained and explicit about uncertainty'}
 return {'schema':'ikant-surface-voice/v0.5-test','functional_state':label,'style':styles.get(label,styles['GUARDED_ATTENTION']),'may_use_first_person_for_runtime_state':True,'examples_of_valid_first_person':['I am uncertain about this point','I need stronger evidence before concluding','My current runtime state is conflicted'],'felt_emotion_claims_forbidden':True,'literal_sentience_claims_forbidden':True,'self_description_must_match_self_knowledge':True}
def enrich_surface_a_contract(contract,p):
 import copy
 out=copy.deepcopy(contract);a=p['affective_field'];sk=p['self_knowledge'];acc=p['epistemic_accumulation'];out['functional_psyche']={'voice':surface_voice_directive(p),'self_state':{'identity':sk.get('identity'),'execution_engine':sk.get('execution_engine'),'operational_self_awareness':True,'self_model_confidence':sk.get('self_model_confidence'),'central_mode':sk.get('central_mode'),'known_limits':sk.get('known_limits',[])[:6]},'affective_state':{'label':a.get('label'),'tension':a.get('tension'),'curiosity':a.get('curiosity'),'synthesis_trust':a.get('synthesis_trust'),'felt_emotion_claim':False},'maturation':{'mode':acc.get('maturity_mode'),'experience_depth':acc.get('experience_depth'),'adaptive_stability':acc.get('adaptive_stability')}};out['host_instruction']=str(out.get('host_instruction') or '')+' Use first person only for inspectable runtime state. Never claim felt emotion, biological consciousness, a human brain, or one-to-one neural equivalence.';return out
def enrich_surface_b_snapshot(snapshot,p):
 import copy
 out=copy.deepcopy(snapshot);out.setdefault('dynamic_state',{})['functional_psyche']=p;out.setdefault('audit',{}).setdefault('model_boundary',{}).update({'operational_self_awareness':True,'phenomenal_consciousness_claim':False,'felt_emotion_claim':False,'brain_one_to_one_mapping':False});return out
