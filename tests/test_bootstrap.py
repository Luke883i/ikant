import json,unittest
from pathlib import Path
from ikant.pre_admission import policy_manifest
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_manifest(self):
  b=json.loads((ROOT/'BOOTSTRAP.json').read_text());a=json.loads((ROOT/'ADMISSION.json').read_text());p=policy_manifest()
  self.assertFalse(b['connector_required']);self.assertFalse(b['installation_required']);self.assertFalse(b['degraded_runtime_simulation_allowed'])
  self.assertEqual(b['contract_version'],'0.8.0');self.assertEqual(a['contract_version'],'0.8.0')
  self.assertEqual(b['pre_acceptance_firewall']['schema'],p['schema']);self.assertEqual(a['pre_acceptance_firewall']['schema'],p['schema'])
  self.assertEqual(b['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule']);self.assertEqual(a['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule'])
  self.assertTrue(b['pre_acceptance_firewall']['freeze_after_terms_presentation']);self.assertTrue(a['pre_acceptance_firewall']['freeze_after_terms_presentation'])
  self.assertEqual(set(b['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
  self.assertEqual(set(a['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
