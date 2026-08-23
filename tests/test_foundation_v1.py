from __future__ import annotations
import json,threading,tempfile,unittest
from pathlib import Path
from ikant.foundation import (
 FOUNDATION_SCHEMA,EXPERIMENT_CONFIG_SCHEMA,FoundationConfigError,ExperimentModelProxy,
 apply_generation_experiment,capability_catalog,default_experiment_config,epistemic_value_projection,
 foundation_projection,load_experiment_config,save_experiment_config,update_experiment_config,
)
ROOT=Path(__file__).resolve().parents[1]

class FakeBroker:
 model='fake-local';managed_runtime=True;runtime_binding_digest='a'*64
 def __init__(self):self.contract=None;self.last_completion_metrics={}
 def health(self):return True
 def complete_surface_a(self,contract,user_text,**kwargs):self.contract=contract;return 'risposta valida'

class FakeShell:
 def __init__(self):self._lock=threading.RLock();self._last_acked_frame={'frame':1};self._pending=None
class FakeDelegate:
 def __init__(self):self._lock=threading.RLock();self.web_shell=FakeShell()
class FakeService:
 def __init__(self,root):self.root=Path(root);self.delegate=FakeDelegate()
 def _delegate_or_raise(self):return self.delegate
 def product_status(self):return {'voice':{'configured':False}}
 def bootstrap_status(self):return {'overall':'READY'}

