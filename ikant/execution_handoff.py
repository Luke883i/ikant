from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXECUTION_HANDOFF_SCHEMA = "ikant-execution-handoff/v0.17-test"
EXECUTION_LEDGER_SCHEMA = "ikant-execution-ledger/v0.17-test"


def _digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _candidate_index(practical: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("node_id")): row
        for row in (practical.get("action_ledger") or {}).get("candidates", [])
        if str(row.get("node_id") or "")
    }


def _base_kind(plan_status: str, action_status: str) -> str:
    if plan_status == "PLAN_HOST_REVALIDATION_REQUIRED" and action_status == "HOST_EXECUTION_ELIGIBLE":
        return "HOST"
    if plan_status == "PLAN_HUMAN_EXECUTION_REQUIRED" and action_status == "HUMAN_EXECUTION_REQUIRED":
        return "HUMAN"
    if plan_status == "PLAN_HUMAN_EXECUTION_REQUIRED" and action_status == "HOST_EXECUTION_ELIGIBLE":
        return "HOST"
    return "NONE"


def _handoff_state(*, plan_status: str, action_status: str, depends_on: list[str]) -> str:
    if plan_status in {"PLAN_BLOCKED", "PLAN_REVIEW_REQUIRED"}:
        return "NOT_HANDOFFABLE"
    if depends_on:
        return "PREDECESSOR_RECONCILIATION_REQUIRED"
    if action_status == "HOST_EXECUTION_ELIGIBLE" and plan_status in {"PLAN_HOST_REVALIDATION_REQUIRED", "PLAN_HUMAN_EXECUTION_REQUIRED"}:
        return "HOST_REVALIDATION_REQUIRED"
    if action_status == "HUMAN_EXECUTION_REQUIRED" and plan_status == "PLAN_HUMAN_EXECUTION_REQUIRED":
        return "HUMAN_EXECUTION_REQUIRED"
    return "NOT_HANDOFFABLE"


def build_execution_ledger(runtime: Any, cycle: dict[str, Any], practical: dict[str, Any]) -> dict[str, Any]:
    """Prepare zero-authority step handoffs from v0.15 actions and v0.16 plans.

    This function never executes an action. Handoffs are exact control-plane bindings so an
    external host can revalidate the same step without treating the plan itself as authority.
    """
    evidence_before = {
        nid: float(getattr(node, "evidence", 0.0))
        for nid, node in getattr(runtime, "nodes", {}).items()
    }
    action_ledger = practical.get("action_ledger") or {}
    planning = practical.get("planning") or {}
    plan_ledger = planning.get("plan_ledger") or {}
    candidates = _candidate_index(practical)
    session_id = str(getattr(runtime, "runtime", {}).get("session_id") or "")
    cycle_id = str(cycle.get("cycle_id") or "")
    intent_sha256 = str((cycle.get("semantic_slice") or {}).get("intent_sha256") or "")
    action_sha = str(action_ledger.get("sha256") or "")
    plan_sha = str(plan_ledger.get("sha256") or "")

    handoffs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for plan in plan_ledger.get("plans", []) or []:
        plan_id = str(plan.get("plan_id") or "")
        plan_status = str(plan.get("status") or "PLAN_REVIEW_REQUIRED")
        for step in plan.get("steps", []) or []:
            if not bool(step.get("material", True)):
                continue
            node_id = str(step.get("action_node_id") or "")
            candidate = candidates.get(node_id)
            errors: list[str] = []
            if candidate is None:
                errors.append("action candidate missing")
                candidate = {}
            action_status = str((candidate.get("decision") or {}).get("status") or "UNKNOWN")
            step_status = str(step.get("action_status") or "UNKNOWN")
            if action_status != step_status:
                errors.append("plan/action status drift")
            fingerprint = str(candidate.get("fingerprint") or "")
            if not fingerprint:
                errors.append("action fingerprint missing")
            approval_sha = str(((candidate.get("decision") or {}).get("approval") or {}).get("receipt_sha256") or "")
            if action_status in {"HOST_EXECUTION_ELIGIBLE", "HUMAN_EXECUTION_REQUIRED"} and not approval_sha:
                errors.append("approval receipt binding missing")
            depends_on = sorted({str(x) for x in step.get("depends_on", []) or [] if str(x)})
            binding = {
                "schema": EXECUTION_HANDOFF_SCHEMA,
                "session_id": session_id,
                "cycle_id": cycle_id,
                "intent_sha256": intent_sha256,
                "action_ledger_sha256": action_sha,
                "plan_ledger_sha256": plan_sha,
                "plan_id": plan_id,
                "decision_problem_id": str(plan.get("decision_problem_id") or plan_id),
                "step_id": str(step.get("step_id") or ""),
                "action_node_id": node_id,
                "action_fingerprint": fingerprint,
                "approval_receipt_sha256": approval_sha,
                "plan_status": plan_status,
                "action_status": action_status,
                "required_capabilities": sorted(set(candidate.get("required_capabilities", []) or [])),
                "depends_on": depends_on,
                "declared_preconditions": list(step.get("preconditions", []) or []),
                "declared_postconditions": list(step.get("postconditions", []) or []),
            }
            idempotency_key = _digest(binding)
            handoff_id = "xh-" + idempotency_key[:24]
            if handoff_id in seen_ids:
                errors.append("handoff collision")
            seen_ids.add(handoff_id)
            base_kind = _base_kind(plan_status, action_status)
            state = _handoff_state(plan_status=plan_status, action_status=action_status, depends_on=depends_on)
            if errors:
                state = "NOT_HANDOFFABLE"
                base_kind = "NONE"
            envelope = {
                **binding,
                "handoff_id": handoff_id,
                "idempotency_key": idempotency_key,
                "handoff_kind": base_kind,
                "handoff_state": state,
                "binding_errors": errors,
                "requires_fresh_host_revalidation": base_kind == "HOST",
                "requires_human_execution": base_kind == "HUMAN",
                "predecessor_reconciliation_required": bool(depends_on),
                "same_cycle_only": True,
                "execution_eligible": False,
                "execution_performed": False,
                "epistemic_authority": 0.0,
                "execution_authority": 0.0,
            }
            handoffs.append(envelope)

    evidence_after = {
        nid: float(getattr(node, "evidence", 0.0))
        for nid, node in getattr(runtime, "nodes", {}).items()
    }
    if evidence_before != evidence_after:
        raise RuntimeError("execution handoff modified evidence")

    ledger = {
        "schema": EXECUTION_LEDGER_SCHEMA,
        "session_id": session_id,
        "cycle_id": cycle_id,
        "intent_sha256": intent_sha256,
        "action_ledger_sha256": action_sha,
        "plan_ledger_sha256": plan_sha,
        "handoff_count": len(handoffs),
        "handoffs": handoffs,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
        "execution_performed": False,
        "boundaries": {
            "handoff_does_not_upgrade_action_or_plan": True,
            "handoff_is_not_execution": True,
            "same_turn_approval_is_not_reusable_authority": True,
            "dependent_steps_require_predecessor_reconciliation": True,
            "host_revalidates_system_safety_law_and_tool_capability": True,
            "receipt_digest_is_integrity_not_actor_authentication": True,
            "host_transport_authentication_is_external": True,
        },
    }
    raw = json.dumps(ledger, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ledger["sha256"] = hashlib.sha256(raw).hexdigest()
    if getattr(runtime, "durable", False):
        from .store import atomic_json_write
        path = Path(runtime.state_dir) / "execution-ledger.json"
        atomic_json_write(path, ledger)
        ledger["path"] = str(path)
    return ledger
