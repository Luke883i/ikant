from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ikant.enduser_identity import local_identity_projection
from ikant.foundation import default_experiment_config, save_experiment_config
from ikant.managed_runtime import _binding_digest
from ikant.runtime_epoch import RuntimeEpochError, compact_epoch, materialize_runtime_epoch, verify_epoch_ledger
from ikant.surface_contract import config_effect_projection, record_config_effect, surface_snapshot


class _SurfaceService:
    def __init__(self, root: Path) -> None:
        self.root = root
    def lifecycle(self):
        return {"state": "ACTIVE"}
    def product_status(self):
        return {"stage": "READY", "attempt": 1, "voice": {"configured": False}}


def _write_contract(root: Path, *, version: str = "0.17.0", convergence: str = "S16") -> None:
    (root / "PRODUCT_CONTRACT.json").write_text(json.dumps({
        "schema": "ikant-product-contract/v0.29-test",
        "product_version": "0.29.0a1",
        "contract_version": version,
        "constitutional_convergence": convergence,
        "slices": [{"id": "S1"}],
    }), encoding="utf-8")


def _runtime(root: Path, *, session: str = "session-s17", cycle: str | None = None, epoch: dict | None = None) -> dict:
    value = {"status": "ACTIVE", "session_id": session, "contract_sha256": "c" * 64}
    if cycle:
        value["cognitive"] = {"last_surface_a_cycle_id": cycle}
    if epoch:
        value["runtime_epoch"] = compact_epoch(epoch)
    (root / ".ikant").mkdir(parents=True, exist_ok=True)
    (root / ".ikant" / "runtime.json").write_text(json.dumps(value), encoding="utf-8")
    return value


