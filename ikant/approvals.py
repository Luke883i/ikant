from __future__ import annotations

import hashlib
import json
from typing import Any

APPROVAL_SCHEMA = "ikant-action-approval/v0.15-test"


def _digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def action_fingerprint(candidate: dict[str, Any]) -> str:
    payload = {
        "node_id": candidate.get("node_id"),
        "text": candidate.get("text"),
        "source_mode": candidate.get("source_mode"),
        "maxim": candidate.get("maxim"),
        "required_capabilities": sorted(candidate.get("required_capabilities", [])),
        "governing_commitment_ids": sorted(candidate.get("governing_commitment_ids", [])),
        "affected_parties": sorted(candidate.get("affected_parties", [])),
        "reversibility": candidate.get("reversibility"),
        "rollback_plan": candidate.get("rollback_plan"),
        "expected_effects": list(candidate.get("expected_effects", [])),
        "failure_modes": list(candidate.get("failure_modes", [])),
        "impact_level": candidate.get("impact_level"),
        "human_impact_assessed": bool(candidate.get("human_impact_assessed")),
        "material": bool(candidate.get("material")),
    }
    return _digest(payload)


def issue_same_turn_approval(
    runtime: Any,
    candidate: dict[str, Any],
    *,
    atom: dict[str, Any] | None,
    intent_sha256: str,
    intention_node_id: str,
) -> dict[str, Any] | None:
    """Create a current-turn approval receipt only from an explicitly user-attributed action atom.

    The receipt is action-fingerprint/session/intent-bound. It is not reusable on later turns and does
    not itself grant capabilities or execute anything.
    """
    if not isinstance(atom, dict):
        return None
    meta = dict(atom.get("metadata") or {})
    if str(atom.get("source_mode") or "") != "user":
        return None
    kind = str(atom.get("kind") or "")
    if kind == "action" and str(candidate.get("source_mode") or "") != "user":
        return None
    if kind == "constraint" and str(meta.get("approves_action_node_id") or "") != str(candidate.get("node_id") or ""):
        return None
    if meta.get("explicit_action_approval") is not True:
        return None
    if str(meta.get("approval_scope") or "") != "this_action":
        return None
    fingerprint = action_fingerprint(candidate)
    receipt = {
        "schema": APPROVAL_SCHEMA,
        "session_id": str(getattr(runtime, "runtime", {}).get("session_id") or ""),
        "intention_node_id": str(intention_node_id),
        "intent_sha256": str(intent_sha256),
        "action_node_id": str(candidate.get("node_id")),
        "action_fingerprint": fingerprint,
        "scope": "this_action",
        "actor_source": "user",
        "same_turn_required": True,
        "grants_capabilities": False,
        "executes_action": False,
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def validate_approval(
    receipt: dict[str, Any] | None,
    candidate: dict[str, Any],
    *,
    session_id: str,
    intent_sha256: str,
    intention_node_id: str,
) -> tuple[bool, list[str]]:
    if not receipt:
        return False, ["approval missing"]
    errors: list[str] = []
    if receipt.get("schema") != APPROVAL_SCHEMA:
        errors.append("approval schema")
    copy = dict(receipt); actual = copy.pop("receipt_sha256", None)
    if actual != _digest(copy):
        errors.append("approval digest")
    if receipt.get("session_id") != session_id:
        errors.append("approval session")
    if receipt.get("intent_sha256") != intent_sha256:
        errors.append("approval intent")
    if receipt.get("intention_node_id") != intention_node_id:
        errors.append("approval intention node")
    if receipt.get("action_node_id") != candidate.get("node_id"):
        errors.append("approval action")
    if receipt.get("action_fingerprint") != action_fingerprint(candidate):
        errors.append("approval action fingerprint")
    if receipt.get("scope") != "this_action" or receipt.get("actor_source") != "user":
        errors.append("approval scope/actor")
    if receipt.get("grants_capabilities") is not False or receipt.get("executes_action") is not False:
        errors.append("approval authority escalation")
    return not errors, errors
