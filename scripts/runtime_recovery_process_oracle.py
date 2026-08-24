from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ikant.chat_session import ChatLog
from ikant.cognitive import record_surface_a
from ikant.runtime import Runtime
from ikant.runtime_recovery import materialize_recovery_frame, reconcile_surface_a_chat, verified_recovery
from ikant.session_egress import activate_runtime_egress
from tests.helpers import materialized_fixture_root
from ikant.admission import digest, issue_receipt, probe, save_probe, save_receipt


def active_root(base: Path) -> Path:
    root = materialized_fixture_root(base)
    contract = (root / "IKANT_ACCESS_CONTRACT.md").read_text(encoding="utf-8")
    state = root / ".ikant"
    save_receipt(state, issue_receipt(contract, "I ACCEPT", presented_terms_sha256=digest(contract)))
    p = probe(root, state, contract)
    if p.get("overall") != "READY":
        raise RuntimeError("fixture probe blocked")
    save_probe(state, p)
    rt = Runtime.initialize(state, contract, durable=True)
    try:
        activate_runtime_egress(rt, initialization=True)
    finally:
        rt.close()
    return root


def child(root: Path, mode: str) -> dict:
    rt = Runtime(root / ".ikant")
    try:
        if mode == "classify":
            return {"pid": os.getpid(), "recovery": verified_recovery(rt)}
        if mode == "materialize":
            frame = materialize_recovery_frame(rt)
            return {"pid": os.getpid(), "frame": frame, "recovery": verified_recovery(rt)}
        if mode == "surface-reconcile":
            before = verified_recovery(rt)
            after = reconcile_surface_a_chat(rt, before)
            return {"pid": os.getpid(), "before": before, "after": after}
        raise ValueError(mode)
    finally:
        rt.close()


def run_child(root: Path, mode: str) -> dict:
    proc = subprocess.run([sys.executable, __file__, "--child", str(root), "--mode", mode], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--child")
    ap.add_argument("--mode")
    args = ap.parse_args()
    if args.child:
        print(json.dumps(child(Path(args.child), args.mode), ensure_ascii=False, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory(prefix="ikant-s17bis-process-") as raw:
        root = active_root(Path(raw))
        rt = Runtime(root / ".ikant")
        try:
            rt.runtime.setdefault("cognitive", {})["pending_surface_a_cycle_id"] = "cycle-process-interrupted"
            rt.runtime["cognitive"]["pending_interaction_contract"] = {"schema": "process-fixture"}
            rt._write_runtime()
        finally:
            rt.close()
        first = run_child(root, "materialize")
        second = run_child(root, "classify")
        if first["pid"] == second["pid"] or first["pid"] == os.getpid() or second["pid"] == os.getpid():
            raise AssertionError("process boundary not crossed")
        if first["frame"]["receipt"]["frame_sha256"] != second["recovery"]["frame_sha256"]:
            raise AssertionError("sealed recovery frame changed across process restart")
        if second["recovery"]["state"] != "SEALED_FRAME_PENDING":
            raise AssertionError(second)

    with tempfile.TemporaryDirectory(prefix="ikant-s17bis-surface-") as raw:
        root = active_root(Path(raw))
        rt = Runtime(root / ".ikant")
        try:
            cycle = "cycle-process-surface"
            log = ChatLog(rt.state_dir / "chat" / "transcript.jsonl", runtime_session_id=rt.runtime["session_id"])
            log.append("user", "domanda process restart", cycle_id=cycle, intention_node_id="intent-process")
            receipt = record_surface_a(rt, cycle, "Risposta validata conservata attraverso il riavvio del processo.")
            response_id = receipt["response_id"]
        finally:
            rt.close()
        reconciled = run_child(root, "surface-reconcile")
        verified = run_child(root, "classify")
        if reconciled["before"]["state"] != "SURFACE_A_UNSEALED" or reconciled["after"].get("response_id") != response_id:
            raise AssertionError(reconciled)
        rt = Runtime(root / ".ikant")
        try:
            rows = ChatLog(rt.state_dir / "chat" / "transcript.jsonl", runtime_session_id=rt.runtime["session_id"]).rows()
            replies = [r for r in rows if r.get("role") == "ikant" and r.get("response_id") == response_id]
            if len(replies) != 1:
                raise AssertionError("surface recovery duplicated chat response")
        finally:
            rt.close()
        if verified["recovery"]["state"] != "SURFACE_A_UNSEALED":
            raise AssertionError(verified)

    print(json.dumps({"schema":"ikant-runtime-recovery-process-oracle/v1-test","status":"PASS","real_process_restart":True,"distinct_processes":True,"sealed_frame_byte_identity_preserved":True,"surface_a_reconciled_without_duplicate_response":True,"model_reexecuted":False,"planner_reexecuted":False,"material_driver_reexecuted":False,"epistemic_authority":0.0,"execution_authority":0.0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
