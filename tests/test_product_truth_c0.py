from __future__ import annotations

import json
from pathlib import Path
import unittest

from ikant.surface_contract import ASSET_REVISION, surface_manifest

ROOT=Path(__file__).resolve().parents[1]

class ProductTruthC0Tests(unittest.TestCase):
    def test_registered_product_bundle_readme_and_surface_share_s21_truth(self):
        contract=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'))
        bundle=json.loads((ROOT/'IKANT_DEVELOPMENT_BUNDLE.json').read_text(encoding='utf-8'))
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        surface=(ROOT/'ikant'/'surface_contract.py').read_text(encoding='utf-8')
        self.assertEqual(contract['constitutional_convergence'],'S21')
        self.assertEqual(contract['contract_version'],'0.22.0')
        self.assertEqual(bundle['baseline']['main_sha'],'c46db91c968edbf2203a27de9f0f17de46c38108')
        self.assertEqual(bundle['baseline']['merged_pr'],57)
        self.assertEqual(bundle['baseline']['merged_slice'],'S21')
        self.assertEqual(bundle['baseline']['product_contract_current_slice'],'S21')
        self.assertEqual(bundle['baseline']['product_contract_version'],'0.22.0')
        self.assertIn('S21',readme);self.assertIn('0.29.0a1',readme)
        self.assertIn('"version":"S21"',surface);self.assertNotIn('"version":"S20"',surface)
        self.assertEqual(ASSET_REVISION,'v031-c0-product-truth-surface-foundation-1')
        self.assertEqual(surface_manifest()['asset_revision'],ASSET_REVISION)

    def test_rta_receipt_and_lattice_keep_model_and_runtime_claims_separate(self):
        receipt=json.loads((ROOT/'backlog'/'rta'/'rta_200k_receipt.json').read_text(encoding='utf-8'))
        lattice=json.loads((ROOT/'backlog'/'rta'/'enterprise_lattice_convergence.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['master_seed'],1085021672383838793)
        self.assertEqual(receipt['campaigns']['as_is_main']['cases'],100_000)
        self.assertEqual(receipt['campaigns']['workbook']['cases'],100_000)
        self.assertEqual(receipt['campaigns']['as_is_main']['tail_new_signatures'],0)
        self.assertEqual(receipt['campaigns']['workbook']['tail_new_signatures'],0)
        self.assertFalse(receipt['claim_boundary']['mutation_counts_are_reliability'])
        self.assertFalse(receipt['claim_boundary']['enterprise_candidate_achieved'])
        self.assertTrue(lattice['workbook_v1_falsified'])
        self.assertEqual(lattice['counts']['runtime_slices_after_s21'],12)
        self.assertEqual(lattice['counts']['non_runtime_gates'],3)
        gates={x['id']:x for x in lattice['gates']}
        self.assertEqual(set(gates),{'C0','G0','E0'})
        self.assertTrue(all(x['adds_runtime_capability'] is False for x in gates.values()))

if __name__=='__main__':unittest.main()
