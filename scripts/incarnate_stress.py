from __future__ import annotations

import argparse
import json
import random
import tempfile
import sys
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from ikant.incarnate import bind_dashboard, validate_incarnate_dashboard


@dataclass
class FakeRuntime:
    root: Path
    def __post_init__(self):
        self.state_dir = self.root / ".ikant"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runtime = {"session_id": "SES-stress", "status": "ACTIVE", "cognitive": {}}


def write_pair(rt: FakeRuntime, cycle: str, *, snapshot_cycle=None, snapshot_session=None, json_ok=True, docx_ok=True):
    c = rt.runtime["cognitive"]
    jp = rt.state_dir / "cognitive" / "surface.json"
    dp = rt.state_dir / "artifacts" / "surface.docx"
    jp.parent.mkdir(parents=True, exist_ok=True); dp.parent.mkdir(parents=True, exist_ok=True)
    if json_ok:
        jp.write_text(json.dumps({"cycle_id": snapshot_cycle or cycle, "session_id": snapshot_session or rt.runtime["session_id"]}), encoding="utf-8")
    elif jp.exists():
        jp.unlink()
    if docx_ok:
        dp.write_bytes(("PK-STRESS-" + cycle).encode())
    elif dp.exists():
        dp.unlink()
    c["last_snapshot"] = str(jp)
    c["last_surface_b_docx"] = str(dp)


def case_oracle(kind: str):
    blocked = {
        "missing_docx", "missing_json", "cycle_mismatch", "session_mismatch",
        "pending_mismatch", "validated_while_pending", "empty_validated",
    }
    if kind in blocked: return "BLOCKED"
    if kind == "pending": return "PENDING"
    if kind == "idle": return "IDLE"
    return "READY"


def run_case(rt: FakeRuntime, rng: random.Random, index: int, kind: str):
    cycle = f"CYC-{index:08d}"
    cog = rt.runtime["cognitive"]
    cog.clear()
    dashboard = {"overall": "STABLE", "contract": {}, "surface_b": {}}
    validated = kind not in {"pending", "idle"}
    text = "Risposta Surface A validata e incorporata nel dashboard." if validated else None
    call_cycle = cycle

    if kind != "idle":
        write_pair(rt, cycle)
    if kind == "pending":
        cog["pending_surface_a_cycle_id"] = cycle
        validated = False
    elif kind == "missing_docx":
        write_pair(rt, cycle, docx_ok=False)
    elif kind == "missing_json":
        write_pair(rt, cycle, json_ok=False)
    elif kind == "cycle_mismatch":
        write_pair(rt, cycle, snapshot_cycle=cycle + "-STALE")
    elif kind == "session_mismatch":
        write_pair(rt, cycle, snapshot_session="SES-other")
    elif kind == "pending_mismatch":
        cog["pending_surface_a_cycle_id"] = cycle + "-OTHER"
        validated = False
        text = None
    elif kind == "validated_while_pending":
        cog["pending_surface_a_cycle_id"] = cycle
    elif kind == "empty_validated":
        text = "   "
    elif kind == "unicode_validated":
        text = "Risposta valida: cautela, continuità, 日本語, العربية, emoji 🧭 senza uscire dal dashboard."
    elif kind == "custom_artifact_bytes":
        Path(cog["last_surface_b_docx"]).write_bytes(rng.randbytes(96))

    bind_dashboard(rt, dashboard, surface_a_text=text, cycle_id=call_cycle if kind != "idle" else None, surface_a_validated=validated)
    expected = case_oracle(kind)
    actual = dashboard["incarnate"]["state"]
    valid, validation_errors = validate_incarnate_dashboard(dashboard)
    mismatch = None
    if actual != expected:
        mismatch = f"state:{kind}:{expected}->{actual}"
    elif expected != "BLOCKED" and not valid:
        mismatch = f"validation:{kind}:{','.join(validation_errors)}"
    elif expected == "BLOCKED" and not dashboard["incarnate"]["errors"]:
        mismatch = f"blocked_without_reason:{kind}"
    signature = (kind, actual, tuple(dashboard["incarnate"]["errors"]))
    return mismatch, signature


def run(seed: int, cases: int, tail: int):
    kinds = [
        "validated", "pending", "idle", "missing_docx", "missing_json", "cycle_mismatch",
        "session_mismatch", "pending_mismatch", "validated_while_pending", "empty_validated",
        "unicode_validated", "custom_artifact_bytes",
    ]
    failures = []
    signatures = set()
    kinds_seen = set()
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime(Path(td))
        rng = random.Random(seed)
        for i in range(cases):
            kind = kinds[i % len(kinds)] if i < len(kinds) else rng.choice(kinds)
            mismatch, signature = run_case(rt, rng, i, kind)
            kinds_seen.add(kind); signatures.add(signature)
            if mismatch: failures.append(mismatch)
        baseline = set(signatures)
        tail_rng = random.Random(seed + 1_000_003)
        tail_new = set()
        for j in range(tail):
            kind = tail_rng.choice(kinds)
            mismatch, signature = run_case(rt, tail_rng, cases + j, kind)
            if mismatch: failures.append(mismatch)
            if signature not in baseline: tail_new.add(signature)
    result = {
        "schema": "ikant-incarnate-stress/v0.7-test",
        "seed": seed,
        "cases": cases,
        "tail_cases": tail,
        "scenario_kinds": len(kinds),
        "scenario_kinds_seen": len(kinds_seen),
        "baseline_signatures": len(baseline),
        "tail_new_signatures": len(tail_new),
        "failure_count": len(failures),
        "sample_failures": failures[:20],
        "saturated": len(kinds_seen) == len(kinds) and len(tail_new) == 0 and not failures,
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=883)
    p.add_argument("--cases", type=int, default=10_000)
    p.add_argument("--tail", type=int, default=1_000)
    a = p.parse_args()
    result = run(a.seed, a.cases, a.tail)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["saturated"] else 2)

if __name__ == "__main__":
    main()
