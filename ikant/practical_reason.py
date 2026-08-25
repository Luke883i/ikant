from __future__ import annotations
from typing import Any

from .action_governance import ACTION_GOVERNANCE_SCHEMA, build_action_ledger
from .intent_reconciliation import reconcile_intent
from .planning import finalize_planning
from .execution_protocol import finalize_execution_protocol

PRACTICAL_REASON_SCHEMA = "ikant-practical-reason/v0.15-test"


def finalize_practical_reason(
    runtime: Any,
    cycle: dict[str, Any],
    *,
    temporal_core: dict[str, Any],
    central: dict[str, Any],
    mined: list[dict[str, Any]],
    atoms: list[dict[str, Any]] | None,
    intention_node_id: str,
) -> dict[str, Any]:
    ledger = build_action_ledger(
        runtime,
        cycle,
        central=central,
        mined=mined,
        atoms=atoms,
        intention_node_id=intention_node_id,
    )
    reconciliation, planner_input = reconcile_intent(
        runtime,
        cycle,
        ledger,
        temporal_core=temporal_core,
        intention_node_id=intention_node_id,
    )
    effective_material_action = ledger.get("material_action", "NONE")
    if reconciliation.get("status") == "BLOCK":
        effective_material_action = "BLOCK"
    elif reconciliation.get("status") == "DEMOTE":
        effective_material_action = "PROPOSE_ONLY" if ledger.get("candidate_count", 0) else "NONE"
    core = {
        "schema": PRACTICAL_REASON_SCHEMA,
        "action_governance_schema": ACTION_GOVERNANCE_SCHEMA,
        "action_ledger": ledger,
        "intent_reconciliation": reconciliation,
        "temporal_replay_sha256": (temporal_core.get("replay") or {}).get("sha256"),
        "material_action": effective_material_action,
        "boundaries": {
            "belief_quality_is_not_permission": True,
            "current_commitment_is_not_approval": True,
            "approval_is_not_capability": True,
            "eligibility_is_not_execution": True,
            "reactive_structure_is_not_planner": True,
            "intent_reconciliation_can_only_preserve_or_downgrade": True,
            "runtime_execution_performed": False,
        },
    }
    planning = finalize_planning(
        runtime,
        cycle,
        core,
        central=central,
        planner_action_ledger=planner_input,
        intent_reconciliation=reconciliation,
    )
    core["planning"] = planning
    core["planning_status"] = planning.get("overall_status", "NONE")
    execution = finalize_execution_protocol(runtime, cycle, core)
    core["execution_protocol"] = execution
    core["execution_handoff_count"] = (execution.get("execution_ledger") or {}).get("handoff_count", 0)
    state = getattr(runtime, "runtime", {}).setdefault("practical_reason", {})
    state["last"] = {
        "schema": PRACTICAL_REASON_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "action_ledger_sha256": ledger.get("sha256"),
        "intent_reconciliation_sha256": reconciliation.get("sha256"),
        "intent_reconciliation_status": reconciliation.get("status"),
        "candidate_count": ledger.get("candidate_count", 0),
        "host_execution_eligible_count": ledger.get("host_execution_eligible_count", 0),
        "material_action": effective_material_action,
        "planning_status": planning.get("overall_status", "NONE"),
        "plan_ledger_sha256": (planning.get("plan_ledger") or {}).get("sha256"),
        "execution_ledger_sha256": (execution.get("execution_ledger") or {}).get("sha256"),
        "execution_handoff_count": (execution.get("execution_ledger") or {}).get("handoff_count", 0),
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    return core
