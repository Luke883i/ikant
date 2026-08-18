from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

INCARNATE_SCHEMA = "ikant-incarnate-egress/v0.7-test"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _file_descriptor(path_value: Any) -> dict[str, Any]:
    path_text = str(path_value or "").strip()
    if not path_text:
        return {"path": None, "name": None, "available": False, "bytes": None, "sha256": None}
    path = Path(path_text)
    try:
        stat = path.stat()
    except OSError:
        return {"path": path_text, "name": path.name, "available": False, "bytes": None, "sha256": None}
    if not path.is_file():
        return {"path": path_text, "name": path.name, "available": False, "bytes": None, "sha256": None}
    return {
        "path": path_text,
        "name": path.name,
        "available": True,
        "bytes": int(stat.st_size),
        "sha256": _sha256_file(path),
    }


def _surface_b(runtime: Any, expected_cycle: str | None) -> tuple[dict[str, Any], list[str]]:
    state = runtime.runtime if isinstance(getattr(runtime, "runtime", None), dict) else {}
    cognitive = state.get("cognitive") or {}
    session_id = str(state.get("session_id") or "") or None
    json_desc = _file_descriptor(cognitive.get("last_snapshot"))
    docx_desc = _file_descriptor(cognitive.get("last_surface_b_docx"))
    errors: list[str] = []
    snapshot: dict[str, Any] | None = None
    snapshot_cycle = None
    snapshot_session = None
    if json_desc["available"]:
        snapshot = _read_json(Path(str(json_desc["path"])))
        if snapshot is None:
            errors.append("surface_b_json_unreadable")
        else:
            snapshot_cycle = snapshot.get("cycle_id")
            snapshot_session = snapshot.get("session_id")
    if expected_cycle:
        if not json_desc["available"]:
            errors.append("surface_b_json_missing")
        if not docx_desc["available"]:
            errors.append("surface_b_docx_missing")
        if snapshot is not None and snapshot_cycle != expected_cycle:
            errors.append("surface_b_cycle_mismatch")
    if snapshot is not None and session_id and snapshot_session not in {None, session_id}:
        errors.append("surface_b_session_mismatch")
    bound = bool(
        expected_cycle
        and json_desc["available"]
        and docx_desc["available"]
        and snapshot is not None
        and snapshot_cycle == expected_cycle
        and snapshot_session in {None, session_id}
    )
    return {
        "available": bool(json_desc["available"] and docx_desc["available"]),
        "bound": bound,
        "cycle_id": snapshot_cycle,
        "session_id": snapshot_session,
        "json": json_desc,
        "docx": docx_desc,
    }, errors


