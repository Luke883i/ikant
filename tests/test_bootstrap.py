import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_manifest(self):
  b=json.loads((ROOT/'BOOTSTRAP.json').read_text());a=json.loads((ROOT/'ADMISSION.json').read_text())
  self.assertNotIn('pre_admission_allowlist',b);self.assertNotIn('pre_admission_allowlist',a)
  self.assertFalse(b['connector_required']);self.assertFalse(b['installation_required']);self.assertFalse(b['degraded_runtime_simulation_allowed'])
  self.assertEqual(b['terms_envelope_path'],'IKANT_ACCESS_CONTRACT.md')
  self.assertEqual(b['pre_acceptance_firewall']['default'],'DENY');self.assertEqual(a['pre_acceptance_firewall']['default'],'DENY')
  self.assertTrue(b['pre_acceptance_firewall']['repository_materialization_requires_acceptance']);self.assertTrue(a['pre_acceptance_firewall']['repository_materialization_requires_acceptance'])
  self.assertEqual(set(b['pre_acceptance_firewall']['forbidden_operations']),set(a['pre_acceptance_firewall']['forbidden_operations']))
