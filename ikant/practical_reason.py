from __future__ import annotations
from typing import Any

from .action_governance import ACTION_GOVERNANCE_SCHEMA, build_action_ledger

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
    core = {
        "schema": PRACTICAL_REASON_SCHEMA,
        "action_governance_schema": ACTION_GOVERNANCE_SCHEMA,
        "action_ledger": ledger,
        "temporal_replay_sha256": (temporal_core.get("replay") or {}).get("sha256"),
        "material_action": ledger.get("material_action", "NONE"),
        "boundaries": {
            "belief_quality_is_not_permission": True,
            "current_commitment_is_not_approval": True,
            "approval_is_not_capability": True,
            "eligibility_is_not_execution": True,
            "runtime_execution_performed": False,
        },
    }
    state = getattr(runtime, "runtime", {}).setdefault("practical_reason", {})
    state["last"] = {
        "schema": PRACTICAL_REASON_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "action_ledger_sha256": ledger.get("sha256"),
        "candidate_count": ledger.get("candidate_count", 0),
        "host_execution_eligible_count": ledger.get("host_execution_eligible_count", 0),
        "material_action": ledger.get("material_action", "NONE"),
        "epistemic_authority": 0.0,
    }
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    return core
