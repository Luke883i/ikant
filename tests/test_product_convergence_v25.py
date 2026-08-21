from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant.invariants import critical_ids
ROOT=Path(__file__).parents[1]

class ProductConvergenceV25Tests(unittest.TestCase):
 def test_s7_remains_historical_registered_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual([x['id'] for x in c['slices'][:7]],['S1','S2','S3','S4','S5','S6','S7']);s=c['slices'][6];self.assertEqual(s['schema'],'ikant-human-surface-protocol/v0.25-test');self.assertEqual(set(s['invariants']),{'HSP-001','HSP-002','HSP-003'});self.assertEqual(s.get('historical_saturation') or s.get('saturation'),{'cases':1000000,'mutations':10000000,'edges':1000000,'tail':100000,'seed':883})
 def test_hsp_invariants_remain_constitutional(self):self.assertTrue({'HSP-001','HSP-002','HSP-003'}<=set(critical_ids()))
 def test_manifests_preserve_hsp_noncollapse(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));s=m['human_surface_protocol'];self.assertEqual(s['schema'],'ikant-human-surface-protocol/v0.25-test');self.assertTrue(s['single_sealed_dashboard_frame']);self.assertTrue(s['typed_payload_exclusive']);self.assertFalse(s['raw_model_tokens_visible']);self.assertFalse(s['parallel_active_human_messages']);self.assertFalse(s['approval_request_is_authorization']);self.assertFalse(s['approval_request_records_decision']);self.assertEqual(s['epistemic_authority'],0.0);self.assertEqual(s['execution_authority'],0.0)
 def test_browser_active_error_channel_remains_removed(self):
  js=(ROOT/'ikant'/'web'/'app.js').read_text(encoding='utf-8');html=(ROOT/'ikant'/'web'/'index.html').read_text(encoding='utf-8');self.assertIn('recoverActiveFrame',js);self.assertNotIn("setError('active-error',error.message)",js);self.assertNotIn('id="active-error"',html)
if __name__=='__main__':unittest.main()
