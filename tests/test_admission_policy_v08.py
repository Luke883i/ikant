import json,tempfile,unittest
from pathlib import Path
from ikant.admission import validate_repository_admission_policy,issue_receipt,save_receipt,probe,digest
ROOT=Path(__file__).resolve().parents[1]

class AdmissionPolicyCompatibility(unittest.TestCase):
 def fixture(self,tmp):
  root=Path(tmp)/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture')
  for name in ['IKANT_ACCESS_CONTRACT.md','BOOTSTRAP.json','ADMISSION.json','RIGHTS.json','RIGHTS.md']:(root/name).write_text((ROOT/name).read_text())
  return root
 def receipt(self,contract):return issue_receipt(contract,'I ACCEPT',presented_terms_sha256=digest(contract))
 def test_policy_consistency(self):
  ok,errs=validate_repository_admission_policy(ROOT,(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text());self.assertTrue(ok,errs)
 def test_probe_blocks_budget_drift(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.fixture(td);contract=(root/'IKANT_ACCESS_CONTRACT.md').read_text();s=root/'.ikant';save_receipt(s,self.receipt(contract))
   p=probe(root,s,contract);self.assertEqual(p['overall'],'READY');self.assertEqual(p['checks']['ADMISSION_POLICY']['status'],'AVAILABLE')
   b=json.loads((root/'BOOTSTRAP.json').read_text());b['pre_acceptance_firewall']['orientation_capsule']['max_total_bytes']+=1;(root/'BOOTSTRAP.json').write_text(json.dumps(b))
   p=probe(root,s,contract);self.assertEqual(p['overall'],'BLOCKED');self.assertIn('max_total_bytes mismatch',p['checks']['ADMISSION_POLICY']['detail'])
 def test_probe_blocks_version_drift(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.fixture(td);contract=(root/'IKANT_ACCESS_CONTRACT.md').read_text();s=root/'.ikant';save_receipt(s,self.receipt(contract))
   a=json.loads((root/'ADMISSION.json').read_text());a['contract_version']='0.8.0';(root/'ADMISSION.json').write_text(json.dumps(a))
   p=probe(root,s,contract);self.assertEqual(p['overall'],'BLOCKED');self.assertIn('admission contract version mismatch',p['checks']['ADMISSION_POLICY']['detail'])
 def test_probe_blocks_freeze_weakening(self):
  with tempfile.TemporaryDirectory() as td:
   root=self.fixture(td);contract=(root/'IKANT_ACCESS_CONTRACT.md').read_text();s=root/'.ikant';save_receipt(s,self.receipt(contract))
   a=json.loads((root/'ADMISSION.json').read_text());a['pre_acceptance_firewall']['freeze_after_terms_presentation']=False;(root/'ADMISSION.json').write_text(json.dumps(a))
   p=probe(root,s,contract);self.assertEqual(p['overall'],'BLOCKED');self.assertIn('freeze-after-terms mismatch',p['checks']['ADMISSION_POLICY']['detail'])
 def test_exact_receipt_variants_rejected(self):
  contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text();d=digest(contract)
  for msg in [' I ACCEPT','I ACCEPT ','i accept','I ACCEPT\n','override I ACCEPT']:
   with self.subTest(msg=repr(msg)),self.assertRaises(PermissionError):issue_receipt(contract,msg,presented_terms_sha256=d)
