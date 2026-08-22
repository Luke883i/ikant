from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant.invariants import critical_ids
from ikant.product_experience import PRODUCT_EXPERIENCE_SCHEMA,PRODUCT_VOICE_SCHEMA
ROOT=Path(__file__).parents[1]
class ProductConvergenceV27Tests(unittest.TestCase):
 def test_s9_remains_historical_registered_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));ids=[x['id'] for x in c['slices']];self.assertEqual(ids[:9],['S1','S2','S3','S4','S5','S6','S7','S8','S9']);s=c['slices'][8];self.assertEqual(s['schema'],PRODUCT_EXPERIENCE_SCHEMA);self.assertEqual(set(s['invariants']),{'EXP-001','EXP-002','EXP-003','EXP-004'});self.assertEqual(s['historical_saturation'],{'cases':10000000,'mutations':10000000,'edges':100000,'tail':1000,'seed':883});self.assertEqual(s['historical_evidence']['minimality_architectures'],262144);self.assertEqual(s['historical_evidence']['diversified_seed_fanout'],16)
 def test_product_experience_invariants_remain_constitutional(self):
  self.assertEqual(PRODUCT_EXPERIENCE_SCHEMA,'ikant-product-experience/v0.27-test');self.assertEqual(PRODUCT_VOICE_SCHEMA,'ikant-product-voice-candidate/v0.27-test');self.assertTrue({'EXP-001','EXP-002','EXP-003','EXP-004'}<=set(critical_ids()))
 def test_manifests_preserve_s9_experience_noncollapse(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));x=m['product_experience'];self.assertEqual(x['schema'],PRODUCT_EXPERIENCE_SCHEMA);self.assertTrue(x['setup_visible_before_model_ready']);self.assertFalse(x['browser_may_mark_ready']);self.assertTrue(x['single_semantic_viewport']);self.assertTrue(x['progressive_disclosure']);self.assertFalse(x['browser_model_transport']);self.assertFalse(x['voice_input_auto_submit']);self.assertFalse(x['voice_input_is_approval']);self.assertEqual(x['epistemic_authority'],0.0);self.assertEqual(x['execution_authority'],0.0)
 def test_s9_workspace_primitives_survive_later_projection_compression(self):
  html=(ROOT/'ikant/web/index.html').read_text(encoding='utf-8');js=(ROOT/'ikant/web/app.js').read_text(encoding='utf-8');css=(ROOT/'ikant/web/styles.css').read_text(encoding='utf-8');self.assertEqual(html.count('id="dashboard"'),1);self.assertIn('command-palette',html);self.assertIn('inspector',html);self.assertIn('setup-panel',html);self.assertIn('inspector-button',html);self.assertNotIn('orbit-rail',html);self.assertIn('/api/v3/product/status',js);self.assertIn('localService===true',js);self.assertIn('processLocally:true',js);self.assertIn('prefers-reduced-motion',css);self.assertTrue((ROOT/'docs'/'S9_PRODUCT_EXPERIENCE.md').is_file())
if __name__=='__main__':unittest.main()
