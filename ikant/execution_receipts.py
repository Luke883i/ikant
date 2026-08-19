from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .plan_graph import normalize_predicate

REVALIDATION_RECEIPT_SCHEMA = "ikant-host-revalidation-receipt/v0.17-test"
EXECUTION_RECEIPT_SCHEMA = "ikant-execution-receipt/v0.17-test"
EXECUTION_RECEIPT_REGISTRY_SCHEMA = "ikant-execution-receipt-registry/v0.17-test"
_OUTCOMES = {"EXECUTED", "FAILED", "DECLINED", "UNKNOWN"}


def _digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def seal_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.pop("receipt_sha256", None)
    out["receipt_sha256"] = _digest(out)
    return out


def _digest_valid(receipt: dict[str, Any]) -> bool:
    copy = dict(receipt)
    actual = copy.pop("receipt_sha256", None)
    return bool(actual) and actual == _digest(copy)


def validate_revalidation_receipt(envelope: dict[str, Any], receipt: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not receipt:
        return False, ["revalidation receipt missing"]
    errors: list[str] = []
    if receipt.get("schema") != REVALIDATION_RECEIPT_SCHEMA:
        errors.append("revalidation schema")
    if not _digest_valid(receipt):
        errors.append("revalidation digest")
    if envelope.get("handoff_kind") != "HOST":
        errors.append("revalidation only valid for host handoff")
    for key in ("session_id", "cycle_id", "intent_sha256", "handoff_id", "idempotency_key", "action_fingerprint", "action_ledger_sha256", "plan_ledger_sha256"):
        if receipt.get(key) != envelope.get(key):
            errors.append(f"revalidation binding:{key}")
    if receipt.get("actor_type") != "host":
        errors.append("revalidation actor")
    if receipt.get("system_safety_law_checked") is not True:
        errors.append("system/safety/law revalidation missing")
    if receipt.get("tool_capability_checked") is not True:
        errors.append("tool capability revalidation missing")
    if receipt.get("current_action_status") != "HOST_EXECUTION_ELIGIBLE":
        errors.append("current action status")
    if receipt.get("grants_runtime_execution_authority") is not False:
        errors.append("revalidation authority escalation")
    if receipt.get("executes_action") is not False:
        errors.append("revalidation executes action")
    return not errors, errors


def validate_execution_receipt(
    envelope: dict[str, Any],
    receipt: dict[str, Any] | None,
    *,
    revalidation_receipt: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    if not receipt:
        return False, ["execution receipt missing"]
    errors: list[str] = []
    if receipt.get("schema") != EXECUTION_RECEIPT_SCHEMA:
        errors.append("execution receipt schema")
    if not _digest_valid(receipt):
        errors.append("execution receipt digest")
    for key in ("session_id", "cycle_id", "intent_sha256", "handoff_id", "idempotency_key", "action_fingerprint", "action_ledger_sha256", "plan_ledger_sha256"):
        if receipt.get(key) != envelope.get(key):
            errors.append(f"execution binding:{key}")
    outcome = str(receipt.get("outcome") or "")
    if outcome not in _OUTCOMES:
        errors.append("execution outcome")
    actor = str(receipt.get("actor_type") or "")
    kind = str(envelope.get("handoff_kind") or "NONE")
    if kind == "HOST" and actor != "host":
        errors.append("execution actor host")
    if kind == "HUMAN" and actor != "human":
        errors.append("execution actor human")
    if kind not in {"HOST", "HUMAN"}:
        errors.append("envelope not handoffable")
    if envelope.get("handoff_state") == "PREDECESSOR_RECONCILIATION_REQUIRED" and outcome in {"EXECUTED", "FAILED"}:
        errors.append("predecessor reconciliation required")
    if kind == "HOST" and outcome in {"EXECUTED", "FAILED"}:
        ok, re_errors = validate_revalidation_receipt(envelope, revalidation_receipt)
        if not ok:
            errors.extend([f"host:{x}" for x in re_errors])
    if outcome in {"EXECUTED", "FAILED"} and not str(receipt.get("execution_ref") or "").strip():
        errors.append("execution reference missing")
    try:
        normalized = [normalize_predicate(x) for x in receipt.get("observed_predicates", []) or []]
    except ValueError:
        errors.append("observed predicate invalid")
        normalized = []
    if len(normalized) != len(set(normalized)):
        errors.append("observed predicate duplicate")
    if receipt.get("runtime_epistemic_authority") not in {0, 0.0}:
        errors.append("execution receipt epistemic authority")
    if receipt.get("grants_runtime_execution_authority") is not False:
        errors.append("execution receipt authority escalation")
    if receipt.get("causes_runtime_execution") is not False:
        errors.append("execution receipt causes execution")
    return not errors, errors


def record_execution_receipt(
    runtime: Any,
    envelope: dict[str, Any],
    receipt: dict[str, Any],
    *,
    revalidation_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_before = {
        nid: float(getattr(node, "evidence", 0.0))
        for nid, node in getattr(runtime, "nodes", {}).items()
    }
    ok, errors = validate_execution_receipt(envelope, receipt, revalidation_receipt=revalidation_receipt)
    if not ok:
        return {"status": "REJECTED", "errors": errors, "recorded": False, "epistemic_authority": 0.0, "execution_authority": 0.0}
    state = getattr(runtime, "runtime", {}).setdefault("execution_protocol", {})
    terminal = state.setdefault("terminal_receipts", {})
    key = str(envelope.get("idempotency_key") or "")
    digest = str(receipt.get("receipt_sha256") or "")
    existing = terminal.get(key)
    if existing:
        if existing.get("receipt_sha256") == digest:
            status = "IDEMPOTENT_REPLAY"
            recorded = False
        else:
            status = "RECEIPT_CONFLICT"
            recorded = False
    else:
        terminal[key] = {
            "handoff_id": envelope.get("handoff_id"),
            "receipt_sha256": digest,
            "outcome": receipt.get("outcome"),
            "execution_ref": receipt.get("execution_ref"),
            "authority": 0.0,
        }
        status = "RECORDED"
        recorded = True
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    if getattr(runtime, "durable", False):
        from .store import atomic_json_write
        projection = {
            "schema": EXECUTION_RECEIPT_REGISTRY_SCHEMA,
            "terminal_receipts": terminal,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        atomic_json_write(Path(runtime.state_dir) / "execution-receipts.json", projection)
    evidence_after = {
        nid: float(getattr(node, "evidence", 0.0))
        for nid, node in getattr(runtime, "nodes", {}).items()
    }
    if evidence_before != evidence_after:
        raise RuntimeError("execution receipt modified evidence")
    return {
        "status": status,
        "errors": [],
        "recorded": recorded,
        "receipt_sha256": digest,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
        "runtime_executed_action": False,
    }
