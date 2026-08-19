from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .approvals import action_fingerprint, issue_same_turn_approval, validate_approval
from .authority import normalize_capability, resolve_authority

ACTION_GOVERNANCE_SCHEMA = "ikant-action-governance/v0.15-test"
ACTION_LEDGER_SCHEMA = "ikant-action-ledger/v0.15-test"
REVERSIBILITY = {"REVERSIBLE", "PARTIAL", "IRREVERSIBLE", "UNKNOWN"}


@dataclass(frozen=True)
class ActionDecision:
    status: str
    execution_eligible: bool
    proposal_allowed: bool
    human_execution_required: bool
    reasons: tuple[str, ...]


def _kind(node: Any) -> str:
    raw = getattr(node, "kind", "")
    return str(getattr(raw, "value", raw))


def _meta(node: Any) -> dict[str, Any]:
    return dict(getattr(node, "metadata", {}) or {})


def _reversibility(meta: dict[str, Any]) -> str:
    value = str(meta.get("reversibility") or "UNKNOWN").upper()
    return value if value in REVERSIBILITY else "UNKNOWN"


def _approval_atom_map(mined: list[dict[str, Any]], atoms: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record, atom in zip(mined, atoms or []):
        meta = dict(atom.get("metadata") or {})
        if str(atom.get("source_mode") or "") != "user" or meta.get("explicit_action_approval") is not True:
            continue
        kind = str(record.get("kind") or atom.get("kind") or "")
        if kind == "action":
            out[str(record.get("id"))] = atom
        elif kind == "constraint" and meta.get("approves_action_node_id"):
            out[str(meta.get("approves_action_node_id"))] = atom
    return out


def _candidate(runtime: Any, row: dict[str, Any], atom: dict[str, Any] | None) -> dict[str, Any]:
    node = getattr(runtime, "nodes", {}).get(str(row.get("id")))
    if node is None:
        raise KeyError(row.get("id"))
    meta = _meta(node)
    required = sorted({normalize_capability(x) for x in meta.get("required_capabilities", []) or []})
    governing = [str(x) for x in meta.get("governing_commitment_ids", []) or []]
    affected = sorted({str(x).strip() for x in meta.get("affected_parties", []) or [] if str(x).strip()})
    mod = getattr(node, "modulators", None)
    social = float(getattr(mod, "social_relevance", 0.0) or 0.0)
    agency = float(getattr(mod, "agency_relevance", 0.0) or 0.0)
    impact_required = bool(affected or social >= 0.5 or agency >= 0.5)
    explicit_maxim = isinstance(meta.get("action_maxim"), str) and bool(meta.get("action_maxim").strip())
    maxim = str(meta.get("action_maxim") or f"Act by: {getattr(node, 'text', row.get('text', ''))}").strip()
    expected_effects = [str(x).strip() for x in meta.get("expected_effects", []) or [] if str(x).strip()]
    failure_modes = [str(x).strip() for x in meta.get("failure_modes", []) or [] if str(x).strip()]
    rollback = str(meta.get("rollback_plan") or "").strip()
    material = bool(meta.get("material_action", True))
    candidate = {
        "node_id": str(getattr(node, "id", row.get("id"))),
        "text": str(getattr(node, "text", row.get("text", ""))),
        "source_mode": str(getattr(node, "source_mode", row.get("source_mode", ""))),
        "epistemic_score": float(row.get("epistemic_score", 0.0)),
        "material": material,
        "maxim": maxim,
        "maxim_explicit": explicit_maxim,
        "required_capabilities": required,
        "governing_commitment_ids": governing,
        "affected_parties": affected,
        "impact_required": impact_required,
        "human_impact_assessed": meta.get("human_impact_assessed") is True,
        "impact_level": str(meta.get("impact_level") or ("UNKNOWN" if impact_required else "NONE")).upper(),
        "reversibility": _reversibility(meta),
        "rollback_plan": rollback,
        "expected_effects": expected_effects,
        "failure_modes": failure_modes,
        "counterfactual_complete": bool(expected_effects and failure_modes),
        "atom_explicit_approval": bool((atom or {}).get("metadata", {}).get("explicit_action_approval") is True),
    }
    candidate["fingerprint"] = action_fingerprint(candidate)
    return candidate


def decide_action(
    runtime: Any,
    candidate: dict[str, Any],
    *,
    central_mode: str,
    approval: dict[str, Any] | None,
    intent_sha256: str,
    intention_node_id: str,
) -> dict[str, Any]:
    authority = resolve_authority(
        runtime,
        governing_commitment_ids=candidate.get("governing_commitment_ids", []),
        required_capabilities=candidate.get("required_capabilities", []),
    )
    approval_ok, approval_errors = validate_approval(
        approval,
        candidate,
        session_id=str(getattr(runtime, "runtime", {}).get("session_id") or ""),
        intent_sha256=intent_sha256,
        intention_node_id=intention_node_id,
    )
    reasons: list[str] = []
    proposal_allowed = True
    human_execution_required = False
    execution_eligible = False

    if central_mode in {"HORIZON_BLOCK", "PRACTICAL_BLOCK"}:
        status = "CENTRAL_BLOCKED"; proposal_allowed = False; reasons.append("central practical/horizon block")
    elif not candidate.get("material", True):
        status = "PROPOSABLE"; reasons.append("non-material candidate")
    elif not candidate.get("maxim_explicit"):
        status = "MAXIM_REQUIRED"; reasons.append("explicit action maxim missing")
    elif candidate.get("impact_required") and not candidate.get("human_impact_assessed"):
        status = "IMPACT_REVIEW_REQUIRED"; reasons.append("human impact unresolved")
    elif str(candidate.get("impact_level")) == "UNKNOWN":
        status = "IMPACT_REVIEW_REQUIRED"; reasons.append("impact level unknown")
    elif not authority.get("authority_satisfied"):
        status = "AUTHORITY_REQUIRED"; reasons.extend(["explicit governing commitment missing"] if not authority.get("explicit_attribution") else [])
        reasons.extend([f"missing capability:{x}" for x in authority.get("missing_capabilities", [])])
    elif candidate.get("reversibility") == "UNKNOWN":
        status = "REVERSIBILITY_REQUIRED"; reasons.append("reversibility unknown")
    elif candidate.get("reversibility") in {"REVERSIBLE", "PARTIAL"} and not candidate.get("rollback_plan"):
        status = "ROLLBACK_REQUIRED"; reasons.append("rollback plan missing")
    elif not candidate.get("counterfactual_complete"):
        status = "COUNTERFACTUAL_REVIEW_REQUIRED"; reasons.append("expected effects/failure modes incomplete")
    elif not approval_ok:
        status = "APPROVAL_REQUIRED"; reasons.extend(approval_errors)
    elif candidate.get("reversibility") != "REVERSIBLE" or str(candidate.get("impact_level")) in {"HIGH", "CRITICAL"}:
        status = "HUMAN_EXECUTION_REQUIRED"; human_execution_required = True; reasons.append("approved but not eligible for autonomous host execution")
    else:
        status = "HOST_EXECUTION_ELIGIBLE"; execution_eligible = True; reasons.append("runtime governance checks satisfied")

    decision = ActionDecision(status, execution_eligible, proposal_allowed, human_execution_required, tuple(dict.fromkeys(reasons)))
    return {
        **asdict(decision),
        "authority": authority,
        "approval": approval,
        "approval_valid": approval_ok,
        "approval_errors": approval_errors,
        "boundaries": {
            "epistemic_support_does_not_grant_authority": True,
            "approval_does_not_grant_missing_capabilities": True,
            "runtime_never_executes_material_action": True,
            "host_system_safety_law_checks_still_required": True,
            "irreversible_or_high_impact_action_requires_human_execution": True,
        },
    }


def build_action_ledger(
    runtime: Any,
    cycle: dict[str, Any],
    *,
    central: dict[str, Any],
    mined: list[dict[str, Any]],
    atoms: list[dict[str, Any]] | None,
    intention_node_id: str,
) -> dict[str, Any]:
    evidence_before = {nid: float(getattr(node, "evidence", 0.0)) for nid, node in getattr(runtime, "nodes", {}).items()}
    atom_by_id = _approval_atom_map(mined, atoms)
    sem = cycle.get("semantic_slice", {})
    intent_sha = str(sem.get("intent_sha256") or "")
    candidates: list[dict[str, Any]] = []
    for row in sem.get("nodes", []):
        if str(row.get("kind")) != "action":
            continue
        candidate = _candidate(runtime, row, atom_by_id.get(str(row.get("id"))))
        approval = issue_same_turn_approval(
            runtime,
            candidate,
            atom=atom_by_id.get(candidate["node_id"]),
            intent_sha256=intent_sha,
            intention_node_id=intention_node_id,
        )
        decision = decide_action(
            runtime,
            candidate,
            central_mode=str(central.get("regulative_mode") or "REFLECTIVE_SYNTHESIS"),
            approval=approval,
            intent_sha256=intent_sha,
            intention_node_id=intention_node_id,
        )
        candidates.append({**candidate, "decision": decision})

    evidence_after = {nid: float(getattr(node, "evidence", 0.0)) for nid, node in getattr(runtime, "nodes", {}).items()}
    if evidence_before != evidence_after:
        raise RuntimeError("action governance modified evidence")

    host_eligible = [x for x in candidates if x["decision"]["status"] == "HOST_EXECUTION_ELIGIBLE"]
    human_only = [x for x in candidates if x["decision"]["status"] == "HUMAN_EXECUTION_REQUIRED"]
    blocked = [x for x in candidates if x["decision"]["status"] not in {"HOST_EXECUTION_ELIGIBLE", "HUMAN_EXECUTION_REQUIRED", "PROPOSABLE"}]
    material_candidates = [x for x in candidates if x.get("material")]
    material_host = [x for x in material_candidates if x["decision"]["status"] == "HOST_EXECUTION_ELIGIBLE"]
    material_human = [x for x in material_candidates if x["decision"]["status"] == "HUMAN_EXECUTION_REQUIRED"]
    material_blocked = [x for x in material_candidates if x["decision"]["status"] not in {"HOST_EXECUTION_ELIGIBLE", "HUMAN_EXECUTION_REQUIRED"}]
    if not candidates:
        material_action = "NONE"
    elif any(x["decision"]["status"] == "CENTRAL_BLOCKED" for x in candidates):
        material_action = "BLOCK"
    elif not material_candidates:
        material_action = "PROPOSE_ONLY"
    elif material_blocked:
        material_action = "REVIEW_REQUIRED"
    elif material_human:
        material_action = "HUMAN_EXECUTION_REQUIRED"
    elif len(material_host) == len(material_candidates):
        material_action = "HOST_EXECUTION_ELIGIBLE"
    else:
        material_action = "REVIEW_REQUIRED"
    ledger = {
        "schema": ACTION_LEDGER_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "intent_sha256": intent_sha,
        "candidate_count": len(candidates),
        "host_execution_eligible_count": len(host_eligible),
        "human_execution_required_count": len(human_only),
        "blocked_count": len(blocked),
        "material_action": material_action,
        "candidates": candidates,
        "evidence_modified": False,
        "epistemic_authority": 0.0,
        "execution_performed": False,
        "boundary": {
            "ledger_is_control_projection_not_world_evidence": True,
            "no_silent_execution": True,
            "host_must_recheck_system_safety_law_and_tool_capability": True,
            "counterfactual_checks_are_declared_metadata_not_real_world_causality": True,
        },
    }
    raw = json.dumps(ledger, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ledger["sha256"] = hashlib.sha256(raw).hexdigest()
    if getattr(runtime, "durable", False):
        from .store import atomic_json_write
        path = Path(runtime.state_dir) / "action-ledger.json"
        atomic_json_write(path, ledger)
        ledger["path"] = str(path)
    return ledger
