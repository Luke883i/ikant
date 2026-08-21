from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids,registry_manifest
from ikant.product_experience import PRODUCT_EXPERIENCE_SCHEMA,PRODUCT_VOICE_SCHEMA
ROOT=Path(__file__).parents[1]

class ProductConvergenceV27Tests(unittest.TestCase):
 def test_v27_identity_converges(self):
  self.assertEqual(PRODUCT_VERSION,'0.27.0a1');self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(registry_manifest()['product_version'],PRODUCT_VERSION);self.assertEqual(INVARIANT_REGISTRY_SCHEMA,'ikant-invariant-registry/v0.27-test')
 def test_s9_is_current_registered_slice(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual(c['schema'],'ikant-product-contract/v0.27-test');self.assertEqual([x['id'] for x in c['slices']],['S1','S2','S3','S4','S5','S6','S7','S8','S9']);self.assertEqual(c['constitutional_convergence'],'S9');s=c['slices'][-1];self.assertEqual(s['schema'],PRODUCT_EXPERIENCE_SCHEMA);self.assertEqual(set(s['invariants']),{'EXP-001','EXP-002','EXP-003','EXP-004'});self.assertEqual(s['saturation'],{'cases':10000000,'mutations':10000000,'edges':100000,'tail':1000,'seed':883});self.assertEqual(s['evidence']['minimality_architectures'],262144);self.assertEqual(s['evidence']['diversified_seed_fanout'],16)
 def test_product_experience_invariants_are_constitutional(self):
  self.assertEqual(PRODUCT_EXPERIENCE_SCHEMA,'ikant-product-experience/v0.27-test');self.assertEqual(PRODUCT_VOICE_SCHEMA,'ikant-product-voice-candidate/v0.27-test');self.assertTrue({'EXP-001','EXP-002','EXP-003','EXP-004'}<=set(critical_ids()))
 def test_manifests_expose_experience_noncollapse(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));x=m['product_experience'];self.assertEqual(x['schema'],PRODUCT_EXPERIENCE_SCHEMA);self.assertTrue(x['setup_visible_before_model_ready']);self.assertFalse(x['browser_may_mark_ready']);self.assertTrue(x['single_semantic_viewport']);self.assertTrue(x['progressive_disclosure']);self.assertTrue(x['traditional_controls_on_demand']);self.assertFalse(x['remote_frontend_dependencies']);self.assertFalse(x['browser_model_transport']);self.assertFalse(x['voice_input_auto_submit']);self.assertFalse(x['voice_input_is_approval']);self.assertTrue(x['voice_output_requires_local_service']);self.assertTrue(x['voice_output_requires_post_ack_turn']);self.assertFalse(x['diagnostics_are_authority']);self.assertEqual(x['epistemic_authority'],0.0);self.assertEqual(x['execution_authority'],0.0)
 def test_canonical_product_workspace_is_local_chat_first_and_progressive(self):
  html=(ROOT/'ikant/web/index.html').read_text(encoding='utf-8');js=(ROOT/'ikant/web/app.js').read_text(encoding='utf-8');css=(ROOT/'ikant/web/styles.css').read_text(encoding='utf-8');app=(ROOT/'ikant/local_app.py').read_text(encoding='utf-8');self.assertEqual(html.count('id="dashboard"'),1);self.assertIn('command-palette',html);self.assertIn('inspector',html);self.assertIn('setup-panel',html);self.assertIn('orbit-rail',html);self.assertNotIn('https://',html);self.assertNotIn('https://',css);self.assertIn('prefers-reduced-motion',css);self.assertIn('ProductBootstrapCoordinator',app);self.assertIn('/api/v3/product/status',js);self.assertIn('localService===true',js);self.assertIn('processLocally:true',js);self.assertTrue((ROOT/'docs'/'S9_PRODUCT_EXPERIENCE.md').is_file())
if __name__=='__main__':unittest.main()
