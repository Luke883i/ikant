from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ikant.admission import digest, issue_receipt, probe, save_receipt
from ikant.invariants import critical_ids, registry_manifest
from ikant.rights_policy import (
    AccessMode,
    ExternalBasis,
    RIGHTS_SCHEMA,
    decide_owner_authorization,
    policy_manifest,
    policy_sha256,
    semantic_access_slice,
    validate_repository_rights,
)

ROOT = Path(__file__).resolve().parents[1]


class RightsPolicyV12(unittest.TestCase):
    def test_rights_manifest_is_digest_bound(self):
        payload = json.loads((ROOT / "RIGHTS.json").read_text(encoding="utf-8"))
        self.assertEqual(payload, policy_manifest())
        contract = (ROOT / "IKANT_ACCESS_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn(f"rights_policy_schema: {RIGHTS_SCHEMA}", contract)
        self.assertIn(f"rights_policy_sha256: {policy_sha256(payload)}", contract)
        ok, errors = validate_repository_rights(ROOT, contract)
        self.assertTrue(ok, errors)

    def test_manual_human_review_is_outside_ai_gate(self):
        d = decide_owner_authorization(AccessMode.HUMAN_MANUAL)
        self.assertEqual(d.code, "HUMAN_MANUAL_OUTSIDE_AI_GATE")
        self.assertEqual(d.owner_authorization, "NOT_REQUIRED_BY_IKANT_POLICY")
        self.assertFalse(d.epistemic_authority)

    def test_public_or_acceptance_without_admission_does_not_authorize_ai_study(self):
        self.assertEqual(decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY).owner_authorization, "RESERVED")
        self.assertEqual(decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY, accepted_current_terms=True).owner_authorization, "RESERVED")

    def test_clean_chat_study_is_owner_authorized_without_local_runtime(self):
        d = decide_owner_authorization(AccessMode.AI_ASSISTED_STUDY, accepted_current_terms=True, clean_admission=True, technical_conformance=False)
        self.assertEqual(d.code, "OWNER_AUTHORIZED_CHAT_STUDY")
        self.assertEqual(d.owner_authorization, "GRANTED_UNDER_CURRENT_IKANT_TERMS")
        self.assertEqual(d.ikant_conformance, "NOT_REQUIRED_FOR_CHAT_STUDY")

    def test_remediated_chat_study_is_prospective_and_nonconforming(self):
        d = decide_owner_authorization(AccessMode.AUTOMATED_REPOSITORY_ANALYSIS, accepted_current_terms=True, remediated_admission=True)
        self.assertEqual(d.code, "OWNER_AUTHORIZED_REMEDIATED_CHAT_STUDY")
        self.assertEqual(d.owner_authorization, "GRANTED_PROSPECTIVELY_AFTER_REMEDIATION")
        self.assertEqual(d.ikant_conformance, "NOT_CONFORMING")

    def test_official_ikant_still_requires_clean_technical_conformance(self):
        self.assertEqual(decide_owner_authorization(AccessMode.OFFICIAL_IKANT, accepted_current_terms=True, clean_admission=True).owner_authorization, "RESERVED")
        d = decide_owner_authorization(AccessMode.OFFICIAL_IKANT, accepted_current_terms=True, clean_admission=True, technical_conformance=True)
        self.assertEqual(d.code, "OWNER_AUTHORIZED_CONFORMING_IKANT")
        self.assertEqual(d.ikant_conformance, "CONFORMING")

    def test_materialization_is_bootstrap_only_and_requires_clean_admission(self):
        d = decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION, accepted_current_terms=True, clean_admission=True)
        self.assertEqual(d.code, "MATERIALIZATION_FOR_CONFORMANCE_ALLOWED")
        self.assertEqual(d.owner_authorization, "GRANTED_FOR_CONFORMANCE_BOOTSTRAP")
        self.assertEqual(d.ikant_conformance, "PENDING")
        denied = decide_owner_authorization(AccessMode.CONFORMANCE_MATERIALIZATION, accepted_current_terms=True, remediated_admission=True)
        self.assertEqual(denied.owner_authorization, "RESERVED")

    def test_model_training_needs_separate_license_even_after_acceptance(self):
        d = decide_owner_authorization(AccessMode.MODEL_TRAINING, accepted_current_terms=True, clean_admission=True, technical_conformance=True)
        self.assertEqual(d.code, "SEPARATE_LICENSE_REQUIRED")
        self.assertEqual(d.owner_authorization, "SEPARATE_LICENSE_REQUIRED")

    def test_external_bases_are_not_adjudicated_or_promoted(self):
        for basis in (ExternalBasis.PLATFORM_DIRECT_GRANT, ExternalBasis.STATUTORY_EXCEPTION, ExternalBasis.SEPARATE_LICENSE):
            d = decide_owner_authorization(AccessMode.OFFICIAL_IKANT, external_basis=basis)
            self.assertEqual(d.code, "EXTERNAL_BASIS_NOT_ADJUDICATED")
            self.assertEqual(d.legal_status, "NOT_ADJUDICATED")
            self.assertEqual(d.ikant_conformance, "NOT_CONFORMING")
            self.assertFalse(d.epistemic_authority)

    def test_semantic_access_slice_has_zero_epistemic_authority(self):
        s = semantic_access_slice(AccessMode.AI_ASSISTED_STUDY, accepted_current_terms=True, clean_admission=True)
        self.assertEqual(s["control"]["code"], "OWNER_AUTHORIZED_CHAT_STUDY")
        self.assertEqual(s["epistemic_boundary"]["authority"], 0.0)
        self.assertFalse(s["epistemic_boundary"]["may_create_external_evidence"])
        self.assertFalse(s["epistemic_boundary"]["may_corroborate_claims"])

    def test_rights_policy_drift_blocks_probe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"; root.mkdir(); (root / "ikant").mkdir(); (root / "ikant" / "runtime.py").write_text("# fixture")
            for name in ("IKANT_ACCESS_CONTRACT.md", "BOOTSTRAP.json", "ADMISSION.json", "RIGHTS.json", "RIGHTS.md"):
                (root / name).write_text((ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")
            contract = (root / "IKANT_ACCESS_CONTRACT.md").read_text(encoding="utf-8")
            receipt = issue_receipt(contract, "I ACCEPT", presented_terms_sha256=digest(contract))
            save_receipt(root / ".ikant", receipt)
            self.assertEqual(probe(root, root / ".ikant", contract)["checks"]["RIGHTS_POLICY"]["status"], "AVAILABLE")
            payload = json.loads((root / "RIGHTS.json").read_text()); payload["tdm"]["reservation"] = 0
            (root / "RIGHTS.json").write_text(json.dumps(payload), encoding="utf-8")
            p = probe(root, root / ".ikant", contract)
            self.assertEqual(p["overall"], "BLOCKED")
            self.assertEqual(p["checks"]["RIGHTS_POLICY"]["status"], "UNAVAILABLE")

    def test_rights_invariants_are_critical(self):
        ids = set(critical_ids())
        self.assertTrue({"ADM-003", "ADM-004", "RGT-001", "RGT-002", "RGT-003", "RGT-004", "EPI-002"} <= ids)
        self.assertEqual(registry_manifest()["contract_version"], "0.12.0")


if __name__ == "__main__":
    unittest.main()