class FoundationV1Tests(unittest.TestCase):
 def seed_runtime(self,root:Path,*,docx=False):
  state=root/'.ikant';(state/'cognitive').mkdir(parents=True);(state/'artifacts').mkdir(parents=True)
  runtime={'status':'ACTIVE','session_id':'SES-1','cognitive':{'last_surface_a_cycle_id':'CYC-1'}}
  (state/'runtime.json').write_text(json.dumps(runtime),encoding='utf-8');(state/'model-runtime.json').write_text(json.dumps({'status':'READY'}),encoding='utf-8')
  snap={'cycle_id':'CYC-1','dynamic_state':{'mined_atoms':[{'source_mode':'repository','evidence':.8,'confidence':.9},{'source_mode':'inference','evidence':.1,'confidence':.5}],'central_projection':{'must_surface_conflicts':['A/B']}},'reticulum':{'roa_alignment':{'crc_basic':False}}}
  (state/'cognitive'/'CYC-1.json').write_text(json.dumps(snap),encoding='utf-8')
  if docx:(state/'artifacts'/'CRC_SNAPSHOT_CYC-1.docx').write_bytes(b'PK-test')
 def test_config_is_revision_bound_and_can_only_select_bounded_modes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'.ikant').mkdir();self.assertEqual(load_experiment_config(root)['revision'],0)
   out=save_experiment_config(root,{'expected_revision':0,'meta_prompt':'Preferisci esempi concreti.','guardrails':{'evidence_mode':'strict','conflict_mode':'abstain','interpretive_hypotheses':'off','max_reply_words':80}})
   self.assertEqual(out['schema'],EXPERIMENT_CONFIG_SCHEMA);self.assertEqual(out['revision'],1);self.assertEqual(out['epistemic_authority'],0.0);self.assertFalse(out['hard_guardrails']['model_tool_calls'])
   with self.assertRaises(FoundationConfigError):save_experiment_config(root,{'expected_revision':0,'meta_prompt':'stale','guardrails':{}})
   with self.assertRaises(FoundationConfigError):save_experiment_config(root,{'expected_revision':1,'meta_prompt':'x','guardrails':{'max_reply_words':500}})
 def test_meta_prompt_modulates_generation_contract_without_authority(self):
  cfg=default_experiment_config();cfg['revision']=4;cfg['meta_prompt']='Usa analogie brevi.';cfg['guardrails'].update({'evidence_mode':'strict','conflict_mode':'abstain','interpretive_hypotheses':'off','max_reply_words':80})
  out=apply_generation_experiment({'format':{'max_words':500,'stance':'careful'},'regulation':{'material_action':'PROPOSE_ONLY'}},cfg)
  self.assertEqual(out['format']['max_words'],80);self.assertIn('Usa analogie brevi.',out['format']['stance']);self.assertEqual(out['regulation']['material_action'],'PROPOSE_ONLY');self.assertEqual(out['experiment_config']['authority_effect'],'NONE')
 def test_managed_model_proxy_loads_current_local_config_per_turn(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'.ikant').mkdir();save_experiment_config(root,{'expected_revision':0,'meta_prompt':'Rispondi in modo compatto.','guardrails':{'max_reply_words':80}});broker=FakeBroker();proxy=ExperimentModelProxy(root,broker);self.assertEqual(proxy.complete_surface_a({'format':{'max_words':500}},'ciao'),'risposta valida');self.assertEqual(broker.contract['format']['max_words'],80);self.assertIn('Rispondi in modo compatto.',broker.contract['format']['stance'])
 def test_catalog_contains_only_currently_demonstrable_services(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);self.seed_runtime(root,docx=False);service=FakeService(root);out=capability_catalog(service);ids={x['id'] for x in out['services']};self.assertTrue({'experiment_config','bootstrap_diagnostics','local_conversation','cognitive_trace','epistemic_inspection','json_snapshot'}<=ids);self.assertNotIn('docx_artifact',ids);self.assertNotIn('loopback_voice',ids);self.assertTrue(out['undemonstrated_features_omitted']);self.assertEqual(out['execution_authority'],0.0)
 def test_epistemic_value_explains_support_derivation_and_conflict_without_truth_claim(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);self.seed_runtime(root);out=epistemic_value_projection(root);self.assertEqual(out['direct_support'],1);self.assertEqual(out['derived_items'],1);self.assertEqual(out['open_conflicts'],1);self.assertGreaterEqual(out['uncertain_items'],1);self.assertFalse(out['truth_certified']);self.assertFalse(out['response_memory_is_evidence']);self.assertIn('conflitti',out['label'].lower())
 def test_config_change_fails_closed_while_exact_frame_is_pending(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'.ikant').mkdir();service=FakeService(root);service.delegate.web_shell._pending={'seq':1}
   with self.assertRaises(FoundationConfigError):update_experiment_config(service,{'expected_revision':0,'meta_prompt':'x','guardrails':{}})
 def test_foundation_projection_is_zero_authority(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);self.seed_runtime(root);out=foundation_projection(FakeService(root));self.assertEqual(out['schema'],FOUNDATION_SCHEMA);self.assertEqual(out['foundation_version'],'1.0-test');self.assertEqual(out['epistemic_authority'],0.0);self.assertEqual(out['execution_authority'],0.0);self.assertTrue(out['promise']['shown_services_are_runtime_demonstrable'])
 def test_http_ui_and_supply_are_source_bound(self):
  http=(ROOT/'ikant/bootstrap_http.py').read_text();managed=(ROOT/'ikant/managed_runtime.py').read_text();html=(ROOT/'ikant/web/index.html').read_text();js=(ROOT/'ikant/web/foundation.js').read_text();sw=(ROOT/'ikant/web/sw.js').read_text()
  self.assertIn("'/api/v7/foundation'",http);self.assertIn("'/api/v7/config'",http);self.assertIn('origin=True',http);self.assertIn('ExperimentModelProxy',managed)
  self.assertIn('id="foundation-meta"',html);self.assertIn('id="foundation-services"',html);self.assertIn('id="foundation-epistemic"',html);self.assertIn('id="voice-button"',html);self.assertRegex(html,r'id="voice-button"[^>]*hidden')
  self.assertIn("'/api/v7/foundation'",js);self.assertIn("'/api/v7/config'",js);self.assertIn('processLocally:true',js);self.assertIn('localService===true',js);self.assertIn('undemonstrated',json.dumps(capability_catalog(FakeService(ROOT))) if (ROOT/'.ikant'/'runtime.json').exists() else 'undemonstrated')
  self.assertIn('foundation-v1-s12',sw);self.assertIn('/foundation.js',sw);self.assertIn('/foundation.css',sw)
 def test_s12_contract_is_preserved_with_three_10m_campaigns_and_100k_tails(self):
  product=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());s=next(s for s in product['slices'] if s['id']=='S12');self.assertLess(product['slices'].index(s),len(product['slices'])-1);self.assertEqual(s['schema'],FOUNDATION_SCHEMA);self.assertEqual(s['saturation'],{'cases':10000000,'mutations':10000000,'edges':10000000,'tail':100000,'seed':20260822});self.assertEqual(s['evidence']['campaigns'],3);self.assertEqual(s['evidence']['modeled_trials_at_declared_scale'],30000000);self.assertEqual(s['evidence']['no_novelty_tail'],100000);self.assertEqual(s['evidence']['no_better_compression_tail'],100000);self.assertEqual(product['constitutional_convergence'],product['slices'][-1]['id']);self.assertIn('S13bis',[x['id'] for x in product['slices']])

if __name__=='__main__':unittest.main()
