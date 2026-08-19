import tempfile,unittest
from pathlib import Path
from ikant.admission import digest,issue_receipt,validate_receipt,save_receipt,probe,validate_repository_admission_policy
from ikant.pre_admission import AdmissionGate,Action,GateState

ROOT=Path(__file__).resolve().parents[1]

class AdmissionV09(unittest.TestCase):
 def test_receipt_requires_presented_digest(self):
  contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text()
  with self.assertRaises(PermissionError):issue_receipt(contract,'I ACCEPT')
  r=issue_receipt(contract,'I ACCEPT',presented_terms_sha256=digest(contract));self.assertTrue(validate_receipt(r,contract)[0])
 def test_repo_change_after_acceptance_blocks(self):
  contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text();old=digest(contract+'old')
  with self.assertRaises(PermissionError):issue_receipt(contract,'I ACCEPT',presented_terms_sha256=old)
 def test_probe_detects_binding_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture')
   for name in ('IKANT_ACCESS_CONTRACT.md','BOOTSTRAP.json','ADMISSION.json'):(root/name).write_text((ROOT/name).read_text())
   contract=(root/'IKANT_ACCESS_CONTRACT.md').read_text();s=root/'.ikant';r=issue_receipt(contract,'I ACCEPT',presented_terms_sha256=digest(contract));r['presented_terms_sha256']='0'*64;save_receipt(s,r);p=probe(root,s,contract);self.assertEqual(p['overall'],'BLOCKED');self.assertEqual(p['checks']['ACCEPTANCE_BINDING']['status'],'UNAVAILABLE')
 def test_unaccounted_completed_orientation_breaches(self):
  g=AdmissionGate();d=g.record_completed_access(Action.READ_ORIENTATION_FILE,target='README.md',initiated_by_host=True,exposed_to_model=False);self.assertEqual(d.code,'PRE_ACCEPT_UNACCOUNTED_ORIENTATION_BREACH');self.assertEqual(g.context.state,GateState.BREACHED.value)
 def test_incidental_unexposed_orientation_overfetch_quarantines(self):
  g=AdmissionGate();d=g.record_completed_access(Action.READ_ORIENTATION_FILE,target='README.md',initiated_by_host=False,exposed_to_model=False);self.assertTrue(d.quarantine_required);self.assertEqual(g.context.state,GateState.DISCOVERED.value)
 def test_policy_is_self_consistent(self):
  ok,errs=validate_repository_admission_policy(ROOT,(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text());self.assertTrue(ok,errs)

if __name__=='__main__':unittest.main()
