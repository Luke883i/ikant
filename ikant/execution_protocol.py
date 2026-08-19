from __future__ import annotations
from typing import Any
from .execution_handoff import EXECUTION_HANDOFF_SCHEMA, build_execution_ledger
from .execution_receipts import record_execution_receipt
from .outcome_reconciliation import reconcile_execution_outcome

EXECUTION_PROTOCOL_SCHEMA = "ikant-execution-protocol/v0.17-test"

def finalize_execution_protocol(runtime: Any, cycle: dict[str, Any], practical: dict[str, Any]) -> dict[str, Any]:
    ledger = build_execution_ledger(runtime, cycle, practical)
    state = getattr(runtime, "runtime", {}).setdefault("execution_protocol", {})
    state["last"] = {"schema": EXECUTION_PROTOCOL_SCHEMA, "cycle_id": cycle.get("cycle_id"), "execution_ledger_sha256": ledger.get("sha256"), "handoff_count": ledger.get("handoff_count", 0), "authority": 0.0, "runtime_execution_performed": False}
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    return {"schema": EXECUTION_PROTOCOL_SCHEMA, "handoff_schema": EXECUTION_HANDOFF_SCHEMA, "execution_ledger": ledger, "epistemic_authority": 0.0, "execution_authority": 0.0, "runtime_execution_performed": False, "boundaries": {"runtime_prepares_but_never_executes": True, "external_revalidation_is_exactly_bound": True, "receipt_acceptance_is_not_world_truth": True, "receipt_replay_is_idempotent_or_conflicting": True, "outcome_reconciliation_never_auto_advances": True, "receipt_digest_is_integrity_not_actor_authentication": True, "host_transport_authentication_is_external": True}}

def accept_and_reconcile(runtime: Any, envelope: dict[str, Any], receipt: dict[str, Any], *, revalidation_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    recording = record_execution_receipt(runtime, envelope, receipt, revalidation_receipt=revalidation_receipt)
    if recording.get("status") not in {"RECORDED", "IDEMPOTENT_REPLAY"}:
        return {"recording": recording, "reconciliation": None, "runtime_execution_performed": False}
    reconciliation = reconcile_execution_outcome(envelope, receipt)
    return {"recording": recording, "reconciliation": reconciliation, "runtime_execution_performed": False, "epistemic_authority": 0.0, "execution_authority": 0.0}
