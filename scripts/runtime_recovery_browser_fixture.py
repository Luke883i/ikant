from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ikant.admission import digest, issue_receipt, probe, save_probe, save_receipt
from ikant.advanced_web_shell import AdvancedWebShellService
from ikant.chat_session import ChatLog
from ikant.cognitive import record_surface_a
from ikant.reactive_http import build_server
from ikant.runtime import Runtime
from ikant.session_egress import activate_runtime_egress, existing_runtime_egress
from tests.helpers import materialized_fixture_root


class FixtureModel:
    model = "fixture-model"
    managed_runtime = True
    runtime_binding_digest = "a" * 64
    def health(self): return True
    def status(self): return {"model": self.model, "managed_runtime": True}


class FixtureVoice:
    def status(self): return {"configured": False}
    def transcribe(self, audio, content_type): raise RuntimeError("voice disabled in recovery fixture")


def active_root(base: Path) -> Path:
    root = materialized_fixture_root(base)
    contract = (root / "IKANT_ACCESS_CONTRACT.md").read_text(encoding="utf-8")
    state = root / ".ikant"
    save_receipt(state, issue_receipt(contract, "I ACCEPT", presented_terms_sha256=digest(contract)))
    p = probe(root, state, contract)
    if p.get("overall") != "READY":
        raise RuntimeError(f"fixture admission probe blocked: {p.get('checks')}")
    save_probe(state, p)
    rt = Runtime.initialize(state, contract, durable=True)
    try:
        activate_runtime_egress(rt, initialization=True)
    finally:
        rt.close()
    return root


def prepare(root: Path, scenario: str) -> dict:
    rt = Runtime(root / ".ikant")
    try:
        guard = existing_runtime_egress(rt)
        if scenario == "sealed":
            text = "sealed canonical frame survives process replacement"
            receipt = guard.seal_frame(text, kind="TURN", cycle_id="cycle-browser-sealed")
            return {"expected_frame_sha256": receipt.frame_sha256, "expected_primary": None}
        if scenario == "interrupted":
            cog = rt.runtime.setdefault("cognitive", {})
            cog["pending_surface_a_cycle_id"] = "cycle-browser-interrupted"
            cog["pending_interaction_contract"] = {"schema": "browser-fixture"}
            rt._write_runtime()
            return {"expected_frame_sha256": None, "expected_primary": "Nessuna risposta è stata rigenerata"}
        if scenario == "surface":
            cycle = "cycle-browser-surface"
            text = "Risposta validata recuperata senza una seconda generazione del modello."
            log = ChatLog(rt.state_dir / "chat" / "transcript.jsonl", runtime_session_id=rt.runtime["session_id"])
            log.append("user", "domanda browser recovery", cycle_id=cycle, intention_node_id="intent-browser")
            receipt = record_surface_a(rt, cycle, text)
            return {"expected_frame_sha256": None, "expected_primary": "iKant: " + text, "response_id": receipt["response_id"]}
        raise ValueError(scenario)
    finally:
        rt.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=("sealed", "interrupted", "surface"), required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix=f"ikant-s17bis-browser-{args.scenario}-") as raw:
        root = active_root(Path(raw))
        expected = prepare(root, args.scenario)
        service = AdvancedWebShellService(root, model=FixtureModel(), voice=FixtureVoice())
        server, pairing = build_server(service, host="127.0.0.1", port=0, assets_dir=ROOT / "ikant" / "web")
        print(json.dumps({"schema":"ikant-runtime-recovery-browser-fixture/v1-test","scenario":args.scenario,"port":int(server.server_address[1]),"pairing_code":pairing.code,**expected}, ensure_ascii=False, sort_keys=True), flush=True)
        try:
            server.serve_forever(poll_interval=0.05)
        finally:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