def _write_model(root: Path, *, model_id: str = "model-a", model_sha: str = "a" * 64, status: str = "READY") -> str:
    binding = {
        "manifest_sha256": "1" * 64,
        "engine": {"id": "llama.cpp", "version": "b9999", "platform": "linux-x86_64", "artifact_sha256": "2" * 64},
        "model": {"id": model_id, "revision": "3" * 40, "sha256": model_sha},
    }
    digest = _binding_digest(binding)
    projection = {
        "schema": "ikant-managed-local-runtime/v0.23-test",
        "status": status,
        "managed": True,
        "manifest_sha256": binding["manifest_sha256"],
        "binding_sha256": digest,
        "engine": binding["engine"],
        "model": binding["model"],
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    (root / ".ikant" / "model-runtime.json").write_text(json.dumps(projection), encoding="utf-8")
    return digest


class RuntimeEpochS17Tests(unittest.TestCase):
    def _root(self):
        tmp = tempfile.TemporaryDirectory(); root = Path(tmp.name); _runtime(root); _write_contract(root); _write_model(root); return tmp, root

    def test_same_material_and_live_process_status_reuse_one_epoch(self):
        tmp, root = self._root()
        with tmp:
            first = materialize_runtime_epoch(root, require_managed_binding=True)
            second = materialize_runtime_epoch(root, require_managed_binding=True)
            self.assertEqual(first["epoch_id"], second["epoch_id"]); self.assertEqual(first["ordinal"], 1)
            raw = json.loads((root / ".ikant" / "model-runtime.json").read_text(encoding="utf-8")); raw["status"] = "RESTARTING"; (root / ".ikant" / "model-runtime.json").write_text(json.dumps(raw), encoding="utf-8")
            third = materialize_runtime_epoch(root, require_managed_binding=True)
            self.assertEqual(third["epoch_id"], first["epoch_id"]); self.assertEqual(verify_epoch_ledger(root)["events"], 1)
            self.assertFalse(third["component"]["live_status_in_epoch_identity"])

    def test_component_config_product_surface_and_session_changes_create_new_epoch_events(self):
        tmp, root = self._root()
        with tmp:
            e1 = materialize_runtime_epoch(root, require_managed_binding=True)
            _write_model(root, model_id="model-b", model_sha="b" * 64); e2 = materialize_runtime_epoch(root, require_managed_binding=True)
            self.assertEqual(e2["ordinal"], e1["ordinal"] + 1)
            saved = save_experiment_config(root, {"expected_revision": 0, "meta_prompt": "Prefer concise structure.", "guardrails": {"evidence_mode": "strict", "conflict_mode": "surface", "interpretive_hypotheses": "bounded", "max_reply_words": 160}})
            self.assertEqual(saved["revision"], 1); e3 = materialize_runtime_epoch(root, require_managed_binding=True); self.assertEqual(e3["ordinal"], e2["ordinal"] + 1)
            _write_contract(root, version="0.18.0", convergence="S16bis"); e4 = materialize_runtime_epoch(root, require_managed_binding=True); self.assertEqual(e4["ordinal"], e3["ordinal"] + 1)
            e5 = materialize_runtime_epoch(root, require_managed_binding=True, surface_contract_sha256="f" * 64); self.assertEqual(e5["ordinal"], e4["ordinal"] + 1)
            runtime = json.loads((root / ".ikant" / "runtime.json").read_text(encoding="utf-8")); runtime["session_id"] = "session-s17-new"; (root / ".ikant" / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
            e6 = materialize_runtime_epoch(root, require_managed_binding=True, surface_contract_sha256="f" * 64); self.assertEqual(e6["ordinal"], e5["ordinal"] + 1)

    def test_invalid_binding_ledger_tamper_and_config_rollback_fail_closed(self):
        tmp, root = self._root()
        with tmp:
            e1 = materialize_runtime_epoch(root, require_managed_binding=True)
            raw = json.loads((root / ".ikant" / "model-runtime.json").read_text(encoding="utf-8")); raw["binding_sha256"] = "0" * 64; (root / ".ikant" / "model-runtime.json").write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(RuntimeEpochError): materialize_runtime_epoch(root, require_managed_binding=True)
            _write_model(root); save_experiment_config(root, {"expected_revision": 0, "meta_prompt": "x", "guardrails": {"evidence_mode": "baseline", "conflict_mode": "surface", "interpretive_hypotheses": "bounded", "max_reply_words": 160}}); materialize_runtime_epoch(root, require_managed_binding=True)
            (root / ".ikant" / "experiment-config.json").write_text(json.dumps(default_experiment_config()), encoding="utf-8")
            with self.assertRaises(RuntimeEpochError): materialize_runtime_epoch(root, require_managed_binding=True)
            lines = (root / ".ikant" / "runtime-epochs.jsonl").read_text(encoding="utf-8").splitlines(); row = json.loads(lines[0]); row["material_sha256"] = "d" * 64; lines[0] = json.dumps(row); (root / ".ikant" / "runtime-epochs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeEpochError): verify_epoch_ledger(root)
            self.assertEqual(e1["epistemic_authority"], 0.0)

    def test_current_cache_is_recoverable_from_canonical_ledger_without_new_epoch(self):
        tmp, root = self._root()
        with tmp:
            first = materialize_runtime_epoch(root, require_managed_binding=True); (root / ".ikant" / "runtime-epoch.json").unlink()
            recovered = materialize_runtime_epoch(root, require_managed_binding=True)
            self.assertEqual(recovered["epoch_id"], first["epoch_id"]); self.assertEqual(verify_epoch_ledger(root)["events"], 1); self.assertTrue((root / ".ikant" / "runtime-epoch.json").is_file())

    def test_surface_snapshot_and_config_receipt_distinguish_current_from_prior_known_epoch(self):
        tmp, root = self._root()
        with tmp:
            e1 = materialize_runtime_epoch(root, require_managed_binding=True); runtime = _runtime(root, cycle="cycle-s17", epoch=e1); _write_model(root)
            service = _SurfaceService(root); stable = surface_snapshot(service, work={"active": False, "terminal": True, "phase": "IDLE"})
            self.assertEqual(stable["runtime_epoch"]["epoch_id"], e1["epoch_id"]); self.assertEqual(stable["public"]["enduser"]["identity"]["label"], "iKant locale")
            record_config_effect(root, config=default_experiment_config(), frame={"receipt": {"cycle_id": "cycle-s17"}, "generation": {"cycle_id": "cycle-s17", "source": "MODEL"}})
            _write_model(root, model_id="model-b", model_sha="b" * 64); e2 = materialize_runtime_epoch(root, require_managed_binding=True); runtime["runtime_epoch"] = compact_epoch(e2); (root / ".ikant" / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
            receipt = config_effect_projection(root, config=default_experiment_config()); self.assertEqual(receipt["runtime_epoch_binding"], "PRIOR_KNOWN")
            overlay = surface_snapshot(service, work={"active": True, "terminal": False, "phase": "RUNNING", "work_id": "w-s17"}); self.assertEqual(overlay["consistency"], "NONBLOCKING_EPOCH_REBASE_REQUIRED"); self.assertEqual(overlay["runtime_epoch"]["epoch_id"], e2["epoch_id"])

    def test_identity_remains_ikant_across_component_epoch_change(self):
        tmp, root = self._root()
        with tmp:
            e1 = materialize_runtime_epoch(root, require_managed_binding=True); a = local_identity_projection(runtime_session_id="session-s17", state="Pronto", runtime_epoch=e1)
            _write_model(root, model_id="model-b", model_sha="b" * 64); e2 = materialize_runtime_epoch(root, require_managed_binding=True); b = local_identity_projection(runtime_session_id="session-s17", state="Pronto", runtime_epoch=e2)
            self.assertEqual(a["label"], "iKant locale"); self.assertEqual(b["label"], "iKant locale"); self.assertNotEqual(a["runtime_epoch"]["epoch_id"], b["runtime_epoch"]["epoch_id"]); self.assertFalse(b["runtime_epoch"]["model_is_identity"])

    def test_managed_turn_gate_and_browser_ui_sources_are_epoch_bound(self):
        root = Path(__file__).resolve().parents[1]
        managed = (root / "ikant" / "managed_runtime.py").read_text(encoding="utf-8")
        cognitive = (root / "ikant" / "cognitive.py").read_text(encoding="utf-8")
        web = (root / "ikant" / "web" / "enduser.js").read_text(encoding="utf-8")
        self.assertIn("materialize_runtime_epoch(self.root,require_managed_binding=True)", managed)
        self.assertIn("self._bind_runtime_epoch();return super().turn(user_text)", managed)
        self.assertIn('cycle["runtime_epoch"]=runtime_epoch', cognitive)
        self.assertIn("runtime_epoch_id", cognitive)
        self.assertIn("model_is_identity", web)
        self.assertIn("ikant:surface-snapshot", web)


if __name__ == "__main__":
    unittest.main()
