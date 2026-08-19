import json,tomllib,unittest
from pathlib import Path
from ikant.pre_admission import policy_manifest
from ikant.invariants import CONTRACT_VERSION,PRODUCT_VERSION,EGRESS_SCHEMA,INVARIANT_REGISTRY_SCHEMA
import ikant
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_manifest(self):
  b=json.loads((ROOT/'BOOTSTRAP.json').read_text());a=json.loads((ROOT/'ADMISSION.json').read_text());p=policy_manifest();project=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']
  self.assertFalse(b['connector_required']);self.assertFalse(b['installation_required']);self.assertFalse(b['degraded_runtime_simulation_allowed'])
  self.assertEqual(b['contract_version'],CONTRACT_VERSION);self.assertEqual(a['contract_version'],CONTRACT_VERSION)
  self.assertEqual(project['version'],PRODUCT_VERSION);self.assertEqual(ikant.__version__,PRODUCT_VERSION)
  self.assertEqual(b['pre_acceptance_firewall']['schema'],p['schema']);self.assertEqual(a['pre_acceptance_firewall']['schema'],p['schema'])
  self.assertEqual(b['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule']);self.assertEqual(a['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule'])
  self.assertTrue(b['pre_acceptance_firewall']['freeze_after_terms_presentation']);self.assertTrue(a['pre_acceptance_firewall']['freeze_after_terms_presentation'])
  self.assertTrue(b['pre_acceptance_firewall']['completed_access_accounting_required']);self.assertTrue(a['pre_acceptance_firewall']['completed_access_accounting_required'])
  self.assertTrue(b['pre_acceptance_firewall']['presented_terms_digest_handoff_required']);self.assertTrue(a['pre_acceptance_firewall']['presented_terms_digest_handoff_required'])
  self.assertEqual(set(b['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
  self.assertEqual(set(a['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
  be=b['active_human_egress'];ae=a['active_human_egress'];self.assertEqual(be['schema'],EGRESS_SCHEMA);self.assertEqual(ae['schema'],EGRESS_SCHEMA);self.assertTrue(be['exclusive']);self.assertTrue(ae['exclusive_human_output'])
  self.assertTrue(be['two_phase_delivery']);self.assertTrue(ae['delivery_ack_after_emit_required']);self.assertTrue(ae['pending_frame_durable']);self.assertTrue(ae['journal_hash_chain']);self.assertEqual(ae['max_frame_bytes'],131072)
  self.assertTrue(be['guard_recreation_forbidden']);self.assertTrue(ae['guard_recreation_forbidden']);self.assertTrue(be['breach_resume_requires_transport_attestation']);self.assertTrue(ae['breach_resume_requires_transport_attestation']);self.assertTrue(be['machine_output_file_only']);self.assertTrue(ae['machine_output_file_only'])
  self.assertEqual(a['invariant_registry']['schema'],INVARIANT_REGISTRY_SCHEMA)
if __name__=='__main__':unittest.main()
