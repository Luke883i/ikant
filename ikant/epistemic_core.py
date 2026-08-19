from __future__ import annotations

from typing import Any

from .calibration import apply_calibration_to_cycle, derive_calibration
from .causal_crc import diagnose_crc_causality
from .hybrid_retrieval import apply_hybrid_retrieval
from .provenance import materialize_provenance

EPISTEMIC_CORE_SCHEMA = "ikant-epistemic-core/v0.13-test"


def prepare_epistemic_core(runtime: Any, intent: str, *, limit: int = 12) -> dict[str, Any]:
    provenance = materialize_provenance(runtime)
    retrieval = apply_hybrid_retrieval(runtime, intent, limit=limit)
    return {"provenance": provenance["summary"], "hybrid_retrieval": retrieval}


def calibrate_cycle(runtime: Any, cycle: dict[str, Any]) -> dict[str, Any]:
    calibration = derive_calibration(runtime, cycle)
    apply_calibration_to_cycle(cycle, calibration)
    return calibration


def finalize_epistemic_core(
    runtime: Any,
    cycle: dict[str, Any],
    crc: dict[str, Any],
    *,
    horizon: Any = None,
    previous_neurofunctional_state: dict[str, Any] | None = None,
    prepared: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prepared = prepared or {}
    provenance = materialize_provenance(runtime)["summary"]
    calibration = calibration or derive_calibration(runtime, cycle)
    causal = diagnose_crc_causality(cycle.get("semantic_slice", {}), crc, horizon=horizon, previous_neurofunctional_state=previous_neurofunctional_state)
    crc["causal_diagnostics"] = causal
    core = {
        "schema": EPISTEMIC_CORE_SCHEMA,
        "provenance": provenance,
        "calibration": calibration,
        "hybrid_retrieval": prepared.get("hybrid_retrieval") or runtime.runtime.get("epistemic_core", {}).get("last_hybrid_retrieval", {}),
        "causal_crc": causal,
        "boundaries": {
            "provenance_is_not_evidence": True,
            "calibration_is_caution_only": True,
            "retrieval_changes_availability_not_evidence": True,
            "causal_diagnostics_are_intervention_proxies_not_ontological_proof": True,
        },
    }
    state = runtime.runtime.setdefault("epistemic_core", {})
    state["last_cycle"] = {
        "schema": EPISTEMIC_CORE_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "provenance_sha256": provenance.get("sha256"),
        "calibration_risk": calibration.get("risk_adjustment"),
        "max_counterfactual_dependency": causal.get("max_counterfactual_dependency"),
        "single_point_dependency": causal.get("single_point_dependency"),
    }
    if hasattr(runtime, "_write_runtime"): runtime._write_runtime()
    return core
