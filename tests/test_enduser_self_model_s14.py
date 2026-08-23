from __future__ import annotations

import unittest
from pathlib import Path

from ikant.enduser_identity import ENDUSER_SCHEMA, enduser_projection
from ikant.public_v1 import conversation_projection

ROOT = Path(__file__).resolve().parents[1]


def _parts(index: int = 1):
    session = f"session-{index}"
    cycle = f"cycle-{index}"
    trace = {
        "schema": "ikant-cognitive-trace-projection/v1.3",
        "cycle_id": cycle,
        "private_chain_of_thought": False,
        "raw_model_rationale": False,
        "stages": [
            {"id": "UNDERSTAND", "label": "Capisco", "status": "complete", "facts": {"mined_objects": 2}},
            {"id": "CONNECT", "label": "Collego", "status": "complete", "facts": {"objects": 3}},
            {"id": "CHECK", "label": "Verifico", "status": "complete", "facts": {"conflicts": 0}},
            {"id": "GOVERN", "label": "Valuto", "status": "complete", "facts": {"material_action": "PROPOSE_ONLY"}},
            {"id": "FORMULATE", "label": "Formulo", "status": "complete", "facts": {"route": "managed-local"}},
            {"id": "INTEGRATE", "label": "Integro", "status": "complete", "facts": {"response_memory": True}},
        ],
    }
    conversation = {
        "runtime_session_id": session,
        "integrity_verified": True,
        "last_sha256": "a" * 64,
        "record_count": 40,
        "visible_record_count": 32,
        "records": [
            {"role": "user", "cycle_id": cycle, "text": "x"},
            {"role": "ikant", "cycle_id": cycle, "text": "y"},
        ],
    }
    experience = {
        "runtime_session_id": session,
        "cycle_id": cycle,
        "state": "Pronto",
        "trace": trace,
        "timing": {"phases": [{"phase": "PRIMARY_DELIVERED"}]},
        "generation_route": "managed-local",
    }
    epistemic = {"cycle_id": cycle, "truth_certified": False}
    capabilities = {"runtime_session_id": session, "cycle_id": cycle, "services": []}
    return conversation, experience, epistemic, capabilities


class EndUserSelfModelS14Tests(unittest.TestCase):
    def test_happy_path_is_consistent_session_bound_and_zero_authority(self):
        c, e, p, k = _parts()
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertEqual(out["schema"], ENDUSER_SCHEMA)
        self.assertEqual(out["audit"]["status"], "CONSISTENT")
        self.assertTrue(out["identity"]["runtime_session_bound"])
        self.assertFalse(out["identity"]["consciousness_claimed"])
        self.assertFalse(out["neuromodel"]["biological_equivalence_claimed"])
        self.assertEqual(out["epistemic_authority"], 0.0)
        self.assertEqual(out["execution_authority"], 0.0)

    def test_cycle_and_session_drift_degrade_instead_of_being_reconciled_silently(self):
        c, e, p, k = _parts()
        p["cycle_id"] = "other-cycle"
        k["runtime_session_id"] = "other-session"
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertEqual(out["audit"]["status"], "DEGRADED")
        self.assertFalse(out["audit"]["cycle_coherent"])
        self.assertFalse(out["audit"]["session_coherent"])

    def test_hash_integrity_never_becomes_truth_certification(self):
        c, e, p, k = _parts()
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertTrue(out["audit"]["conversation_integrity_verified"])
        self.assertTrue(out["audit"]["hash_integrity_is_not_truth"])
        self.assertFalse(out["audit"]["truth_certified"])

    def test_visible_history_boundary_is_explicit_and_count_drift_degrades(self):
        c, e, p, k = _parts()
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertTrue(out["audit"]["conversation_truncated"])
        self.assertEqual(out["audit"]["visible_record_count"], 32)
        self.assertEqual(out["audit"]["record_count"], 40)
        c["record_count"] = 2
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertEqual(out["audit"]["status"], "DEGRADED")
        self.assertFalse(out["audit"]["record_counts_coherent"])

    def test_private_reasoning_contract_violation_degrades_public_trace(self):
        c, e, p, k = _parts()
        e["trace"]["private_chain_of_thought"] = True
        out = enduser_projection(conversation=c, experience=e, epistemic_value=p, capabilities=k)
        self.assertEqual(out["audit"]["status"], "DEGRADED")
        self.assertFalse(out["audit"]["trace_contract_valid"])
        self.assertFalse(out["neuromodel"]["private_chain_of_thought_exposed"])

    def test_empty_conversation_declares_zero_visible_and_total_records(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = conversation_projection(td)
        self.assertEqual(out["record_count"], 0)
        self.assertEqual(out["visible_record_count"], 0)
        self.assertFalse(out["truncated"])

    def test_renderer_is_read_only_progressive_disclosure(self):
        js = (ROOT / "ikant/web/enduser.js").read_text(encoding="utf-8")
        self.assertIn("/api/v8/public", js)
        self.assertIn("Audit del ciclo", js)
        self.assertIn("Modello cognitivo sintetico", js)
        self.assertIn("non prova coscienza", js)
        self.assertIn("textContent", js)
        self.assertNotIn("shellCommand", js)
        self.assertNotIn("/api/v2/shell", js)
        self.assertNotIn("method:'POST'", js)

    def test_public_asset_composes_renderer_and_cache_boundary_changes(self):
        http = (ROOT / "ikant/bootstrap_http.py").read_text(encoding="utf-8")
        sw = (ROOT / "ikant/web/sw.js").read_text(encoding="utf-8")
        public = (ROOT / "ikant/public_v1.py").read_text(encoding="utf-8")
        self.assertIn("assets_dir/'public-v1.js',assets_dir/'enduser.js'", http)
        self.assertIn("enduser-s14", sw)
        self.assertIn('"enduser": enduser', public)
        self.assertIn("enduser_identity_is_session_bound_projection", public)


if __name__ == "__main__":
    unittest.main()
