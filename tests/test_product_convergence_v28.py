from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant.invariants import critical_ids
from ikant.epistemic_projection import EPISTEMIC_WORKSPACE_SCHEMA,EPISTEMIC_INDEX_SCHEMA
ROOT=Path(__file__).parents[1];EXPECTED_EPW={'EPW-001','EPW-002','EPW-003','EPW-004'}
class ProductConvergenceV28Tests(unittest.TestCase):
 def test_s10_remains_historical_registered_prefix(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));ids=[x['id'] for x in c['slices']];self.assertEqual(ids[:10],['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10']);s=c['slices'][9];self.assertEqual(s['schema'],EPISTEMIC_WORKSPACE_SCHEMA);self.assertEqual(set(s['invariants']),EXPECTED_EPW);self.assertEqual(s['historical_saturation'],{'cases':10000000,'mutations':10000000,'edges':10000000,'tail':1000,'seed':20260821});self.assertEqual(s['historical_evidence']['minimality_architectures'],1048576);self.assertEqual(s['historical_evidence']['minimal_valid_architectures'],1);self.assertEqual(s['historical_evidence']['additional_stress_cases'],1000000);self.assertEqual(s['historical_evidence']['additional_stress_seed'],314159265)
 def test_epistemic_workspace_invariants_are_constitutional(self):self.assertEqual(EPISTEMIC_WORKSPACE_SCHEMA,'ikant-epistemic-workspace/v0.28-test');self.assertEqual(EPISTEMIC_INDEX_SCHEMA,'ikant-epistemic-index/v0.28-test');self.assertTrue(EXPECTED_EPW<=set(critical_ids()))
 def test_manifests_preserve_read_only_noncollapse(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));x=m['epistemic_workspace'];self.assertEqual(x['schema'],EPISTEMIC_WORKSPACE_SCHEMA);self.assertTrue(x['read_only']);self.assertTrue(x['requires_current_s8_writer']);self.assertTrue(x['requires_exact_last_ack']);self.assertTrue(x['pending_frame_blocks_read']);self.assertTrue(x['same_session_cycle_required']);self.assertEqual(x['history_limit'],64);self.assertEqual(x['object_limit'],96);self.assertEqual(x['snapshot_max_bytes'],4194304);self.assertTrue(x['docx_requires_json_companion']);self.assertFalse(x['projection_is_source_truth']);self.assertFalse(x['presentation_is_evidence']);self.assertFalse(x['presentation_is_authorization']);self.assertFalse(x['persistence_added']);self.assertEqual(x['epistemic_authority'],0.0);self.assertEqual(x['execution_authority'],0.0)
 def test_s10_assets_and_docs_are_preserved(self):
  for p in ('ikant/epistemic_projection.py','ikant/epistemic_workspace.py','ikant/epistemic_http.py','ikant/web/epistemic.js','ikant/web/epistemic.css','docs/S10_EPISTEMIC_WORKSPACE.md'):self.assertTrue((ROOT/p).is_file(),p)
if __name__=='__main__':unittest.main()
