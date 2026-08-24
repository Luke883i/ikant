from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ikant.chat_session import ChatLog
from ikant.cognitive import record_surface_a
from ikant.runtime_recovery import (
    RECOVERY_SCHEMA,
    materialize_recovery_frame,
    reconcile_interrupted_turn,
    reconcile_surface_a_chat,
    recover_work_projection,
    verified_recovery,
)
from ikant.session_egress import activate_runtime_egress, existing_runtime_egress
from tests.helpers import active_runtime


class RuntimeRecoveryS17bisTests(unittest.TestCase):
    def _runtime(self, tmp: Path):
        rt = active_runtime(tmp, durable=True)
        activate_runtime_egress(rt, initialization=True)
        return rt

    def test_sealed_frame_is_recovery_source_without_reexecution(self):
        with tempfile.TemporaryDirectory() as raw:
            rt = self._runtime(Path(raw))
            try:
                guard = existing_runtime_egress(rt)
                receipt = guard.seal_frame("sealed canonical frame", kind="TURN", cycle_id="cycle-sealed")
                out = verified_recovery(rt)
                self.assertEqual(out["schema"], RECOVERY_SCHEMA)
                self.assertEqual(out["state"], "SEALED_FRAME_PENDING")
                self.assertEqual(out["frame_sha256"], receipt.frame_sha256)
                self.assertFalse(out["model_reexecuted"])
                self.assertFalse(out["planner_reexecuted"])
                self.assertFalse(out["material_driver_reexecuted"])
                self.assertEqual(out["epistemic_authority"], 0.0)
                self.assertEqual(out["execution_authority"], 0.0)
            finally:
                rt.close()

    def test_interrupted_unsealed_turn_materializes_recovery_not_answer(self):
        with tempfile.TemporaryDirectory() as raw:
            rt = self._runtime(Path(raw))
            try:
                cog = rt.runtime.setdefault("cognitive", {})
                cog["pending_surface_a_cycle_id"] = "cycle-interrupted"
                cog["pending_interaction_contract"] = {"schema": "test"}
                rt._write_runtime()
                before = verified_recovery(rt)
                self.assertEqual(before["state"], "INTERRUPTED_UNSEALED")
                frame = materialize_recovery_frame(rt)
                self.assertIsNotNone(frame)
                self.assertEqual(frame["receipt"]["kind"], "RECOVERY")
                self.assertEqual(frame["receipt"]["cycle_id"], "cycle-interrupted")
                self.assertIn("Nessuna risposta è stata rigenerata", frame["primary_text"])
                self.assertEqual(rt.runtime["cognitive"]["pending_surface_a_cycle_id"], "cycle-interrupted")
            finally:
                rt.close()

    def test_interrupted_cleanup_is_explicit_and_idempotent_after_recovery_ack_state(self):
        with tempfile.TemporaryDirectory() as raw:
            rt = self._runtime(Path(raw))
            try:
                cog = rt.runtime.setdefault("cognitive", {})
                cog["pending_surface_a_cycle_id"] = "cycle-interrupted"
                cog["pending_interaction_contract"] = {"schema": "test"}
                rt._write_runtime()
                first = verified_recovery(rt)
                out = reconcile_interrupted_turn(rt, first)
                self.assertNotIn("pending_surface_a_cycle_id", rt.runtime.get("cognitive", {}))
                self.assertNotIn("pending_interaction_contract", rt.runtime.get("cognitive", {}))
                self.assertEqual(rt.runtime["cognitive"]["last_runtime_recovery"]["cycle_id"], "cycle-interrupted")
                self.assertFalse(out["model_reexecuted"])
            finally:
                rt.close()

    def test_surface_a_unsealed_reconciles_chat_once_without_new_response_node(self):
        with tempfile.TemporaryDirectory() as raw:
            rt = self._runtime(Path(raw))
            try:
                cycle = "cycle-surface-a"
                session = rt.runtime["session_id"]
                log = ChatLog(rt.state_dir / "chat" / "transcript.jsonl", runtime_session_id=session)
                user = log.append("user", "domanda di recovery", cycle_id=cycle, intention_node_id="intent-recovery")
                receipt = record_surface_a(rt, cycle, "Risposta validata recuperabile dopo un riavvio locale.")
                node_count = len(rt.nodes)
                before = verified_recovery(rt)
                self.assertEqual(before["state"], "SURFACE_A_UNSEALED")
                self.assertEqual(before["response_id"], receipt["response_id"])
                first = reconcile_surface_a_chat(rt, before)
                second = reconcile_surface_a_chat(rt, first)
                self.assertTrue(first["chat_reconciled"])
                self.assertFalse(second["chat_reconciled"])
                rows = log.rows()
                replies = [r for r in rows if r.get("role") == "ikant" and r.get("reply_to_seq") == user["seq"]]
                self.assertEqual(len(replies), 1)
                self.assertEqual(replies[0]["response_id"], receipt["response_id"])
                self.assertEqual(len(rt.nodes), node_count)
            finally:
                rt.close()

    def test_pending_cycle_with_validated_surface_a_is_integrity_conflict(self):
        with tempfile.TemporaryDirectory() as raw:
            rt = self._runtime(Path(raw))
            try:
                cycle = "cycle-conflict"
                record_surface_a(rt, cycle, "Risposta valida che non può coesistere con pending cognitivo.")
                rt.runtime.setdefault("cognitive", {})["pending_surface_a_cycle_id"] = cycle
                rt._write_runtime()
                with self.assertRaisesRegex(RuntimeError, "already has validated Surface A"):
                    verified_recovery(rt)
            finally:
                rt.close()

    def test_recovered_work_is_derived_zero_authority(self):
        recovery = {"state": "SEALED_FRAME_PENDING", "cycle_id": "cycle-1", "recovery_basis": "DURABLE_EGRESS_FRAME"}
        out = recover_work_projection({}, recovery)
        self.assertEqual(out["phase"], "SEALED")
        self.assertTrue(out["active"])
        self.assertEqual(out["facts"]["recovery_source"], "DURABLE_EGRESS_FRAME")
        self.assertEqual(out["epistemic_authority"], 0.0)
        self.assertEqual(out["execution_authority"], 0.0)

    def test_pre_active_is_explicit_recovery_state(self):
        class Stub:
            runtime = {"status": "INITIALIZING"}
        out = verified_recovery(Stub())
        self.assertEqual(out["state"], "PRE_ACTIVE")
        self.assertFalse(out["recovery_required"])

    def test_real_process_restart_oracle(self):
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run([sys.executable, "scripts/runtime_recovery_process_oracle.py"], cwd=root, capture_output=True, text=True, check=True)
        receipt = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["real_process_restart"])
        self.assertTrue(receipt["sealed_frame_byte_identity_preserved"])

    def test_independent_source_surface_census(self):
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run([sys.executable, "scripts/surface_census_s17bis.py"], cwd=root, capture_output=True, text=True, check=True)
        receipt = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["independent_of_surface_manifest"])

    def test_recovery_module_has_no_model_or_planner_import(self):
        source = (Path(__file__).resolve().parents[1] / "ikant" / "runtime_recovery.py").read_text(encoding="utf-8")
        self.assertNotIn("model.complete", source)
        self.assertNotIn("complete_surface_a", source)
        self.assertNotIn("workspace_plan", source)
        self.assertNotIn("execution_driver", source)
        self.assertIn("material_driver_reexecuted", source)


if __name__ == "__main__":
    unittest.main()
