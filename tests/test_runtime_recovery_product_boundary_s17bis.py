from __future__ import annotations

import unittest

from scripts.runtime_recovery_falsify import SIGNATURE_SPACE, modeled


class RuntimeRecoveryProductBoundaryS17bisTests(unittest.TestCase):
    def test_registered_boundary_scale_has_true_no_novelty_after_full_lattice_cycle(self):
        for seed in (17, 883, 2026):
            out = modeled(SIGNATURE_SPACE, SIGNATURE_SPACE, seed)
            self.assertTrue(out["coverage_complete"], seed)
            self.assertEqual(out["semantic_signatures"], SIGNATURE_SPACE, seed)
            self.assertEqual(out["domain_pairs_observed"], out["domain_pair_space"], seed)
            self.assertEqual(out["tail_new_signatures"], 0, seed)
            self.assertEqual(
                out["coverage_strategy"],
                "seed_bound_full_lattice_permutation_with_random_multifault_cooccurrence",
            )


if __name__ == "__main__":
    unittest.main()
