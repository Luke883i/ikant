from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

CAUSAL_CRC_SCHEMA = "ikant-crc-causal-diagnostics/v0.13-test"


def _metric(crc: dict[str, Any], key: str) -> float:
    try: return float((crc.get("diagnostics") or {}).get(key, 0.0))
    except (TypeError, ValueError): return 0.0


def _distance(base: dict[str, Any], alt: dict[str, Any]) -> float:
    flips = float(bool((base.get("roa_alignment") or {}).get("crc_basic")) != bool((alt.get("roa_alignment") or {}).get("crc_basic")))
    collapse = abs(_metric(base, "mean_coefficient_of_collapse") - _metric(alt, "mean_coefficient_of_collapse"))
    debt = min(1.0, abs(_metric(base, "epistemic_debt_open_count") - _metric(alt, "epistemic_debt_open_count")) / 4.0)
    coherence = abs(_metric(base, "functional_coherence") - _metric(alt, "functional_coherence"))
    return min(1.0, 0.45 * flips + 0.20 * collapse + 0.20 * debt + 0.15 * coherence)


def diagnose_crc_causality(
    semantic_slice: dict[str, Any],
    baseline_crc: dict[str, Any],
    *,
    horizon: Any = None,
    previous_neurofunctional_state: dict[str, Any] | None = None,
    evaluator: Callable[..., dict[str, Any]] | None = None,
    max_node_ablations: int = 4,
    max_source_ablations: int = 3,
) -> dict[str, Any]:
    """Measure intervention sensitivity of the runtime representation.

    This is an executable ablation diagnostic. It does not establish ontological causality,
    consciousness, or causal sufficiency in the represented world.
    """
    if evaluator is None:
        from .crc import evaluate_reticulum as evaluator
    rows = [dict(x) for x in semantic_slice.get("nodes", []) if isinstance(x, dict)]
    candidates = [x for x in rows if x.get("kind") not in {"principle", "intention", "response"}]
    candidates.sort(key=lambda x: (-float(x.get("epistemic_score", 0.0)), str(x.get("id", ""))))
    node_runs = []
    for row in candidates[:max(0, max_node_ablations)]:
        ablated = {**semantic_slice, "nodes": [x for x in rows if x.get("id") != row.get("id")]}
        alt = evaluator(ablated, horizon=horizon, previous_neurofunctional_state=previous_neurofunctional_state)
        node_runs.append({"node_id": row.get("id"), "source_mode": row.get("source_mode"), "dependency": round(_distance(baseline_crc, alt), 6), "crc_basic_flip": bool((baseline_crc.get("roa_alignment") or {}).get("crc_basic")) != bool((alt.get("roa_alignment") or {}).get("crc_basic"))})
    source_runs = []
    modes = []
    for row in candidates:
        mode = str(row.get("source_mode"))
        if mode not in modes: modes.append(mode)
    for mode in modes[:max(0, max_source_ablations)]:
        ablated = {**semantic_slice, "nodes": [x for x in rows if str(x.get("source_mode")) != mode]}
        alt = evaluator(ablated, horizon=horizon, previous_neurofunctional_state=previous_neurofunctional_state)
        source_runs.append({"source_mode": mode, "dependency": round(_distance(baseline_crc, alt), 6), "crc_basic_flip": bool((baseline_crc.get("roa_alignment") or {}).get("crc_basic")) != bool((alt.get("roa_alignment") or {}).get("crc_basic"))})
    deps = [x["dependency"] for x in node_runs + source_runs]
    digest = hashlib.sha256(json.dumps({"nodes": node_runs, "sources": source_runs}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": CAUSAL_CRC_SCHEMA,
        "structural_path_complete": bool((baseline_crc.get("roa_alignment") or {}).get("representational_path_complete")),
        "intervention_count": len(node_runs) + len(source_runs),
        "node_ablations": node_runs,
        "source_ablations": source_runs,
        "mean_counterfactual_dependency": round(sum(deps) / len(deps), 6) if deps else 0.0,
        "max_counterfactual_dependency": round(max(deps), 6) if deps else 0.0,
        "single_point_dependency": any(x["crc_basic_flip"] for x in node_runs),
        "source_class_dependency": any(x["crc_basic_flip"] for x in source_runs),
        "ablation_sha256": digest,
        "claim_boundary": "Executable runtime intervention diagnostic; not proof of ontological closure, consciousness, or real-world causality.",
        "epistemic_authority": 0.0,
    }
