from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from ikant.advanced_web_shell import (
    ADVANCED_WEB_SHELL_SCHEMA,
    SHELL_ACK_SCHEMA,
    SHELL_COMMAND_SCHEMA,
    AdvancedWebShellController,
    AdvancedWebShellError,
)
from ikant.web_frame import WEB_ACK_SCHEMA, WEB_FRAME_SCHEMA

ROOT = Path(__file__).parents[1]
SESSION = "SES-S8-TEST"
CLIENT = "client-1234567890"


def frame(seq: int = 1, *, sha: str = "a" * 64, session: str = SESSION) -> dict:
    return {
        "schema": WEB_FRAME_SCHEMA,
        "text": "+--+\n| sealed |\n+--+",
        "receipt": {
            "runtime_session_id": session,
            "epoch": 1,
            "frame_seq": seq,
            "frame_sha256": sha,
        },
        "delivery_state": "FRAME_PENDING",
        "acknowledged": False,
        "recovery": False,
    }


def command(opened: dict, seq: int, op: str, key: str, expected, payload=None) -> dict:
    return {
        "schema": SHELL_COMMAND_SCHEMA,
        "shell_id": opened["shell_id"],
        "client_id": CLIENT,
        "seq": seq,
        "op": op,
        "idempotency_key": key,
        "expected_frame": deepcopy(expected),
        "payload": {} if payload is None else payload,
    }


