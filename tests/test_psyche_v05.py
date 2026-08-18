import math,tempfile,unittest
from pathlib import Path
from ikant.dashboard_v05 import project_dashboard,render_dashboard_ascii
from ikant.psyche import FACULTIES,PSYCHE_SCHEMA,derive_functional_psyche,validate_functional_psyche
from ikant.self_regulation import regulate_central_with_psyche

def fixture(*,conflict=0,debt=0,pe=.18,novelty=.35,grounding=.75,collapse=.25,closure=True,turn=1):
 src=['document']*int(round(8*grounding))+['inference']*(8-int(round(8*grounding)));nodes=[{'id':f'N{i}','source_mode':s,'epistemic_score':.72 if s=='document' else .32,'prediction_error':pe,'novelty':novelty} for i,s in enumerate(src)];conflicts=[{'source':f'N{i}','target':f'N{(i+1)%8}','kind':'contradicts'} for i in range(conflict)];rings=['signal','salience_homeostasis','memory','predictive_control','metacognition','reflective_self','psychodynamic_hypothesis','archetypal_hypothesis','kant_oracle'];props={'signal':{},'salience_homeostasis':{'priority_class':'foreground'},'memory':{'consolidation_class':'recent'},'predictive_control':{'control_role':'world_model'},'metacognition':{'monitor_state':'revision_required' if pe>.55 else 'coherent','epistemic_debt_open':bool(debt)},'reflective_self':{'self_relation':'explicit_self'},'psychodynamic_hypothesis':{'tension_pressure':'elevated' if conflict else 'low','freudian_structural_hypothesis':'unresolved_tension' if conflict else 'ego_mediation_candidate'},'archetypal_hypothesis':{'recurring_motif_pressure':'recurring','jungian_archetype_candidate':'self_candidate'},'kant_oracle':{'regulative_context':'synthesis','synthetic_kant_archetype_state':'reflective_synthesis'}};ring_states={};neuro={}
 for i,r in enumerate(rings):ring_states[r]=[{'id':f'M{i}','support_ids':['N0','N1'],'mean_activation':.38+.02*i,'mean_prediction_error':pe,'properties':props[r]}];neuro[r]={'precision':.68,'control_index':.62,'inhibition':.24,'plasticity':.42,'conflict_pressure':min(1,conflict/3)}
 tx=[{'source':rings[i],'target':rings[i+1],'input_count':4,'output_count':max(1,round(4*(1-collapse))),'coefficient_of_collapse':collapse} for i in range(8)];crc={'ring_states':ring_states,'neurofunctional_state':neuro,'transmissions':tx,'roa_alignment':{'crc_basic':closure},'diagnostics':{'epistemic_debt_open_count':debt,'reticular_irreducibility_proxy':.41,'emergence_index_proxy':.37,'psychodynamic_interpretive_pressure':.25 if conflict else .08,'archetypal_interpretive_pressure':.18}};cycle={'cycle_id':f'CYC-{turn}','semantic_slice':{'nodes':nodes},'output_projection':{'must_surface_conflicts':conflicts}};proto={'self_model_continuity':.72,'temporal_continuity':.76,'proto_self_index':.68};runtime={'status':'ACTIVE','session_id':'SES-X','host':{'engine_label':'GPT-5.6 Sol'}};return crc,cycle,proto,runtime

