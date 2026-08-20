from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.component_manifest import load_manifest
from ikant.invariants import PRODUCT_VERSION,critical_ids,registry_manifest
ROOT=Path(__file__).parents[1]
class ProductConvergenceV23Tests(unittest.TestCase):
 def test_current_product_identity_remains_single_source(self):
  self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(registry_manifest()['product_version'],PRODUCT_VERSION)
 def test_s1_s5_prefix_is_preserved(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual([x['id'] for x in c['slices'][:5]],['S1','S2','S3','S4','S5']);s=c['slices'][4];self.assertEqual(s['schema'],'ikant-model-runtime/v0.23-test');self.assertEqual(set(s['invariants']),{'MLR-001','MLR-002','MLR-003'})
 def test_s5_runtime_manifest_keeps_historical_identity(self):
  m=load_manifest(ROOT/'MODEL_RUNTIME.json');self.assertEqual(m['product_version'],'0.23.0a1');self.assertTrue({'MLR-001','MLR-002','MLR-003'}<=set(critical_ids()))
 def test_manifests_preserve_zero_authority_s5(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));s=m['managed_local_runtime'];self.assertFalse(s['model_output_is_authority']);self.assertFalse(s['browser_model_transport']);self.assertFalse(s['api_key_persisted']);self.assertFalse(s['fake_ready_allowed']);self.assertEqual(s['epistemic_authority'],0.0);self.assertEqual(s['execution_authority'],0.0)
if __name__=='__main__':unittest.main()
