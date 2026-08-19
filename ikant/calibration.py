from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
from typing import Any

CALIBRATION_SCHEMA = "ikant-calibrated-uncertainty/v0.13-test"
_OUTCOME = {"success": 1.0, "partial": 0.5, "failure": 0.0, "corrected": 0.0}


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, float(v)))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


@dataclass(frozen=True)
class CalibrationProfile:
    schema: str
    sample_count: int
    mean_confidence: float
    empirical_success: float
    brier_mean: float
    calibration_gap: float
    risk_adjustment: float
    cold_start: bool
    evidence_modified: bool = False
    authority: str = "CAUTION_ONLY"


def _events(runtime: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = getattr(runtime, "events_path", None)
    if path is not None and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
    rows.extend(getattr(runtime, "events_mem", []) or [])
    by_seq = {int(x.get("seq", i + 1)): x for i, x in enumerate(rows)}
    return [by_seq[k] for k in sorted(by_seq)]


def _cycle(runtime: Any, cycle_id: str) -> dict[str, Any] | None:
    if cycle_id in getattr(runtime, "cycles", {}):
        return runtime.cycles[cycle_id]
    path = getattr(runtime, "cycles_dir", None)
    if path is not None:
        p = Path(path) / f"{cycle_id}.json"
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): return None
    return None


def cycle_confidence(cycle: dict[str, Any]) -> float:
    sem = cycle.get("semantic_slice") or {}
    by = {x.get("id"): x for x in sem.get("nodes", []) if isinstance(x, dict)}
    projection = cycle.get("output_projection") or {}
    ids = list(projection.get("assertable_node_ids", []))
    rows = [by[x] for x in ids if x in by]
    if not rows:
        rows = [x for x in by.values() if x.get("kind") not in {"intention", "response", "principle"}]
    return _clamp(_mean([float(x.get("epistemic_score", 0.0)) for x in rows])) if rows else 0.0


def feedback_samples(runtime: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for event in _events(runtime):
        if event.get("op") != "FEEDBACK":
            continue
        outcome = str((event.get("payload") or {}).get("outcome", "unknown"))
        if outcome not in _OUTCOME:
            continue
        cid = str(event.get("subject") or "")
        cycle = _cycle(runtime, cid)
        if not cycle:
            continue
        out.append((cycle_confidence(cycle), _OUTCOME[outcome]))
    return out


def derive_calibration(runtime: Any, current_cycle: dict[str, Any] | None = None) -> dict[str, Any]:
    samples = feedback_samples(runtime)
    ps = [p for p, _ in samples]; ys = [y for _, y in samples]
    n = len(samples)
    brier = _mean([(p - y) ** 2 for p, y in samples]) if samples else 0.25
    mean_p = _mean(ps) if ps else 0.5
    mean_y = _mean(ys) if ys else 0.5
    gap = abs(mean_p - mean_y)
    exposure = 1.0 - math.exp(-n / 12.0)
    empirical_risk = _clamp(0.65 * brier + 0.35 * gap)
    cold_start = n < 4
    risk = _clamp((0.16 * (1.0 - exposure)) + empirical_risk * exposure)
    if current_cycle is not None:
        current = cycle_confidence(current_cycle)
        risk = _clamp(risk + (0.06 * abs(current - 0.5) * (1.0 - exposure)))
    profile = CalibrationProfile(CALIBRATION_SCHEMA, n, round(mean_p, 6), round(mean_y, 6), round(brier, 6), round(gap, 6), round(risk, 6), cold_start)
    record = asdict(profile)
    core = runtime.runtime.setdefault("epistemic_core", {}); core["calibration"] = record
    legacy = runtime.runtime.setdefault("calibration", {})
    legacy.update({"n": n, "brier_sum": round(brier * n, 6), "brier_mean": round(brier, 6)})
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    return record


def apply_calibration_to_cycle(cycle: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    policy = cycle.setdefault("output_policy", {})
    base_caution = _clamp(float(policy.get("epistemic_caution", 0.0)))
    base_threshold = _clamp(float(policy.get("claim_threshold", 0.42 + 0.38 * base_caution)))
    risk = _clamp(float(profile.get("risk_adjustment", 0.0)))
    adjusted_caution = max(base_caution, _clamp(base_caution + 0.35 * risk * (1.0 - base_caution)))
    adjusted_threshold = max(base_threshold, _clamp(0.42 + 0.38 * adjusted_caution))
    policy["epistemic_caution"] = round(adjusted_caution, 6)
    policy["claim_threshold"] = round(adjusted_threshold, 6)
    policy["calibration"] = {
        "schema": CALIBRATION_SCHEMA,
        "sample_count": int(profile.get("sample_count", 0)),
        "risk_adjustment": round(risk, 6),
        "base_caution": round(base_caution, 6),
        "adjusted_caution": round(adjusted_caution, 6),
        "base_claim_threshold": round(base_threshold, 6),
        "adjusted_claim_threshold": round(adjusted_threshold, 6),
        "monotone_caution_only": True,
        "evidence_modified": False,
    }
    return cycle