def bind_dashboard(
    runtime: Any,
    dashboard: dict[str, Any],
    *,
    surface_a_text: str | None = None,
    cycle_id: str | None = None,
    surface_a_validated: bool = False,
) -> dict[str, Any]:
    """Bind human-facing dashboard output to one Surface A / Surface B cycle.

    This function never creates evidence. It only inspects persisted runtime state and
    strengthens the human egress contract. A validated Surface A is renderable only
    when its Surface B JSON+DOCX pair is present and bound to the same cycle.
    """
    state = runtime.runtime if isinstance(getattr(runtime, "runtime", None), dict) else {}
    cognitive = state.get("cognitive") or {}
    pending = str(cognitive.get("pending_surface_a_cycle_id") or "") or None
    text = None if surface_a_text is None else str(surface_a_text)
    # A later dashboard render must retain the last validated Surface A instead of
    # degrading to IDLE. The response node is a persisted speech act with zero evidence.
    if text is None and not pending and not surface_a_validated:
        response_id = cognitive.get("last_surface_a_response_id")
        node = getattr(runtime, "nodes", {}).get(response_id) if response_id else None
        metadata = getattr(node, "metadata", {}) if node is not None else {}
        if node is not None and metadata.get("surface_a_validated") is True:
            text = str(getattr(node, "text", ""))
            cycle_id = cycle_id or cognitive.get("last_surface_a_cycle_id") or metadata.get("last_cycle_id")
            surface_a_validated = bool(text.strip() and cycle_id)
    expected = str(cycle_id or pending or dashboard.get("surface_b", {}).get("cycle_id") or "") or None
    errors: list[str] = []

    if cycle_id and pending and cycle_id != pending:
        errors.append("pending_cycle_mismatch")
    if surface_a_validated:
        if pending:
            errors.append("validated_surface_a_still_pending")
        if not text or not text.strip():
            errors.append("validated_surface_a_missing")
        if not expected:
            errors.append("validated_surface_a_cycle_missing")
    elif text and text.strip():
        errors.append("surface_a_text_not_validated")

    surface_b, b_errors = _surface_b(runtime, expected)
    errors.extend(b_errors)
    if surface_a_validated and not surface_b.get("bound"):
        errors.append("validated_surface_a_without_bound_surface_b")

    if errors:
        egress_state = "BLOCKED"
    elif surface_a_validated:
        egress_state = "READY"
    elif pending:
        egress_state = "PENDING"
    else:
        egress_state = "IDLE"

    a_status = "VALIDATED" if surface_a_validated else ("PENDING" if pending else "EMPTY")
    dashboard["incarnate"] = {
        "schema": INCARNATE_SCHEMA,
        "state": egress_state,
        "cycle_id": expected,
        "surface_a": {
            "status": a_status,
            "cycle_id": expected,
            "text": text if surface_a_validated else None,
            "inside_dashboard": True,
        },
        "surface_b": surface_b,
        "errors": list(dict.fromkeys(errors)),
        "invariants": {
            "single_human_egress": True,
            "surface_a_inside_dashboard": True,
            "surface_b_docx_required": True,
            "same_cycle_binding_required": True,
            "render_validated_surface_a_only_after_close": True,
            "concurrent_pending_turns_forbidden": True,
        },
    }
    contract = dashboard.setdefault("contract", {})
    contract.update(
        {
            "single_human_egress": True,
            "surface_a_inside_dashboard": True,
            "surface_b_docx_required_per_substantive_turn": True,
            "surface_a_surface_b_same_cycle_required": True,
            "concurrent_pending_turns_forbidden": True,
        }
    )
    if errors:
        dashboard["overall"] = "BLOCKED"
    elif egress_state == "PENDING" and dashboard.get("overall") == "STABLE":
        dashboard["overall"] = "WATCH"
    return dashboard


def validate_incarnate_dashboard(dashboard: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    inc = dashboard.get("incarnate") or {}
    if inc.get("schema") != INCARNATE_SCHEMA:
        errors.append("incarnate_schema")
    invariants = inc.get("invariants") or {}
    for key in (
        "single_human_egress",
        "surface_a_inside_dashboard",
        "surface_b_docx_required",
        "same_cycle_binding_required",
        "render_validated_surface_a_only_after_close",
        "concurrent_pending_turns_forbidden",
    ):
        if invariants.get(key) is not True:
            errors.append("invariant_" + key)
    state = inc.get("state")
    a = inc.get("surface_a") or {}
    b = inc.get("surface_b") or {}
    internal_errors = list(inc.get("errors") or [])
    if state == "READY":
        if a.get("status") != "VALIDATED" or not str(a.get("text") or "").strip():
            errors.append("ready_surface_a")
        if not b.get("bound"):
            errors.append("ready_surface_b")
        if a.get("cycle_id") != inc.get("cycle_id") or b.get("cycle_id") != inc.get("cycle_id"):
            errors.append("ready_cycle_binding")
        if internal_errors:
            errors.append("ready_with_errors")
    elif state == "PENDING":
        if a.get("status") != "PENDING":
            errors.append("pending_surface_a")
        if not b.get("bound"):
            errors.append("pending_surface_b")
    elif state == "BLOCKED":
        if not internal_errors:
            errors.append("blocked_without_error")
    elif state != "IDLE":
        errors.append("state_unknown")
    return not errors, list(dict.fromkeys(errors))
