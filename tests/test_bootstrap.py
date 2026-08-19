import json,tomllib,unittest
from pathlib import Path
from ikant.pre_admission import policy_manifest
import ikant
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_manifest(self):
  b=json.loads((ROOT/'BOOTSTRAP.json').read_text());a=json.loads((ROOT/'ADMISSION.json').read_text());p=policy_manifest();project=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']
  self.assertFalse(b['connector_required']);self.assertFalse(b['installation_required']);self.assertFalse(b['degraded_runtime_simulation_allowed'])
  self.assertEqual(b['contract_version'],'0.9.0');self.assertEqual(a['contract_version'],'0.9.0')
  self.assertEqual(project['version'],'0.9.0a1');self.assertEqual(ikant.__version__,'0.9.0a1')
  self.assertEqual(b['pre_acceptance_firewall']['schema'],p['schema']);self.assertEqual(a['pre_acceptance_firewall']['schema'],p['schema'])
  self.assertEqual(b['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule']);self.assertEqual(a['pre_acceptance_firewall']['orientation_capsule'],p['orientation_capsule'])
  self.assertTrue(b['pre_acceptance_firewall']['freeze_after_terms_presentation']);self.assertTrue(a['pre_acceptance_firewall']['freeze_after_terms_presentation'])
  self.assertTrue(b['pre_acceptance_firewall']['completed_access_accounting_required']);self.assertTrue(a['pre_acceptance_firewall']['completed_access_accounting_required'])
  self.assertTrue(b['pre_acceptance_firewall']['presented_terms_digest_handoff_required']);self.assertTrue(a['pre_acceptance_firewall']['presented_terms_digest_handoff_required'])
  self.assertEqual(set(b['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
  self.assertEqual(set(a['pre_acceptance_firewall']['forbidden_operations']),set(p['forbidden_before_acceptance']))
  self.assertTrue(b['active_human_egress']['exclusive']);self.assertTrue(a['active_human_egress']['exclusive_human_output'])
  self.assertEqual(b['active_human_egress']['exit_command'],'EXIT IKANT');self.assertEqual(a['active_human_egress']['exit_command'],'EXIT IKANT')
