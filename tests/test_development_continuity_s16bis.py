from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DevelopmentContinuityS16bisTests(unittest.TestCase):
 def test_bundle_has_complete_mutated_roadmap_and_dod_shapes(self):
  bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'))
  self.assertEqual(bundle['schema'],'ikant-development-continuity-bundle/v1-test')
  self.assertEqual([x['id'] for x in bundle['roadmap']],['S16bis','S17','S18','S19','S20','S21'])
  required={'foundation_links','expected_runtime','user_experience','technology_supply_chain','dod','success_metrics','checklist','ui_ux_prototype','prerequisites'}
  for row in bundle['roadmap']:
   self.assertTrue(required<=set(row),row['id']);self.assertEqual(set(row['dod']),{'local','intermediate','final'})
  self.assertEqual(set(bundle['iteration_protocol']['modes']),{'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'})
  self.assertEqual(set(bundle['iteration_protocol']['end_of_iteration_choices']),{'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'})
 def test_bundle_records_three_distinct_ten_million_campaigns_without_reliability_claim(self):
  bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'));rows=bundle['modeled_campaigns']
  self.assertEqual([x['campaign'] for x in rows],['hardening','hypothetical','usage'])
  for row in rows:
   self.assertEqual(row['cases'],10_000_000);self.assertEqual(row['tail'],100_000);self.assertTrue(row['coverage_complete']);self.assertEqual(row['signatures_observed'],row['signature_space']);self.assertEqual(row['tail_new_signatures'],0);self.assertIn('not',row['interpretation'].lower())
 def test_structural_bundle_gate_passes_but_does_not_claim_readiness_with_open_blockers(self):
  run=subprocess.run([sys.executable,'scripts/development_bundle_gate.py'],cwd=ROOT,text=True,capture_output=True,check=False)
  self.assertEqual(run.returncode,0,run.stderr+run.stdout);out=json.loads(run.stdout);self.assertEqual(out['status'],'PASS');self.assertFalse(out['ready_to_advance']);self.assertIn('FND-002',out['open_high_or_critical_blockers'])
 def test_surface_contract_source_fails_closed_only_after_canonical_bind(self):
  source=(ROOT/'ikant/web/surface-contract.js').read_text(encoding='utf-8')
  self.assertIn("canonicalBound=true",source);self.assertIn("legacy_semantic_fallback:false",source);self.assertIn("if(canonicalBound)return failClosed",source);self.assertIn("return nativeFetch(input,init)",source)
 def test_actual_javascript_boundary_when_node_is_available(self):
  node=shutil.which('node')
  if not node:self.skipTest('node unavailable; real JS oracle remains required in Hosted/browser gate')
  run=subprocess.run([node,'scripts/surface_contract_failclosed.mjs'],cwd=ROOT,text=True,capture_output=True,check=False)
  self.assertEqual(run.returncode,0,run.stderr+run.stdout);out=json.loads(run.stdout.strip().splitlines()[-1]);self.assertEqual(out['status'],'PASS');self.assertFalse(out['active_post_bind_legacy_fallback'])
 def test_material_s15bis_lineage_gap_remains_explicit_until_reconciled(self):
  contract=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));ids=[x['id'] for x in contract['slices']]
  bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'));finding={x['id']:x for x in bundle['audit_findings']}['FND-002']
  if 'S15bis' not in ids:self.assertEqual(finding['status'],'OPEN')

if __name__=='__main__':unittest.main()
