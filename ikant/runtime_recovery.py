from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

RECOVERY_SCHEMA = "ikant-runtime-recovery/v1-test"
WORK_SCHEMA = "ikant-reactive-work-state/v1-test"


def _zero_authority(**extra: Any) -> dict[str, Any]:
    return {
        **extra,
        "model_reexecuted": False,
        "planner_reexecuted": False,
        "material_driver_reexecuted": False,
        "presentation_is_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _journal_rows(guard: Any) -> list[dict[str, Any]]:
    path = Path(guard.journal_path)
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _sealed_cycles(guard: Any) -> set[str]:
    out: set[str] = set()
    for row in _journal_rows(guard):
        if row.get("event") != "SEAL_FRAME":
            continue
        cycle = str((row.get("payload") or {}).get("cycle_id") or "")
        if cycle:
            out.add(cycle)
    return out


def _chat_state(runtime: Any) -> tuple[Any, list[dict[str, Any]]]:
    from .chat_session import ChatLog

    session = str(runtime.runtime.get("session_id") or "")
    log = ChatLog(Path(runtime.state_dir) / "chat" / "transcript.jsonl", runtime_session_id=session)
    log.verify()
    return log, log.rows()


def _surface_a_from_state(runtime: Any, rows: list[dict[str, Any]], cycle_id: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row.get("role") == "ikant" and str(row.get("cycle_id") or "") == cycle_id:
            text = str(row.get("text") or "").strip()
            if text:
                return {"text": text, "response_id": str(row.get("response_id") or "") or None, "source": "VERIFIED_CHAT", "chat_seq": row.get("seq")}
    cog = runtime.runtime.get("cognitive") if isinstance(runtime.runtime.get("cognitive"), dict) else {}
    if str(cog.get("last_surface_a_cycle_id") or "") != cycle_id:
        return None
    response_id = str(cog.get("last_surface_a_response_id") or "")
    node = runtime.nodes.get(response_id) if response_id else None
    if node is None:
        return None
    metadata = dict(getattr(node, "metadata", {}) or {})
    cycles = {str(x) for x in metadata.get("response_cycles", [])}
    if getattr(node, "source_mode", None) != "runtime_derived" or float(getattr(node, "evidence", 1.0)) != 0.0 or metadata.get("surface_a_validated") is not True or cycle_id not in cycles:
        return None
    text = str(getattr(node, "text", "") or "").strip()
    if not text:
        return None
    return {"text": text, "response_id": response_id, "source": "VALIDATED_RESPONSE_NODE", "chat_seq": None}


def verified_recovery(runtime: Any) -> dict[str, Any]:
    from .session_egress import EgressState, existing_runtime_egress

    if runtime.runtime.get("status") != "ACTIVE":
        return _zero_authority(schema=RECOVERY_SCHEMA, state="PRE_ACTIVE", recovery_required=False, cycle_id=None)
    guard = existing_runtime_egress(runtime)
    if guard is None:
        return _zero_authority(schema=RECOVERY_SCHEMA, state="INTEGRITY_BLOCKED", recovery_required=True, cycle_id=None, reason="ACTIVE runtime has no egress guard")
    guard.verify()
    if guard.state == EgressState.BREACHED:
        return _zero_authority(schema=RECOVERY_SCHEMA, state="INTEGRITY_BLOCKED", recovery_required=True, cycle_id=guard.record.last_cycle_id, reason=guard.record.breach_reason or "egress breached")
    log, rows = _chat_state(runtime)
    del log
    sealed = _sealed_cycles(guard)
    cog = runtime.runtime.get("cognitive") if isinstance(runtime.runtime.get("cognitive"), dict) else {}
    pending = str(cog.get("pending_surface_a_cycle_id") or "") or None
    if guard.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
        pending_frame = guard.pending_frame()
        if pending_frame is None:
            raise RuntimeError("pending egress has no recoverable frame")
        receipt, text = pending_frame
        return _zero_authority(schema=RECOVERY_SCHEMA, state="SEALED_FRAME_PENDING", recovery_required=False, cycle_id=receipt.cycle_id, frame_sha256=receipt.frame_sha256, frame_seq=receipt.frame_seq, egress_epoch=receipt.epoch, release_after_frame=receipt.release_after_frame, frame_bytes=len(text.encode("utf-8")), recovery_basis="DURABLE_EGRESS_FRAME")
    if guard.state == EgressState.RELEASED:
        return _zero_authority(schema=RECOVERY_SCHEMA, state="RELEASED", recovery_required=False, cycle_id=guard.record.last_cycle_id)
    if pending:
        reply = _surface_a_from_state(runtime, rows, pending)
        if reply is not None:
            raise RuntimeError("pending cognitive cycle already has validated Surface A")
        if guard.record.last_kind == "RECOVERY" and str(guard.record.last_cycle_id or "") == pending:
            return _zero_authority(schema=RECOVERY_SCHEMA, state="RECOVERY_ACKED_PENDING_RECONCILE", recovery_required=True, cycle_id=pending, recovery_basis="ACKED_RECOVERY_FRAME")
        return _zero_authority(schema=RECOVERY_SCHEMA, state="INTERRUPTED_UNSEALED", recovery_required=True, cycle_id=pending, recovery_basis="PENDING_COGNITIVE_WITH_LOCKED_EGRESS")
    last_surface_cycle = str(cog.get("last_surface_a_cycle_id") or "") or None
    if last_surface_cycle and last_surface_cycle not in sealed:
        reply = _surface_a_from_state(runtime, rows, last_surface_cycle)
        if reply is None:
            return _zero_authority(schema=RECOVERY_SCHEMA, state="INTEGRITY_BLOCKED", recovery_required=True, cycle_id=last_surface_cycle, reason="validated Surface A marker has no recoverable content")
        return _zero_authority(schema=RECOVERY_SCHEMA, state="SURFACE_A_UNSEALED", recovery_required=True, cycle_id=last_surface_cycle, surface_a_text=reply["text"], response_id=reply["response_id"], recovery_basis=reply["source"], chat_seq=reply["chat_seq"])
    return _zero_authority(schema=RECOVERY_SCHEMA, state="ACTIVE_CANONICAL", recovery_required=False, cycle_id=guard.record.last_cycle_id)


def reconcile_surface_a_chat(runtime: Any, recovery: dict[str, Any]) -> dict[str, Any]:
    if recovery.get("state") != "SURFACE_A_UNSEALED":
        return recovery
    from .chat_session import ChatLog
    cycle = str(recovery.get("cycle_id") or "")
    text = str(recovery.get("surface_a_text") or "").strip()
    response_id = str(recovery.get("response_id") or "") or None
    session = str(runtime.runtime.get("session_id") or "")
    log = ChatLog(Path(runtime.state_dir) / "chat" / "transcript.jsonl", runtime_session_id=session)
    log.verify()
    rows = log.rows()
    existing = [r for r in rows if r.get("role") == "ikant" and str(r.get("cycle_id") or "") == cycle]
    if existing:
        return {**recovery, "chat_reconciled": False, "chat_seq": existing[-1].get("seq")}
    replied = {int(r["reply_to_seq"]) for r in rows if r.get("role") == "ikant" and isinstance(r.get("reply_to_seq"), int)}
    candidates = [r for r in rows if r.get("role") == "user" and str(r.get("cycle_id") or "") == cycle and int(r.get("seq") or 0) not in replied]
    if len(candidates) != 1:
        raise RuntimeError("Surface A recovery requires exactly one unanswered same-cycle user record")
    user = candidates[0]
    row = log.append("ikant", text, cycle_id=cycle, response_id=response_id, intention_node_id=user.get("intention_node_id"), reply_to_seq=int(user["seq"]), metadata={"surface_a_validated": True, "speech_act_not_evidence": True, "recovered_after_restart": True})
    runtime._event("RUNTIME_RECOVERY_CHAT_RECONCILE", cycle, {"response_id": response_id, "chat_seq": row["seq"]})
    return {**recovery, "chat_reconciled": True, "chat_seq": row["seq"]}


def reconcile_interrupted_turn(runtime: Any, recovery: dict[str, Any] | None = None) -> dict[str, Any]:
    current = recovery or verified_recovery(runtime)
    if current.get("state") not in {"INTERRUPTED_UNSEALED", "RECOVERY_ACKED_PENDING_RECONCILE"}:
        return current
    cycle = str(current.get("cycle_id") or "")
    cog = runtime.runtime.setdefault("cognitive", {})
    if str(cog.get("pending_surface_a_cycle_id") or "") != cycle:
        raise RuntimeError("recovery cycle drift")
    cog.pop("pending_surface_a_cycle_id", None)
    cog.pop("pending_interaction_contract", None)
    cog["last_runtime_recovery"] = {"schema": RECOVERY_SCHEMA, "state": "INTERRUPTED_UNSEALED_ACKED", "cycle_id": cycle, "model_reexecuted": False, "planner_reexecuted": False, "material_driver_reexecuted": False, "epistemic_authority": 0.0, "execution_authority": 0.0}
    runtime._write_runtime()
    runtime._event("RUNTIME_RECOVERY_ABORT_PENDING", cycle, {"after_exact_recovery_ack": True, "model_reexecuted": False, "planner_reexecuted": False, "material_driver_reexecuted": False})
    return verified_recovery(runtime)


def materialize_recovery_frame(runtime: Any) -> dict[str, Any] | None:
    from .human_dashboard import persist_dashboard
    from .session_host import prepare_human_frame
    from .web_frame import wrap_prepared_frame
    recovery = verified_recovery(runtime)
    if recovery.get("state") == "RECOVERY_ACKED_PENDING_RECONCILE":
        reconcile_interrupted_turn(runtime, recovery)
        return None
    cycle = str(recovery.get("cycle_id") or "") or None
    if recovery.get("state") == "INTERRUPTED_UNSEALED":
        message = "Il turno è stato interrotto prima della consegna. Nessuna risposta è stata rigenerata. Puoi riprovare dopo questa conferma."
        dashboard = persist_dashboard(runtime)
        prepared = prepare_human_frame(runtime, dashboard, kind="RECOVERY", cycle_id=cycle, recovery={"reason": message})
        frame = wrap_prepared_frame(prepared, primary_text="iKant: " + message)
        frame["runtime_recovery"] = deepcopy(recovery)
        return frame
    if recovery.get("state") == "SURFACE_A_UNSEALED":
        recovery = reconcile_surface_a_chat(runtime, recovery)
        text = str(recovery.get("surface_a_text") or "").strip()
        dashboard = persist_dashboard(runtime, surface_a_text=text, cycle_id=cycle, surface_a_validated=True)
        prepared = prepare_human_frame(runtime, dashboard, kind="RECOVERY", cycle_id=cycle, recovery={"reason": "Risposta validata recuperata localmente dopo riavvio; nessuna nuova generazione eseguita."})
        frame = wrap_prepared_frame(prepared, primary_text="iKant: " + text)
        frame["runtime_recovery"] = deepcopy(recovery)
        return frame
    return None


def recovery_ack_target(root: str | Path) -> dict[str, Any] | None:
    from .runtime import Runtime
    from .session_egress import EgressState, existing_runtime_egress
    rt = Runtime(Path(root).resolve() / ".ikant")
    try:
        guard = existing_runtime_egress(rt)
        if not guard or guard.state not in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
            return None
        rec = guard.record
        if rec.last_kind != "RECOVERY":
            return None
        recovery = verified_recovery(rt)
        return {"cycle_id": rec.last_cycle_id, "recovery_state": recovery.get("state")}
    finally:
        rt.close()


def finalize_recovery_after_ack(root: str | Path, target: dict[str, Any] | None) -> None:
    if not target or target.get("recovery_state") != "SEALED_FRAME_PENDING":
        return
    cycle = str(target.get("cycle_id") or "")
    if not cycle:
        return
    from .runtime import Runtime
    rt = Runtime(Path(root).resolve() / ".ikant")
    try:
        cog = rt.runtime.get("cognitive") if isinstance(rt.runtime.get("cognitive"), dict) else {}
        if str(cog.get("pending_surface_a_cycle_id") or "") == cycle:
            current = verified_recovery(rt)
            if current.get("state") == "RECOVERY_ACKED_PENDING_RECONCILE":
                reconcile_interrupted_turn(rt, current)
    finally:
        rt.close()


def recover_work_projection(live_work: dict[str, Any], recovery: dict[str, Any]) -> dict[str, Any]:
    live = deepcopy(live_work) if isinstance(live_work, dict) else {}
    if live.get("active") is True:
        live.setdefault("facts", {})["recovery_source"] = "LIVE_PROCESS"
        return live
    state = str(recovery.get("state") or "")
    if state == "SEALED_FRAME_PENDING":
        return _zero_authority(schema=WORK_SCHEMA, phase="SEALED", moment="DELIVERY", active=True, terminal=False, message="La risposta è pronta; sto completando la consegna.", detail="Stato di consegna ricostruito dal frame canonico durevole.", facts={"route": "RECOVERY_CANONICAL", "recovery_source": "DURABLE_EGRESS_FRAME"}, cycle_bound=bool(recovery.get("cycle_id")), progress_fraction=None, identifiers_exposed=False, private_chain_of_thought=False, raw_prompt_exposed=False)
    if state in {"INTERRUPTED_UNSEALED", "RECOVERY_ACKED_PENDING_RECONCILE"}:
        return _zero_authority(schema=WORK_SCHEMA, phase="FAILED", moment="DEGRADED", active=False, terminal=True, message="Il turno precedente è stato interrotto in modo controllato.", detail="Nessuna risposta o azione è stata rigenerata automaticamente.", facts={"route": "INTERRUPTED_UNSEALED", "recovery_source": "DURABLE_RUNTIME"}, cycle_bound=bool(recovery.get("cycle_id")), progress_fraction=None, identifiers_exposed=False, private_chain_of_thought=False, raw_prompt_exposed=False)
    if state == "SURFACE_A_UNSEALED":
        return _zero_authority(schema=WORK_SCHEMA, phase="SEALED", moment="DELIVERY", active=True, terminal=False, message="Una risposta validata è stata recuperata localmente.", detail="La risposta viene riconsegnata senza nuova generazione.", facts={"route": "RECOVERY_SURFACE_A", "recovery_source": recovery.get("recovery_basis")}, cycle_bound=True, progress_fraction=None, identifiers_exposed=False, private_chain_of_thought=False, raw_prompt_exposed=False)
    if state == "INTEGRITY_BLOCKED":
        return _zero_authority(schema=WORK_SCHEMA, phase="FAILED", moment="DEGRADED", active=False, terminal=True, message="Stato runtime non verificabile.", detail="La proiezione derivativa non viene ricostruita.", facts={"route": "RECOVERY_BLOCKED"}, cycle_bound=False, progress_fraction=None, identifiers_exposed=False, private_chain_of_thought=False, raw_prompt_exposed=False)
    return live or {"schema": WORK_SCHEMA, "phase": "IDLE", "moment": "READY", "active": False, "terminal": True, "message": "", "detail": "", "facts": {}, "progress_fraction": None, "identifiers_exposed": False, "private_chain_of_thought": False, "epistemic_authority": 0.0, "execution_authority": 0.0}


def recover_work_for_root(root: str | Path, live_work: dict[str, Any]) -> dict[str, Any]:
    if isinstance(live_work, dict) and live_work.get("active") is True:
        return recover_work_projection(live_work, {"state": "LIVE"})
    from .runtime import Runtime
    try:
        rt = Runtime(Path(root).resolve() / ".ikant")
    except RuntimeError as exc:
        if "already locked by another writer" in str(exc):
            return live_work
        raise
    try:
        recovery = verified_recovery(rt)
        return recover_work_projection(live_work, recovery)
    finally:
        rt.close()
