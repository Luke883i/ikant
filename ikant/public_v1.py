from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .chat_session import ChatLog, sanitize_terminal_text
from .experience_projection import runtime_projection
from .foundation import foundation_projection

PUBLIC_EXPERIENCE_SCHEMA = "ikant-public-experience/v1-test"
PUBLIC_RELEASE = "v1.0-public-test"
VISIBLE_CHAT_LIMIT = 32
VISIBLE_TEXT_BYTES = 6144
MAX_SYSTEM_FILE_BYTES = 2 * 1024 * 1024

_SYSTEM_PROJECTIONS = (
    ("managed_model", "Motore locale", "model-runtime.json"),
    ("host_conformance", "Conformità host", "host-conformance.json"),
    ("agency", "Capability e lease", "agency.json"),
    ("temporal_memory", "Memoria temporale", "temporal-memory.json"),
    ("practical_reason", "Valutazione azioni", "action-ledger.json"),
    ("planning", "Pianificazione", "plan-ledger.json"),
    ("execution", "Riconciliazione esecuzione", "execution-ledger.json"),
    ("temporal_autonomy", "Attività temporali", "temporal-autonomy.json"),
)


def _json_object(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size <= 0 or stat.st_size > MAX_SYSTEM_FILE_BYTES:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _bounded_text(value: object, limit: int = VISIBLE_TEXT_BYTES) -> str:
    text = sanitize_terminal_text(str(value or "")).strip()
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text
    return raw[:limit].decode("utf-8", errors="ignore").rstrip() + "…"


def conversation_projection(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    runtime = _json_object(root / ".ikant" / "runtime.json")
    session_id = str(runtime.get("session_id") or "")
    path = root / ".ikant" / "chat" / "transcript.jsonl"
    if not session_id or not path.is_file():
        return {
            "status": "EMPTY",
            "runtime_session_id": session_id or None,
            "records": [],
            "integrity_verified": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
    log = ChatLog(path, runtime_session_id=session_id)
    index = log.verify()
    rows = log.rows()[-VISIBLE_CHAT_LIMIT:]
    records = []
    for row in rows:
        role = str(row.get("role") or "")
        if role not in {"user", "ikant"}:
            continue
        records.append({
            "seq": int(row.get("seq") or 0),
            "role": role,
            "text": _bounded_text(row.get("text")),
            "at": str(row.get("at") or "")[:64] or None,
            "cycle_id": str(row.get("cycle_id") or "")[:160] or None,
        })
    return {
        "status": "AVAILABLE",
        "runtime_session_id": session_id,
        "records": records,
        "record_limit": VISIBLE_CHAT_LIMIT,
        "integrity_verified": bool(index.get("ok")),
        "last_sha256": index.get("last_sha256"),
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def runtime_system_projection(root: str | Path) -> dict[str, Any]:
    state = Path(root).resolve() / ".ikant"
    systems = []
    for system_id, label, filename in _SYSTEM_PROJECTIONS:
        value = _json_object(state / filename)
        if not value:
            continue
        schema = str(value.get("schema") or "")[:160] or None
        status = value.get("status", value.get("state", value.get("overall", "PRESENT")))
        if isinstance(status, (dict, list)):
            status = "PRESENT"
        systems.append({
            "id": system_id,
            "label": label,
            "mode": "INSPECT",
            "status": str(status)[:80],
            "schema": schema,
            "evidence": "persisted bounded runtime projection",
            "actionable": False,
        })
    return {
        "systems": systems,
        "rule": "ONLY_PERSISTED_RECOGNIZED_RUNTIME_PROJECTIONS",
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def journey_projection(service: Any) -> dict[str, Any]:
    try:
        lifecycle = dict(service.lifecycle() or {})
    except Exception:
        lifecycle = {}
    try:
        product = dict(service.product_status() or {})
    except Exception:
        product = {}
    state = str(lifecycle.get("state") or "UNKNOWN")
    stage = str(product.get("stage") or "UNKNOWN")
    if stage == "BLOCKED":
        action, label = "RETRY", "Riprova preparazione"
    elif stage not in {"READY", "UNKNOWN"}:
        action, label = "WAIT", "Preparazione in corso"
    elif state == "AWAITING_ACCEPTANCE":
        action, label = "ACCEPT", "Accetta le condizioni"
    elif state == "ACCEPTED":
        action, label = "PROBE", "Verifica ambiente"
    elif state == "PROBED":
        action, label = "INITIALIZE", "Avvia iKant"
    elif state == "ACTIVE":
        action, label = "CHAT", "Scrivi a iKant"
    else:
        action, label = "WAIT", "Controlla lo stato"
    milestones = [
        {"id": "connect", "label": "Connesso", "done": bool(product or lifecycle)},
        {"id": "accept", "label": "Condizioni", "done": state in {"ACCEPTED", "PROBED", "ACTIVE"}},
        {"id": "probe", "label": "Verifica", "done": state in {"PROBED", "ACTIVE"}},
        {"id": "active", "label": "Pronto", "done": state == "ACTIVE"},
    ]
    return {
        "state": state,
        "product_stage": stage,
        "next_action": action,
        "next_action_label": label,
        "milestones": milestones,
        "browser_decides_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def public_projection(service: Any) -> dict[str, Any]:
    foundation = foundation_projection(service)
    try:
        experience = runtime_projection(service.root)
    except Exception:
        experience = None
    return {
        "schema": PUBLIC_EXPERIENCE_SCHEMA,
        "release": PUBLIC_RELEASE,
        "journey": journey_projection(service),
        "conversation": conversation_projection(service.root),
        "capabilities": foundation.get("capabilities") or {},
        "runtime_systems": runtime_system_projection(service.root),
        "epistemic_value": foundation.get("epistemic_value") or {},
        "config": foundation.get("config") or {},
        "experience": experience,
        "promise": {
            "single_local_runtime": True,
            "visible_services_are_demonstrated": True,
            "visible_chat_is_integrity_checked": True,
            "runtime_system_cards_are_inspection_only": True,
            "epistemic_summary_does_not_certify_truth": True,
            "presentation_never_grants_authority": True,
        },
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
