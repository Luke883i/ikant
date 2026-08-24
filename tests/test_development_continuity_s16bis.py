from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DevelopmentContinuityS16bisTests(unittest.TestCase):
    def test_bundle_has_adaptive_post_s17bis_roadmap_and_dod_shapes(self):
        bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'))
        self.assertEqual(bundle['schema'],'ikant-development-continuity-bundle/v1-test')
        self.assertEqual([x['id'] for x in bundle['roadmap']],['S16bis','S17','S17bis','S18','S19','S20','S21','S22','S23','S24','S25','S26'])
        required={'foundation_links','expected_runtime','user_experience','technology_supply_chain','dod','success_metrics','checklist','ui_ux_prototype','prerequisites'}
        for row in bundle['roadmap']:
            self.assertTrue(required<=set(row),row['id']);self.assertEqual(set(row['dod']),{'local','intermediate','final'})
        self.assertEqual(set(bundle['iteration_protocol']['modes']),{'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'})
        self.assertEqual(set(bundle['iteration_protocol']['end_of_iteration_choices']),{'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'})
        dag=bundle['dependency_dag'];self.assertIn(['S19','S20'],dag['commutable_siblings']);self.assertIn(['S18','S19'],dag['causal_edges']);self.assertIn(['S18','S20'],dag['causal_edges']);self.assertNotIn(['S19','S20'],dag['causal_edges']);self.assertIn(['S23','S24'],dag['causal_edges']);self.assertNotIn(['S22','S24'],dag['causal_edges'])

    def test_bundle_records_modeled_campaigns_without_reliability_claim(self):
        bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'));rows=bundle['modeled_campaigns']
        self.assertEqual([x['campaign'] for x in rows],['hardening','hypothetical','usage','post_s17_multiaxial','s17bis_runtime_recovery','s18_causal_100m'])
        for row in rows:
            self.assertEqual(row['cases'],10_000_000);self.assertEqual(row['tail'],100_000);self.assertTrue(row['coverage_complete']);self.assertEqual(row['signatures_observed'],row['signature_space']);self.assertEqual(row['tail_new_signatures'],0);self.assertIn('not',row['interpretation'].lower())
        s18=rows[-1];self.assertEqual(s18['levels'],10);self.assertEqual(s18['aggregate_cases'],100_000_000);self.assertEqual(s18['seed_fanout'],1000)

    def test_bundle_gate_represents_s18_registered_candidate_over_merged_s17bis(self):
        run=subprocess.run([sys.executable,'scripts/development_bundle_gate.py'],cwd=ROOT,text=True,capture_output=True,check=False);self.assertEqual(run.returncode,0,run.stderr+run.stdout);out=json.loads(run.stdout)
        self.assertEqual(out['status'],'PASS');self.assertEqual(out['candidate_slice'],'S18');self.assertEqual(out['candidate_registration_state'],'REGISTERED_CANDIDATE');self.assertEqual(out['baseline_product_contract_current_slice'],'S17bis');self.assertEqual(out['product_contract_current_slice'],'S18');self.assertTrue(out['registered_candidate_is_not_merged_main']);self.assertTrue(out['git_baseline_checked']);self.assertTrue(out['ready_to_develop_candidate']);self.assertTrue(out['candidate_complete']);self.assertTrue(out['ready_to_advance']);self.assertEqual(out['candidate_entry_blockers'],[]);self.assertEqual(out['candidate_open_objectives'],[]);self.assertIn('FND-003',out['future_open_risks'])
        bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'));findings={x['id']:x for x in bundle['audit_findings']}
        for fid in ('FND-017','FND-018','FND-019'):self.assertEqual(findings[fid]['status'],'CLOSED')
        self.assertEqual(bundle['baseline']['main_sha'],'4b8d466452e7ace02edc32f2f6012c9d19e10238');self.assertEqual(bundle['baseline']['merged_pr'],54);self.assertEqual(bundle['baseline']['merged_slice'],'S17bis')

    def test_post_s17_model_is_historical_not_current_roadmap_authority(self):
        from scripts.post_s17_multiaxial_falsify import run
        out=run(100_000,10_000,202608241302);self.assertEqual(out['fault_families'],96);self.assertEqual(out['semantic_signature_space'],12_288);self.assertTrue(out['domain_pair_matrix_complete']);self.assertTrue(out['structural']['S18_S19_commutable'])
        bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'));self.assertEqual(bundle['roadmap'][3]['name'],'Durable Cognitive State / Causal Ledger');self.assertIn(['S18','S19'],bundle['dependency_dag']['causal_edges'])

    def test_surface_contract_source_fails_closed_only_after_canonical_bind(self):
        source=(ROOT/'ikant/web/surface-contract.js').read_text(encoding='utf-8');self.assertIn('canonicalBound=true',source);self.assertIn('legacy_semantic_fallback:false',source);self.assertIn('if(canonicalBound)return failClosed',source);self.assertIn('return nativeFetch(input,init)',source)

    def test_actual_javascript_boundary_when_node_is_available(self):
        node=shutil.which('node')
        if not node:self.skipTest('node unavailable; real JS oracle remains required in Hosted/browser gate')
        run=subprocess.run([node,'scripts/surface_contract_failclosed.mjs'],cwd=ROOT,text=True,capture_output=True,check=False);self.assertEqual(run.returncode,0,run.stderr+run.stdout);out=json.loads(run.stdout.strip().splitlines()[-1]);self.assertEqual(out['status'],'PASS');self.assertFalse(out['active_post_bind_legacy_fallback'])

    def test_material_corrective_lineage_is_reconciled_through_s17bis(self):
        contract=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));by={x['id']:x for x in contract['slices']};self.assertEqual(by['S15bis']['material_merge']['pr'],47);self.assertEqual(by['S16bis']['material_merge']['pr'],49);self.assertEqual(by['S17bis']['material_merge'],{'pr':54,'merge_commit_sha':'4b8d466452e7ace02edc32f2f6012c9d19e10238'})

if __name__=='__main__':unittest.main()
