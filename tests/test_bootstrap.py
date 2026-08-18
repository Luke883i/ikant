import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_manifest(self):
  b=json.loads((ROOT/'BOOTSTRAP.json').read_text());a=json.loads((ROOT/'ADMISSION.json').read_text());self.assertFalse(b['connector_required']);self.assertFalse(b['installation_required']);self.assertFalse(b['degraded_runtime_simulation_allowed']);self.assertEqual(set(b['pre_admission_allowlist']),set(a['pre_admission_allowlist']))