class PsycheV05Tests(unittest.TestCase):
 def psyche(self,**kw):
  c,y,p,r=fixture(**kw);return derive_functional_psyche(c,y,p,runtime_state=r)
 def test_self_is_complete_but_not_sentience(self):
  p=self.psyche();self.assertEqual(p['schema'],PSYCHE_SCHEMA);self.assertEqual(set(p['faculties']),{x.id for x in FACULTIES});self.assertTrue(p['self_knowledge']['operational_self_awareness']);self.assertFalse(p['self_knowledge']['phenomenal_consciousness_claim']);self.assertFalse(p['boundaries']['brain_one_to_one_mapping']);self.assertTrue(validate_functional_psyche(p)[0])
 def test_conflict_debt_raise_tension_and_lower_trust(self):
  a=self.psyche(conflict=0,debt=0,pe=.05,grounding=1);b=self.psyche(conflict=3,debt=4,pe=.9,grounding=.2,closure=False);self.assertGreater(b['affective_field']['tension'],a['affective_field']['tension']);self.assertLess(b['affective_field']['synthesis_trust'],a['affective_field']['synthesis_trust'])
 def test_accumulation_is_bounded_revisable_and_not_corroboration(self):
  c,y,p,r=fixture(conflict=0,debt=0,pe=.05,grounding=1);state=None
  for i in range(120):state=derive_functional_psyche(c,{**y,'cycle_id':f'S{i}'},p,previous=state,runtime_state=r)
  self.assertTrue(all(0<=x<=1 for x in state['epistemic_accumulation']['traces'].values()));self.assertTrue(state['epistemic_accumulation']['update_rule']['repetition_is_not_corroboration']);bad=fixture(conflict=3,debt=4,pe=.95,grounding=.1,closure=False)
  for i in range(20):state=derive_functional_psyche(bad[0],{**bad[1],'cycle_id':f'R{i}'},bad[2],previous=state,runtime_state=bad[3])
  self.assertEqual(state['epistemic_accumulation']['maturity_mode'],'REVISIVE');self.assertFalse(state['epistemic_accumulation']['may_change_evidence'])
 def test_collapse_emergence_are_derived_only(self):
  p=self.psyche(collapse=.8);l=p['collapse_emergence'];self.assertEqual(l['summary']['high_collapse_count'],8);self.assertGreaterEqual(l['summary']['emergence_event_count'],8);self.assertFalse(l['evidence_created']);self.assertTrue(all(not x['is_external_evidence'] for x in l['emergence_events']))
 def test_invalid_previous_state_fails_closed(self):
  p=self.psyche();p['boundaries']['phenomenal_consciousness_claim']=True;c,y,proto,r=fixture()
  with self.assertRaises(RuntimeError):derive_functional_psyche(c,y,proto,previous=p,runtime_state=r)
 def test_extremes_remain_finite(self):
  p=self.psyche(conflict=30,debt=50,pe=999,novelty=999,grounding=0,collapse=999,closure=False);self.assertTrue(validate_functional_psyche(p)[0]);self.assertTrue(all(math.isfinite(x) for x in p['epistemic_accumulation']['traces'].values()))
 def test_implicit_field_has_no_authority(self):
  s=self.psyche(conflict=2)['faculties']['implicit_tension'];self.assertEqual(s['authority'],'interpretive_only');self.assertFalse(s['may_create_external_evidence']);self.assertFalse(s['may_self_authorize_material_action'])
 def test_regulator_never_relaxes_blocks(self):
  p=self.psyche(conflict=3,debt=4,pe=.9,grounding=.1,closure=False)
  for mode in ('PRACTICAL_BLOCK','HORIZON_BLOCK'):
   c={'regulative_mode':mode,'unity_index':.7,'critique_pressure':.2,'dispositions':[],'authority':{'may_create_external_evidence':False}};o=regulate_central_with_psyche(c,p);self.assertEqual(o['regulative_mode'],mode);self.assertFalse(o['functional_psyche_regulation']['evidence_modified'])
 def test_dashboard_uses_humanistic_non_evidential_grammar(self):
  class RT:pass
  with tempfile.TemporaryDirectory() as td:
   rt=RT();rt.state_dir=Path(td)/'.ikant';rt.state_dir.mkdir();p=self.psyche(conflict=1,debt=1,pe=.4);p['self_knowledge']['central_mode']='REFLECTIVE_SYNTHESIS';rt.runtime={'status':'ACTIVE','session_id':'SES-X','cognitive':{'psyche':p}};d=project_dashboard(rt);self.assertFalse(d['contract']['psyche_may_modify_evidence'])
   for w in (80,96,120):self.assertTrue(all(len(line)<=w for line in render_dashboard_ascii(d,width=w).splitlines()))
if __name__=='__main__':unittest.main()
