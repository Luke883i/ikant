from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from ikant.component_manifest import load_manifest, manifest_digest, select_engine_artifact
from ikant.component_store import atomic_json, tree_digest
from ikant.model_manager import ModelManager

ROOT = Path(__file__).resolve().parents[1]
CPU_SHA256 = "01b90b0764821d0e53b985730eea3837e29a976ee00e783e18837937b93fc3f1"
OPENVINO_SHA256 = "e86a81b4a443200996efc33e627b321bd377bad19ea2d9489d43ad960ccc16ae"
MODEL_SHA256 = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"


class RuntimeBackendCompatibilityV29Tests(unittest.TestCase):
    def test_linux_x64_is_exact_b10344_cpu_asset(self):
        manifest = load_manifest(ROOT / "MODEL_RUNTIME.json")
        platform, artifact = select_engine_artifact(manifest, key="linux-x86_64")
        self.assertEqual(platform, "linux-x86_64")
        self.assertEqual(
            artifact["url"],
            "https://github.com/ggml-org/llama.cpp/releases/download/b10344/llama-b10344-bin-ubuntu-x64.tar.gz",
        )
        self.assertEqual(artifact["sha256"], CPU_SHA256)
        self.assertNotIn("openvino", artifact["url"].lower())
        self.assertGreaterEqual(int(artifact["max_size_bytes"]), 16_512_385)
        self.assertLessEqual(int(artifact["max_size_bytes"]), 30_000_000)

    def test_openvino_to_cpu_changes_manifest_identity(self):
        current = load_manifest(ROOT / "MODEL_RUNTIME.json")
        old = copy.deepcopy(current)
        old_artifact = old["engine"]["artifacts"]["linux-x86_64"]
        old_artifact.update(
            url="https://github.com/ggml-org/llama.cpp/releases/download/b10344/llama-b10344-bin-ubuntu-openvino-2026.2.1-x64.tar.gz",
            sha256=OPENVINO_SHA256,
            max_size_bytes=160_000_000,
        )
        self.assertNotEqual(manifest_digest(current), manifest_digest(old))

    def test_old_openvino_install_marker_cannot_be_reused(self):
        manifest = load_manifest(ROOT / "MODEL_RUNTIME.json")
        with tempfile.TemporaryDirectory() as td:
            manager = ModelManager(manifest, component_root=td, platform="linux-x86_64")
            install = Path(td) / "engines" / manager.engine_version / "linux-x86_64"
            install.mkdir(parents=True)
            server = install / "llama-server"
            server.write_bytes(b"fixture-server")
            server.chmod(0o700)
            marker = install / ".ikant-install.json"
            digest = tree_digest(install)
            atomic_json(marker, {"artifact_sha256": OPENVINO_SHA256, "tree_sha256": digest})
            self.assertIsNone(manager._valid_install(install, marker, manager.engine_artifact))
            atomic_json(marker, {"artifact_sha256": CPU_SHA256, "tree_sha256": digest})
            self.assertEqual(manager._valid_install(install, marker, manager.engine_artifact), server.resolve())

    def test_hosted_cpu_proof_binds_exact_engine_model_and_readiness(self):
        proof = json.loads((ROOT / "backlog" / "runtime_compat_proof_b10344_qwen35.json").read_text())
        self.assertEqual(proof["schema"], "ikant-runtime-compat-proof/v0.29-test")
        self.assertEqual(proof["engine_release"], "b10344")
        self.assertEqual(proof["engine_asset_sha256"], CPU_SHA256)
        self.assertEqual(proof["model_sha256"], MODEL_SHA256)
        self.assertEqual(proof["platform"], "linux-x86_64")
        self.assertEqual(proof["backend"], "cpu")
        self.assertTrue(proof["ready"])
        self.assertEqual(proof["status"], "PASS")
        self.assertIsNone(proof["returncode_before_cleanup"])
        self.assertEqual(proof["epistemic_authority"], 0.0)
        self.assertEqual(proof["execution_authority"], 0.0)

    def test_compatibility_falsification_is_converged(self):
        receipt = json.loads((ROOT / "backlog" / "runtime_backend_compat_falsification_v29.json").read_text())
        self.assertEqual(receipt["trajectories"], 10_000_000)
        self.assertEqual(receipt["mutation_trials"], 10_000_000)
        self.assertEqual(receipt["mutation_classes"], 48)
        self.assertEqual(receipt["baseline_failures"], 0)
        self.assertEqual(receipt["survivors"], [])
        self.assertEqual(receipt["partial_kill_classes"], [])
        self.assertGreaterEqual(receipt["min_kills_per_mutant"], 208_333)
        self.assertEqual(receipt["tail_novelty"], 0)
        self.assertTrue(receipt["candidate"]["readiness_still_required"])
        self.assertFalse(receipt["candidate"]["dynamic_fallback"])


if __name__ == "__main__":
    unittest.main()
