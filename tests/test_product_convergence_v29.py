from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids
from ikant.bootstrap_runtime import BOOTSTRAP_OBSERVABILITY_SCHEMA
ROOT=Path(__file__).parents[1];EXPECTED={'BOS-001','BOS-002','BOS-003','BOS-004'}
class ProductConvergenceV29Tests(unittest.TestCase):
 def test_v29_identity_converges(self):self.assertEqual(PRODUCT_VERSION,'0.29.0a1');self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(INVARIANT_REGISTRY_SCHEMA,'ikant-invariant-registry/v0.29-test')
 def test_s10bis_is_preserved_as_registered_historical_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());ids=[x['id'] for x in c['slices']];self.assertEqual(ids[:11],['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S10bis']);s=c['slices'][10];self.assertEqual(s['schema'],BOOTSTRAP_OBSERVABILITY_SCHEMA);self.assertEqual(set(s['invariants']),EXPECTED);self.assertEqual(s['saturation'],{'cases':10000000,'mutations':10000000,'edges':10000000,'tail':1000,'seed':20260821});self.assertEqual(s['evidence']['minimality_architectures'],1048576);self.assertEqual(s['evidence']['minimal_valid_architectures'],1);self.assertEqual(s['evidence']['minimal_enabled_features'],14)
 def test_s11_is_current_without_rewriting_s10bis_evidence(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());self.assertEqual(c['constitutional_convergence'],'S11');self.assertEqual(c['slices'][-1]['id'],'S11');self.assertEqual(c['slices'][-1]['schema'],'ikant-experience-projection/v1.3')
 def test_s10_is_preserved_as_historical_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());s=c['slices'][9];self.assertEqual(s['id'],'S10');self.assertIn('historical_saturation',s);self.assertNotIn('saturation',s)
 def test_bos_invariants_and_assets_exist(self):
  self.assertTrue(EXPECTED<=set(critical_ids()))
  for p in ('ikant/bootstrap_observability.py','ikant/bootstrap_runtime.py','ikant/bootstrap_http.py','ikant/web/bootstrap.js','ikant/web/bootstrap.css','docs/S10BIS_BOOTSTRAP_OBSERVABILITY.md'):self.assertTrue((ROOT/p).is_file(),p)
 def test_pwa_keeps_s10bis_lineage_and_bumps_for_ecf13(self):
  sw=(ROOT/'ikant/web/sw.js').read_text();self.assertIn('ikant-s10bis-bootstrap-v1',sw);self.assertIn('ecf1-3-runtime-v30',sw)
if __name__=='__main__':unittest.main()
