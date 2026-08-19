from __future__ import annotations

from typing import Any

from .plan_graph import inverse_predicate, normalize_predicate

OUTCOME_RECONCILIATION_SCHEMA = "ikant-outcome-reconciliation/v0.17-test"


def reconcile_execution_outcome(envelope: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    declared = [normalize_predicate(x) for x in envelope.get("declared_postconditions", []) or []]
    observed = [normalize_predicate(x) for x in receipt.get("observed_predicates", []) or []]
    observed_set = set(observed)
    outcome = str(receipt.get("outcome") or "UNKNOWN")
    conflicts = sorted(p for p in declared if inverse_predicate(p) in observed_set)
    confirmed = sorted(p for p in declared if p in observed_set)
    missing = sorted(set(declared) - observed_set)

    if outcome == "DECLINED":
        status = "EXECUTION_DECLINED"
    elif outcome == "FAILED":
        status = "EXECUTION_FAILED"
    elif outcome != "EXECUTED":
        status = "OUTCOME_UNKNOWN"
    elif conflicts:
        status = "POSTCONDITION_CONFLICT"
    elif declared and len(confirmed) == len(declared):
        status = "POSTCONDITIONS_REPORTED"
    elif confirmed:
        status = "POSTCONDITIONS_PARTIAL"
    else:
        status = "OBSERVATION_REQUIRED"

    return {
        "schema": OUTCOME_RECONCILIATION_SCHEMA,
        "handoff_id": envelope.get("handoff_id"),
        "outcome": outcome,
        "status": status,
        "declared_postconditions": declared,
        "host_reported_predicates": observed,
        "reported_matches": confirmed,
        "reported_conflicts": conflicts,
        "unreported_postconditions": missing,
        "execution_ref": receipt.get("execution_ref"),
        "execution_ref_is_not_proof_of_effect": True,
        "host_report_is_not_independent_evidence": True,
        "observed_world_verified": False,
        "next_step_auto_advance": False,
        "next_step_requires_fresh_revalidation": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
