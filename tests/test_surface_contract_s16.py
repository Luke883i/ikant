from __future__ import annotations

import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from ikant.foundation import default_experiment_config, save_experiment_config
from ikant.reactive_http import build_server
from ikant.surface_contract import (
    CONFIG_EFFECT_SCHEMA,
    SURFACE_CONTRACT_SCHEMA,
    config_effect_projection,
    record_config_effect,
    surface_manifest,
    surface_snapshot,
)


class _SlowSurfaceService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.web_adapter = None

    def bind_web_adapter(self, adapter) -> None:
        self.web_adapter = adapter

    def shell_command(self, body):
        time.sleep(0.25)
        path = self.root / ".ikant" / "runtime.json"
        runtime = json.loads(path.read_text(encoding="utf-8"))
        cognitive = runtime.setdefault("cognitive", {})
        cognitive["last_surface_a_cycle_id"] = "cycle-s16-http"
        cognitive["last_surface_a_generation"] = {
            "cycle_id": "cycle-s16-http",
            "source": "MODEL",
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        path.write_text(json.dumps(runtime), encoding="utf-8")
        return {
            "schema": "ikant-s16-http-fixture/v1-test",
            "frame": {
                "receipt": {"cycle_id": "cycle-s16-http"},
                "generation": {"cycle_id": "cycle-s16-http", "source": "MODEL"},
            },
        }

    def shell_ack(self, body):
        return {"acknowledged": True}


class SurfaceContractS16Tests(unittest.TestCase):
    def test_manifest_is_all_and_only_and_profiles_are_semantically_identical(self):
        manifest = surface_manifest()
        ids = [row["id"] for row in manifest["abstractions"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            set(ids),
            {
                "admission_lifecycle",
                "conversation_turn",
                "generation_config",
                "cognitive_trace",
                "epistemic_workspace",
                "capability_catalog",
                "runtime_systems",
                "enduser_identity_audit",
                "reactive_work",
                "artifacts",
                "bootstrap_diagnostics",
                "voice_candidate",
            },
        )
        self.assertNotIn("commercial_assist", ids)
        self.assertNotIn("native_app_open", ids)
        profiles = {row["id"]: row for row in manifest["surface_profiles"]}
        self.assertEqual(profiles["webapp"]["semantic_contract_sha256"], manifest["semantic_contract_sha256"])
        self.assertEqual(profiles["floating_pwa_profile"]["semantic_contract_sha256"], manifest["semantic_contract_sha256"])
        self.assertFalse(profiles["floating_pwa_profile"]["native_os_overlay_claimed"])
        for row in manifest["abstractions"]:
            self.assertEqual(row["surfaces"], ["webapp", "floating_pwa_profile"])
            if row["id"] != "admission_lifecycle":
                self.assertEqual(row["authority_effect"], "NONE")

    def test_config_effect_receipt_separates_saved_current_and_effective_cycle_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".ikant"
            state.mkdir()
            (state / "runtime.json").write_text(
                json.dumps(
                    {
                        "status": "ACTIVE",
                        "session_id": "s16-receipt",
                        "cognitive": {"last_surface_a_cycle_id": "cycle-1"},
                    }
                ),
                encoding="utf-8",
            )
            config = default_experiment_config()
            frame = {
                "receipt": {"cycle_id": "cycle-1"},
                "generation": {"cycle_id": "cycle-1", "source": "MODEL"},
            }
            receipt = record_config_effect(root, config=config, frame=frame)
            self.assertEqual(receipt["schema"], CONFIG_EFFECT_SCHEMA)
            self.assertTrue(receipt["final_surface_effect_confirmed"])
            projected = config_effect_projection(root, config=config)
            self.assertEqual(projected["status"], "CONFIRMED_CURRENT")
            self.assertTrue(projected["integrity_verified"])
            saved = save_experiment_config(
                root,
                {
                    "expected_revision": 0,
                    "meta_prompt": "Preferisci risposte strutturate.",
                    "guardrails": {
                        "evidence_mode": "strict",
                        "conflict_mode": "surface",
                        "interpretive_hypotheses": "bounded",
                        "max_reply_words": 160,
                    },
                },
            )
            changed = config_effect_projection(root, config=saved)
            self.assertEqual(changed["status"], "CONFIRMED_CYCLE_CONFIG_NOW_CHANGED")
            self.assertEqual(changed["cycle_config_revision"], 0)
            self.assertEqual(changed["current_config_revision"], 1)

    def test_fallback_and_local_routes_never_claim_confirmed_generation_effect(self):
        for source, expected in (
            ("OPERATIONAL_FALLBACK", "MODEL_CONFIG_ATTEMPTED_FINAL_FALLBACK"),
            ("LOCAL_INTERACTION_KERNEL", "BYPASSED_NON_MODEL_ROUTE"),
        ):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = root / ".ikant"
                state.mkdir()
                (state / "runtime.json").write_text(
                    json.dumps(
                        {
                            "status": "ACTIVE",
                            "session_id": "s16-route",
                            "cognitive": {"last_surface_a_cycle_id": "cycle-route"},
                        }
                    ),
                    encoding="utf-8",
                )
                config = default_experiment_config()
                record_config_effect(
                    root,
                    config=config,
                    frame={
                        "receipt": {"cycle_id": "cycle-route"},
                        "generation": {"cycle_id": "cycle-route", "source": source},
                    },
                )
                out = config_effect_projection(root, config=config)
                self.assertEqual(out["status"], expected)
                self.assertFalse(out["final_surface_effect_confirmed"])

    def test_running_snapshot_is_nonblocking_and_preserves_semantic_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".ikant"
            state.mkdir()
            (state / "runtime.json").write_text(json.dumps({"status": "ACTIVE", "session_id": "overlay-s16"}), encoding="utf-8")
            service = _SlowSurfaceService(root)
            baseline = surface_snapshot(
                service,
                work={"schema": "ikant-reactive-work-state/v1-test", "active": False, "terminal": False, "phase": "IDLE"},
            )
            started = time.perf_counter()
            overlay = surface_snapshot(
                service,
                work={"schema": "ikant-reactive-work-state/v1-test", "active": True, "terminal": False, "work_id": "w-1", "phase": "RUNNING"},
            )
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 0.1)
            self.assertEqual(overlay["snapshot_mode"], "WORK_OVERLAY")
            self.assertEqual(overlay["consistency"], "NONBLOCKING_OVER_STABLE_BASE")
            self.assertEqual(overlay["semantic_contract_sha256"], baseline["semantic_contract_sha256"])
            self.assertEqual(overlay["base_snapshot_sha256"], baseline["snapshot_sha256"])
            self.assertEqual(overlay["work"]["phase"], "RUNNING")

    def test_real_http_surface_stays_observable_during_synchronous_turn_and_receipts_after_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".ikant"
            state.mkdir()
            (state / "runtime.json").write_text(json.dumps({"status": "ACTIVE", "session_id": "http-s16"}), encoding="utf-8")
            service = _SlowSurfaceService(root)
            server, pairing = build_server(service, host="127.0.0.1", port=0, assets_dir=Path(__file__).resolve().parents[1] / "ikant" / "web")
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            thread.start()
            port = int(server.server_address[1])
            origin = f"http://127.0.0.1:{port}"

            def request(method: str, path: str, body=None, token=None):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                headers = {"Accept": "application/json", "Origin": origin}
                if token:
                    headers["Authorization"] = "Bearer " + token
                raw = None
                if body is not None:
                    raw = json.dumps(body).encode()
                    headers["Content-Type"] = "application/json"
                    headers["Content-Length"] = str(len(raw))
                conn.request(method, path, body=raw, headers=headers)
                response = conn.getresponse()
                payload = response.read()
                status = response.status
                conn.close()
                return status, json.loads(payload.decode()) if payload else {}

            try:
                status, paired = request("POST", "/api/v1/pair", {"code": pairing.code})
                self.assertEqual(status, 200)
                token = paired["bearer_token"]
                status, baseline = request("GET", "/api/v10/surface", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(baseline["schema"], SURFACE_CONTRACT_SCHEMA)
                self.assertEqual(baseline["snapshot_mode"], "STABLE")
                turn_result = {}

                def turn():
                    turn_result["value"] = request("POST", "/api/v2/shell/command", {"op": "TURN", "payload": {"text": "slow surface contract turn"}}, token)

                worker = threading.Thread(target=turn)
                worker.start()
                deadline = time.monotonic() + 1.0
                running = None
                max_elapsed = 0.0
                while time.monotonic() < deadline:
                    started = time.perf_counter()
                    status, candidate = request("GET", "/api/v10/surface", token=token)
                    max_elapsed = max(max_elapsed, time.perf_counter() - started)
                    if status == 200 and candidate.get("work", {}).get("phase") == "RUNNING":
                        running = candidate
                        break
                    time.sleep(0.01)
                self.assertIsNotNone(running)
                self.assertLess(max_elapsed, 0.2)
                self.assertEqual(running["snapshot_mode"], "WORK_OVERLAY")
                self.assertEqual(running["semantic_contract_sha256"], baseline["semantic_contract_sha256"])
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive())
                self.assertEqual(turn_result["value"][0], 200)
                status, sealed = request("GET", "/api/v10/surface", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(sealed["work"]["phase"], "SEALED")
                self.assertEqual(sealed["config_effect"]["status"], "CONFIRMED_CURRENT")
                status, ack = request("POST", "/api/v2/shell/ack", {}, token)
                self.assertEqual(status, 200)
                self.assertTrue(ack["acknowledged"])
                status, delivered = request("GET", "/api/v10/surface", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(delivered["work"]["phase"], "DELIVERED")
                self.assertFalse(delivered["work"]["active"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=1)


if __name__ == "__main__":
    unittest.main()