def web_ack(identity: dict) -> dict:
    return {
        "schema": WEB_ACK_SCHEMA,
        "runtime_session_id": identity["runtime_session_id"],
        "epoch": identity["epoch"],
        "frame_seq": identity["frame_seq"],
        "frame_sha256": identity["frame_sha256"],
        "visible_text": "+--+\n| sealed |\n+--+",
        "visible_text_sha256": identity["frame_sha256"],
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def shell_ack(opened: dict, seq: int, key: str, identity: dict) -> dict:
    return {
        "schema": SHELL_ACK_SCHEMA,
        "shell_id": opened["shell_id"],
        "client_id": CLIENT,
        "seq": seq,
        "idempotency_key": key,
        "frame_ack": web_ack(identity),
    }


class AdvancedWebShellV26Tests(unittest.TestCase):
    def setUp(self):
        self.shell = AdvancedWebShellController()
        self.opened = self.shell.open(SESSION, CLIENT)
        self.exec_count = 0
        self.ack_count = 0

    def execute_frame(self, op, payload):
        self.exec_count += 1
        return frame(self.exec_count)

    def acknowledge_frame(self, ack):
        self.ack_count += 1
        return {"acknowledged": True, "delivery_state": "DASHBOARD_LOCKED"}

    def sync_once(self, key="op-sync-123456789"):
        c = command(self.opened, 1, "SYNC", key, None)
        r = self.shell.execute(SESSION, c, self.execute_frame)
        a = self.shell.acknowledge(SESSION, shell_ack(self.opened, 1, key, r["expected_ack"]), self.acknowledge_frame)
        return r, a

    def test_open_is_single_writer_and_same_client_reopen_is_idempotent(self):
        reopened = self.shell.open(SESSION, CLIENT)
        self.assertEqual(reopened["shell_id"], self.opened["shell_id"])
        self.assertEqual(reopened["next_seq"], 1)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.open(SESSION, "other-client-123456")
        with self.assertRaises(AdvancedWebShellError):
            self.shell.open("SES-DRIFT", CLIENT)

    def test_projection_is_zero_authority_hsp_only(self):
        self.assertEqual(self.opened["schema"], ADVANCED_WEB_SHELL_SCHEMA)
        self.assertTrue(self.opened["single_writer"])
        self.assertEqual(self.opened["semantic_output_channel"], "HSPV2_SEALED_DASHBOARD_ONLY")
        self.assertFalse(self.opened["browser_is_authority"])
        self.assertFalse(self.opened["shell_state_is_authority"])
        self.assertEqual(self.opened["epistemic_authority"], 0.0)
        self.assertEqual(self.opened["execution_authority"], 0.0)

    def test_first_operation_must_be_unbound_sync(self):
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 1, "TURN", "op-turn-123456789", None, {"text": "ciao"}), self.execute_frame)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 1, "SYNC", "op-sync-123456789", {"runtime_session_id":SESSION,"epoch":1,"frame_seq":1,"frame_sha256":"a"*64}), self.execute_frame)

    def test_pending_exact_command_replay_never_executes_twice_and_stays_pending(self):
        c = command(self.opened, 1, "SYNC", "op-sync-123456789", None)
        first = self.shell.execute(SESSION, c, self.execute_frame)
        second = self.shell.execute(SESSION, deepcopy(c), self.execute_frame)
        self.assertEqual(self.exec_count, 1)
        self.assertEqual(second["frame"], first["frame"])
        self.assertTrue(second["operation"]["replay"])
        self.assertTrue(second["pending_operation"])
        self.assertEqual(second["pending_seq"], 1)
        reopened = self.shell.open(SESSION, CLIENT)
        self.assertIsNotNone(reopened["pending_response"])
        self.assertTrue(reopened["pending_response"]["pending_operation"])

    def test_different_command_while_pending_is_denied(self):
        c = command(self.opened, 1, "SYNC", "op-sync-123456789", None)
        self.shell.execute(SESSION, c, self.execute_frame)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 1, "SYNC", "op-sync-987654321", None), self.execute_frame)

    def test_exact_ack_advances_sequence_and_exact_ack_replay_is_non_committing(self):
        r, acked = self.sync_once()
        self.assertEqual(self.ack_count, 1)
        self.assertEqual(acked["next_seq"], 2)
        self.assertEqual(acked["last_acked_frame"], r["expected_ack"])
        a = shell_ack(self.opened, 1, "op-sync-123456789", r["expected_ack"])
        replay = self.shell.acknowledge(SESSION, deepcopy(a), self.acknowledge_frame)
        self.assertTrue(replay["replay"])
        self.assertEqual(self.ack_count, 1)

    def test_stale_sequence_and_expected_frame_drift_fail_closed(self):
        r, acked = self.sync_once()
        expected = acked["last_acked_frame"]
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 1, "SYNC", "op-stale-12345678", expected), self.execute_frame)
        wrong = dict(expected);wrong["frame_sha256"] = "b" * 64
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 2, "SYNC", "op-next-123456789", wrong), self.execute_frame)

    def test_idempotency_key_cannot_be_reused_for_later_operation(self):
        _, acked = self.sync_once("op-shared-12345678")
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 2, "SYNC", "op-shared-12345678", acked["last_acked_frame"]), self.execute_frame)

    def test_malformed_downstream_frame_does_not_consume_idempotency_key(self):
        c = command(self.opened, 1, "SYNC", "op-retry-123456789", None)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, c, lambda _op, _payload: {"schema": "bad"})
        good = self.shell.execute(SESSION, deepcopy(c), self.execute_frame)
        self.assertEqual(good["status"], "FRAME_PENDING")
        self.assertEqual(self.exec_count, 1)

    def test_ack_must_bind_pending_operation_and_exact_frame(self):
        c = command(self.opened, 1, "SYNC", "op-sync-123456789", None)
        r = self.shell.execute(SESSION, c, self.execute_frame)
        bad_seq = shell_ack(self.opened, 2, "op-sync-123456789", r["expected_ack"])
        with self.assertRaises(AdvancedWebShellError):
            self.shell.acknowledge(SESSION, bad_seq, self.acknowledge_frame)
        bad_frame = shell_ack(self.opened, 1, "op-sync-123456789", {**r["expected_ack"], "frame_sha256":"c"*64})
        with self.assertRaises(AdvancedWebShellError):
            self.shell.acknowledge(SESSION, bad_frame, self.acknowledge_frame)
        self.assertEqual(self.ack_count, 0)

    def test_turn_payload_is_exact_and_bounded(self):
        _, acked = self.sync_once()
        expected = acked["last_acked_frame"]
        for payload in ({"text":""},{"text":"x\x00y"},{"text":"x","extra":1}):
            with self.subTest(payload=payload):
                with self.assertRaises(AdvancedWebShellError):
                    self.shell.execute(SESSION, command(self.opened, 2, "TURN", "op-turn-123456789", expected, payload), self.execute_frame)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 2, "TURN", "op-turn-123456789", expected, {"text":"x"*65537}), self.execute_frame)

    def test_nonturn_payload_and_unknown_operation_are_denied(self):
        _, acked = self.sync_once()
        expected = acked["last_acked_frame"]
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 2, "EXIT", "op-exit-123456789", expected, {"x":1}), self.execute_frame)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, command(self.opened, 2, "EVAL", "op-eval-123456789", expected), self.execute_frame)

    def test_returned_frame_must_bind_runtime_session(self):
        c = command(self.opened, 1, "SYNC", "op-sync-123456789", None)
        with self.assertRaises(AdvancedWebShellError):
            self.shell.execute(SESSION, c, lambda _op,_payload: frame(1, session="OTHER"))

    def test_sync_can_observe_already_released_runtime_without_frame(self):
        c = command(self.opened, 1, "SYNC", "op-sync-123456789", None)
        out = self.shell.execute(SESSION, c, lambda _op,_payload: {"released":True})
        self.assertEqual(out["status"], "RELEASED")
        self.assertEqual(out["next_seq"], 2)
        self.assertIsNone(out["frame"])

    def test_canonical_pwa_uses_v2_shell_and_has_no_parallel_active_error_surface(self):
        app = (ROOT/"ikant"/"web"/"app.js").read_text(encoding="utf-8")
        html = (ROOT/"ikant"/"web"/"index.html").read_text(encoding="utf-8")
        http = (ROOT/"ikant"/"local_http.py").read_text(encoding="utf-8")
        local_app = (ROOT/"ikant"/"local_app.py").read_text(encoding="utf-8")
        self.assertIn("/api/v2/shell/open", app)
        self.assertIn("/api/v2/shell/command", app)
        self.assertIn("/api/v2/shell/ack", app)
        self.assertNotIn("'/api/v1/turn'", app)
        self.assertNotIn('id="active-error"', html)
        self.assertIn("_legacy_active_blocked", http)
        for route in ("/api/v1/frame","/api/v1/frame/ack","/api/v1/turn","/api/v1/resume","/api/v1/initialize"):
            self.assertIn(route, http)
        self.assertIn("AdvancedWebShellService", local_app)


if __name__ == "__main__":
    unittest.main()
