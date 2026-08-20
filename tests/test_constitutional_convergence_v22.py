from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.invariants import PRODUCT_VERSION,critical_ids,registry_manifest
ROOT=Path(__file__).parents[1]
class ConstitutionalConvergenceV22Tests(unittest.TestCase):
 def test_current_product_identity_remains_single_source(self):
  self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(registry_manifest()['product_version'],PRODUCT_VERSION)
 def test_product_contract_preserves_s1_s4_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual([x['id'] for x in c['slices'][:4]],['S1','S2','S3','S4'])
  for s in c['slices'][:4]:
   self.assertTrue((ROOT/(s['machine_test'].replace('.','/')+'.py')).is_file());self.assertTrue(set(s['seeded_harnesses'])<={'stress','mutations','edges'})
   for key in ('stress','mutations','edges'):self.assertTrue((ROOT/s[key]).is_file())
  self.assertNotIn('mutations',c['slices'][3]['seeded_harnesses'])
 def test_s1_s4_are_constitutional(self):
  ids=set(critical_ids());self.assertTrue({'AGY-001','AGY-002','AGY-003','EMB-001','EMB-002','WEB-001','WEB-002','NAT-001','NAT-002','NAT-003'}<=ids)
 def test_authority_chain_is_not_collapsed(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertTrue(c['authority_separation_required']);self.assertEqual(c['authority_chain'],['evidence','permission','approval','grant','lease','execution','reported_outcome'])
if __name__=='__main__':unittest.main()
