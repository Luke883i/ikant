from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .human_frame import ActorSessionBinding, validate_human_frame, validate_interaction_receipt
from .store import append_jsonl
from .temporal_memory import materialize_temporal_memory, set_temporal_state, temporal_available, temporal_state
from .temporal_replay import replay_temporal_events, temporal_events

MEMORY_GOVERNANCE_SCHEMA = "ikant-memory-governance/v1-test"
MEMORY_FORGET_PREVIEW_SCHEMA = "ikant-memory-forget-preview/v1-test"
MEMORY_GOVERNANCE_EVENT_SCHEMA = "ikant-memory-governance-event/v1-test"
MEMORY_FORGET_RECEIPT_SCHEMA = "ikant-memory-forget-receipt/v1-test"
DERIVATION_KINDS = {"supports", "abstracts", "associates", "retroacts", "activates"}
DERIVED_SOURCE_MODES = {"runtime_derived", "inference", "cache", "demo"}
ZERO = "0" * 64


class MemoryGovernanceError(RuntimeError):
    pass


class MemoryGovernanceAuthorityError(PermissionError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _event_hash(row: dict[str, Any]) -> str:
    material = {k: row[k] for k in ("schema", "seq", "origin_session_id", "op", "payload", "prev_sha256")}
    return _sha(material)


def _journal_path(runtime: Any) -> Path:
    return Path(runtime.state_dir) / "memory-governance-events.jsonl"


def governance_events(runtime: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if getattr(runtime, "durable", False):
        path = _journal_path(runtime)
        if path.exists():
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise MemoryGovernanceError(f"memory governance malformed json line {lineno}") from exc
    rows.extend(getattr(runtime, "_ikant_memory_governance_events_mem", []) or [])
    by: dict[int, dict[str, Any]] = {}
    for row in rows:
        seq = int(row.get("seq", 0))
        if seq < 1:
            raise MemoryGovernanceError("memory governance invalid sequence")
        if seq in by and by[seq] != row:
            raise MemoryGovernanceError("memory governance duplicate sequence divergence")
        by[seq] = row
    ordered = [by[k] for k in sorted(by)]
    prev = ZERO
    for seq, row in enumerate(ordered, 1):
        if row.get("schema") != MEMORY_GOVERNANCE_EVENT_SCHEMA or row.get("seq") != seq:
            raise MemoryGovernanceError("memory governance schema/sequence drift")
        if row.get("op") != "FORGET_COMMITTED":
            raise MemoryGovernanceError("memory governance unknown operation")
        if row.get("prev_sha256") != prev or row.get("sha256") != _event_hash(row):
            raise MemoryGovernanceError("memory governance hash-chain drift")
        prev = row["sha256"]
    return ordered


def _append_governance_event(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    rows = governance_events(runtime)
    row = {
        "schema": MEMORY_GOVERNANCE_EVENT_SCHEMA,
        "seq": len(rows) + 1,
        "origin_session_id": str(runtime.runtime.get("session_id") or ""),
        "op": "FORGET_COMMITTED",
        "payload": dict(payload),
        "prev_sha256": rows[-1]["sha256"] if rows else ZERO,
    }
    row["sha256"] = _event_hash(row)
    if getattr(runtime, "durable", False):
        append_jsonl(_journal_path(runtime), row)
    mem = getattr(runtime, "_ikant_memory_governance_events_mem", None)
    if mem is None:
        mem = []
        setattr(runtime, "_ikant_memory_governance_events_mem", mem)
    mem.append(row)
    governance_events(runtime)
    return row


def _kind(relation: Any) -> str:
    return str(getattr(getattr(relation, "kind", None), "value", getattr(relation, "kind", "")))


def _support_aware_closure(runtime: Any, root_id: str) -> tuple[list[str], list[str]]:
    affected = {root_id}
    relations = sorted((r for r in getattr(runtime, "relations", {}).values() if getattr(r, "active", True)), key=lambda r: str(getattr(r, "id", "")))
    changed = True
    while changed:
        changed = False
        for relation in relations:
            if _kind(relation) not in DERIVATION_KINDS:
                continue
            source = str(getattr(relation, "source", ""))
            target_id = str(getattr(relation, "target", ""))
            if source not in affected or target_id in affected:
                continue
            target = runtime.nodes.get(target_id)
            if target is None or str(getattr(target, "source_mode", "")) not in DERIVED_SOURCE_MODES:
                continue
            alternate = False
            for inbound in relations:
                if _kind(inbound) not in DERIVATION_KINDS or str(getattr(inbound, "target", "")) != target_id:
                    continue
                sid = str(getattr(inbound, "source", ""))
                if sid in affected:
                    continue
                support = runtime.nodes.get(sid)
                if support is not None and temporal_available(support):
                    alternate = True
                    break
            if not alternate:
                affected.add(target_id)
                changed = True
    downstream = set()
    for relation in relations:
        if _kind(relation) in DERIVATION_KINDS and str(getattr(relation, "source", "")) in affected:
            tid = str(getattr(relation, "target", ""))
            node = runtime.nodes.get(tid)
            if node is not None and str(getattr(node, "source_mode", "")) in DERIVED_SOURCE_MODES:
                downstream.add(tid)
    preserved = sorted(tid for tid in downstream if tid not in affected)
    return sorted(affected), preserved


def _task_impact(task_projection: dict[str, Any] | None, affected: set[str]) -> tuple[list[str], list[str]]:
    dependent: list[str] = []
    independent: list[str] = []
    for row in (task_projection or {}).get("tasks", []) if isinstance(task_projection, dict) else []:
        tid = str(row.get("task_id") or "")
        if not tid:
            continue
        deps = {str(x) for x in (row.get("memory_dependency_ids") or [])}
        if deps & affected:
            dependent.append(tid)
        elif row.get("status") in {"ACTIVE", "PAUSED_FAILURE", "PAUSED_GOVERNANCE"}:
            independent.append(tid)
    return sorted(set(dependent)), sorted(set(independent))


def preview_forget(runtime: Any, node_id: str, *, reason: str, task_projection: dict[str, Any] | None = None) -> dict[str, Any]:
    nid = str(node_id or "")
    if nid not in runtime.nodes:
        raise KeyError(nid)
    affected, preserved = _support_aware_closure(runtime, nid)
    states = {x: ("FORGOTTEN" if x == nid else "DEPENDENCY_INVALIDATED") for x in affected}
    dependent_tasks, independent_tasks = _task_impact(task_projection, set(affected))
    replay = replay_temporal_events(temporal_events(runtime))
    body = {
        "schema": MEMORY_FORGET_PREVIEW_SCHEMA,
        "runtime_session_id": str(runtime.runtime.get("session_id") or ""),
        "node_id": nid,
        "reason": str(reason),
        "suppressed_states": {k: states[k] for k in sorted(states)},
        "preserved_node_ids": preserved,
        "dependent_task_ids": dependent_tasks,
        "independent_task_ids": independent_tasks,
        "temporal_journal_tail_sha256": replay["journal_tail_sha256"],
        "already_unavailable": not temporal_available(runtime.nodes[nid]),
        "history_rewrite": False,
        "evidence_modified": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    body["preview_sha256"] = _sha(body)
    return body


def _verify_preview(preview: dict[str, Any]) -> None:
    raw = dict(preview or {})
    actual = raw.pop("preview_sha256", None)
    if raw.get("schema") != MEMORY_FORGET_PREVIEW_SCHEMA or actual != _sha(raw):
        raise ValueError("memory forget preview digest")


def forget_action_fingerprint(preview: dict[str, Any]) -> str:
    _verify_preview(preview)
    return "memory:forget:" + str(preview["preview_sha256"])


def validate_forget_authorization(preview: dict[str, Any], frame: dict[str, Any], receipt: dict[str, Any], *, binding: ActorSessionBinding, secret: bytes) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        _verify_preview(preview)
    except ValueError as exc:
        errors.append(str(exc))
    ok, frame_errors = validate_human_frame(frame)
    if not ok:
        errors.extend("frame:" + x for x in frame_errors)
    ok, receipt_errors = validate_interaction_receipt(frame, receipt, binding=binding, secret=secret)
    if not ok:
        errors.extend("receipt:" + x for x in receipt_errors)
    if frame.get("purpose") != "ACTION_CONFIRMATION" or receipt.get("decision") != "APPROVE":
        errors.append("explicit forget approval")
    if frame.get("session_id") != preview.get("runtime_session_id") or binding.session_id != preview.get("runtime_session_id"):
        errors.append("forget session")
    if frame.get("action_fingerprint") != forget_action_fingerprint(preview):
        errors.append("forget fingerprint")
    if frame.get("handoff_id") not in {None, ""}:
        errors.append("forget may not bind execution handoff")
    if frame.get("requested_entitlements") not in (None, [], ()):
        errors.append("forget may not carry entitlements")
    return not errors, list(dict.fromkeys(errors))


def reconcile_memory_governance(runtime: Any) -> dict[str, Any]:
    rows = governance_events(runtime)
    changed: list[str] = []
    for row in rows:
        payload = row.get("payload") or {}
        states = payload.get("suppressed_states") or {}
        replay_nodes = replay_temporal_events(temporal_events(runtime))["state"]["nodes"]
        for nid in sorted(states):
            node = runtime.nodes.get(nid)
            if node is None:
                continue
            wanted = str(states[nid])
            graph_state = temporal_state(node)
            replay_state = str((replay_nodes.get(nid) or {}).get("temporal_state") or "ACTIVE")
            if graph_state != wanted or replay_state != wanted:
                set_temporal_state(runtime, nid, wanted, reason=f"governed_forget:{row['sha256']}")
                changed.append(nid)
                replay_nodes = replay_temporal_events(temporal_events(runtime))["state"]["nodes"]
    if changed:
        materialize_temporal_memory(runtime)
    return {
        "schema": MEMORY_GOVERNANCE_SCHEMA,
        "ok": True,
        "events": len(rows),
        "reconciled_node_ids": sorted(set(changed)),
        "history_rewrite": False,
        "evidence_modified": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def apply_forget(runtime: Any, preview: dict[str, Any], frame: dict[str, Any], receipt: dict[str, Any], *, binding: ActorSessionBinding, secret: bytes, task_projection: dict[str, Any] | None = None) -> dict[str, Any]:
    ok, errors = validate_forget_authorization(preview, frame, receipt, binding=binding, secret=secret)
    if not ok:
        raise MemoryGovernanceAuthorityError("invalid forget authorization: " + "; ".join(errors))
    for existing in governance_events(runtime):
        if (existing.get("payload") or {}).get("preview_sha256") == preview["preview_sha256"]:
            rec = reconcile_memory_governance(runtime)
            return {
                "schema": MEMORY_FORGET_RECEIPT_SCHEMA,
                "status": "IDEMPOTENT",
                "preview_sha256": preview["preview_sha256"],
                "governance_event_sha256": existing["sha256"],
                "suppressed_node_ids": sorted((preview.get("suppressed_states") or {}).keys()),
                "dependent_task_ids": list(preview.get("dependent_task_ids") or []),
                "reconciled_node_ids": rec["reconciled_node_ids"],
                "history_rewrite": False,
                "evidence_modified": False,
                "epistemic_authority": 0.0,
                "execution_authority": 0.0,
            }
    current = preview_forget(runtime, str(preview["node_id"]), reason=str(preview.get("reason") or ""), task_projection=task_projection)
    if current["preview_sha256"] != preview["preview_sha256"]:
        raise MemoryGovernanceError("forget impact drifted after preview")
    before = {nid: float(node.evidence) for nid, node in runtime.nodes.items()}
    event = _append_governance_event(runtime, {
        "preview_sha256": preview["preview_sha256"],
        "node_id": preview["node_id"],
        "reason": preview.get("reason"),
        "suppressed_states": dict(preview.get("suppressed_states") or {}),
        "preserved_node_ids": list(preview.get("preserved_node_ids") or []),
        "dependent_task_ids": list(preview.get("dependent_task_ids") or []),
        "interaction_receipt_mac_sha256": receipt.get("mac_sha256"),
        "history_rewrite": False,
        "evidence_modified": False,
    })
    reconciled = reconcile_memory_governance(runtime)
    materialize_temporal_memory(runtime)
    after = {nid: float(node.evidence) for nid, node in runtime.nodes.items()}
    if before != after:
        raise MemoryGovernanceError("forget governance modified evidence")
    return {
        "schema": MEMORY_FORGET_RECEIPT_SCHEMA,
        "status": "COMMITTED",
        "preview_sha256": preview["preview_sha256"],
        "governance_event_sha256": event["sha256"],
        "suppressed_node_ids": sorted((preview.get("suppressed_states") or {}).keys()),
        "preserved_node_ids": list(preview.get("preserved_node_ids") or []),
        "dependent_task_ids": list(preview.get("dependent_task_ids") or []),
        "reconciled_node_ids": reconciled["reconciled_node_ids"],
        "history_rewrite": False,
        "evidence_modified": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
