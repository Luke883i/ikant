from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids,registry_manifest
ROOT=Path(__file__).parents[1]
class ProductConvergenceV24Tests(unittest.TestCase):
 def test_v24_identity_converges(self):
  self.assertEqual(PRODUCT_VERSION,'0.24.0a1');self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(registry_manifest()['product_version'],PRODUCT_VERSION);self.assertEqual(INVARIANT_REGISTRY_SCHEMA,'ikant-invariant-registry/v0.24-test')
 def test_s6_is_current_registered_slice(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual([x['id'] for x in c['slices']],['S1','S2','S3','S4','S5','S6']);self.assertEqual(c['constitutional_convergence'],'S6');s=c['slices'][-1];self.assertEqual(s['schema'],'ikant-temporal-autonomy/v0.24-test');self.assertEqual(set(s['invariants']),{'TMP-001','TMP-002','TMP-003'});self.assertEqual(s['saturation'],{'cases':1000000,'mutations':10000000,'edges':1000000,'tail':100000,'seed':883})
 def test_temporal_invariants_are_constitutional(self):
  self.assertTrue({'TMP-001','TMP-002','TMP-003'}<=set(critical_ids()))
 def test_manifests_expose_zero_authority_temporal_boundary(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));s=m['temporal_autonomy'];self.assertFalse(s['material_execution_bridge']);self.assertFalse(s['pre_wake_approval_reusable']);self.assertFalse(s['pre_wake_grant_reusable']);self.assertFalse(s['pre_wake_lease_reusable']);self.assertFalse(s['automatic_material_retry']);self.assertFalse(s['hardware_wake']);self.assertFalse(s['os_background_service']);self.assertTrue(s['requires_locked_egress_to_poll']);self.assertTrue(s['fresh_host_revalidation_required']);self.assertEqual(s['epistemic_authority'],0.0);self.assertEqual(s['execution_authority'],0.0)
 def test_product_gate_derives_registered_slices(self):
  text=(ROOT/'scripts'/'product_boundary.py').read_text(encoding='utf-8');self.assertNotIn('EXPECTED_SLICES',text);self.assertIn('--deep-current',text);self.assertIn("constitutional_convergence",text)
if __name__=='__main__':unittest.main()
