from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Any

from .store import read_json
from .task_governance import GovernedTemporalTasks, TEMPORAL_TASK_GOVERNANCE_EVENT_SCHEMA, TEMPORAL_TASK_PROJECTION_SCHEMA
from .temporal_autonomy import TEMPORAL_PROJECTION_SCHEMA

MEMORY_GOVERNANCE_PROJECTION_SCHEMA = "ikant-memory-governance-projection/v1-test"
ZERO = "0" * 64


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    import hashlib
    return hashlib.sha256(_canonical(value)).hexdigest()


def _memory_event_hash(row: dict[str, Any]) -> str:
    material = {k: row[k] for k in ("schema", "seq", "origin_session_id", "op", "payload", "prev_sha256")}
    return _sha(material)


def _task_event_hash(row: dict[str, Any]) -> str:
    material = {k: row[k] for k in ("schema", "seq", "session_id", "event_type", "payload", "prev_sha256")}
    return _sha(material)


def memory_governance_projection(state_dir: str | Path) -> dict[str, Any]:
    state = Path(state_dir)
    rows: list[dict[str, Any]] = []
    path = state / "memory-governance-events.jsonl"
    if path.exists():
        try:
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception:
            return {"schema": MEMORY_GOVERNANCE_PROJECTION_SCHEMA, "integrity": "BLOCKED", "reason": "governance_journal_unreadable", "epistemic_authority": 0.0, "execution_authority": 0.0}
    prev = ZERO
    try:
        for seq, row in enumerate(rows, 1):
            if row.get("schema") != "ikant-memory-governance-event/v1-test" or row.get("seq") != seq or row.get("op") != "FORGET_COMMITTED":
                raise ValueError("shape")
            if row.get("prev_sha256") != prev or row.get("sha256") != _memory_event_hash(row):
                raise ValueError("hash")
            prev = row["sha256"]
    except ValueError:
        return {"schema": MEMORY_GOVERNANCE_PROJECTION_SCHEMA, "integrity": "BLOCKED", "reason": "governance_journal_integrity", "epistemic_authority": 0.0, "execution_authority": 0.0}
    memory = {}
    try:
        memory = json.loads((state / "temporal-memory.json").read_text(encoding="utf-8")) if (state / "temporal-memory.json").is_file() else {}
    except Exception:
        return {"schema": MEMORY_GOVERNANCE_PROJECTION_SCHEMA, "integrity": "BLOCKED", "reason": "temporal_memory_unreadable", "epistemic_authority": 0.0, "execution_authority": 0.0}
    records = memory.get("records") if isinstance(memory.get("records"), dict) else {}
    summary = memory.get("summary") if isinstance(memory.get("summary"), dict) else {}
    if records:
        digest = _sha({k: records[k] for k in sorted(records)})
        if summary.get("sha256") != digest:
            return {"schema": MEMORY_GOVERNANCE_PROJECTION_SCHEMA, "integrity": "BLOCKED", "reason": "temporal_memory_digest", "epistemic_authority": 0.0, "execution_authority": 0.0}
    return {
        "schema": MEMORY_GOVERNANCE_PROJECTION_SCHEMA,
        "integrity": "VERIFIED",
        "forget_event_count": len(rows),
        "forgotten_count": sum(1 for row in records.values() if row.get("state") == "FORGOTTEN"),
        "dependency_invalidated_count": sum(1 for row in records.values() if row.get("state") == "DEPENDENCY_INVALIDATED"),
        "available_count": int(summary.get("available_count") or 0),
        "journal_tail_sha256": prev,
        "history_rewrite": False,
        "read_only_projection": True,
        "presentation_is_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _task_governance_rows(state: Path, session_id: str) -> tuple[list[dict[str, Any]], str | None]:
    path = state / "temporal-task-governance-events.jsonl"
    if not path.exists():
        return [], None
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return [], "governance_journal_unreadable"
    prev = ZERO
    allowed={"TASK_BOUND","TASK_BOUND_RECOVERED","INTENT_ERASED"}
    for seq,row in enumerate(rows,1):
        if row.get("schema") != TEMPORAL_TASK_GOVERNANCE_EVENT_SCHEMA or row.get("seq") != seq or row.get("session_id") != session_id or row.get("event_type") not in allowed:
            return [], "governance_journal_shape"
        if row.get("prev_sha256") != prev or row.get("sha256") != _task_event_hash(row):
            return [], "governance_journal_integrity"
        prev=row["sha256"]
    return rows,None


def task_governance_projection(state_dir: str | Path, *, session_id: str) -> dict[str, Any]:
    """Read-only S20 projection. Never instantiates the scheduler or writes state."""
    state=Path(state_dir);sid=str(session_id or "")
    rows,error=_task_governance_rows(state,sid)
    if error:
        return {"schema":TEMPORAL_TASK_PROJECTION_SCHEMA,"session_id":sid,"integrity":"BLOCKED","reason":error,"task_count":0,"active_task_count":0,"residency_mode":"IN_PROCESS_ONLY","background_guaranteed":False,"same_cognitive_runtime_required":True,"time_is_not_authority":True,"read_only_projection":True,"epistemic_authority":0.0,"execution_authority":0.0}
    core=read_json(state/"temporal-autonomy.json",{})
    if not core:
        return {"schema":TEMPORAL_TASK_PROJECTION_SCHEMA,"session_id":sid,"integrity":"VERIFIED","task_count":0,"active_task_count":0,"pending_wake_count":0,"governance_event_count":len(rows),"governed_task_count":0,"intent_erased_count":0,"residency_mode":"IN_PROCESS_ONLY","background_guaranteed":False,"same_cognitive_runtime_required":True,"time_is_not_authority":True,"read_only_projection":True,"epistemic_authority":0.0,"execution_authority":0.0}
    if core.get("schema") != TEMPORAL_PROJECTION_SCHEMA or core.get("session_id") != sid:
        return {"schema":TEMPORAL_TASK_PROJECTION_SCHEMA,"session_id":sid,"integrity":"BLOCKED","reason":"core_projection_schema_session","task_count":0,"active_task_count":0,"residency_mode":"IN_PROCESS_ONLY","background_guaranteed":False,"same_cognitive_runtime_required":True,"time_is_not_authority":True,"read_only_projection":True,"epistemic_authority":0.0,"execution_authority":0.0}
    bound={};erased=set()
    for row in rows:
        payload=row.get("payload") or {};tid=str(payload.get("task_id") or "")
        if not tid:continue
        if row["event_type"] in {"TASK_BOUND","TASK_BOUND_RECOVERED"}:bound[tid]=str(payload.get("capsule_id") or "")
        elif row["event_type"]=="INTENT_ERASED":erased.add(tid)
    task_count=int(core.get("task_count") or 0)
    integrity="LEGACY_TASKS_BLOCKED" if task_count>0 and not bound else "VERIFIED"
    return {"schema":TEMPORAL_TASK_PROJECTION_SCHEMA,"session_id":sid,"integrity":integrity,"task_count":task_count,"active_task_count":int(core.get("active_task_count") or 0) if integrity=="VERIFIED" else 0,"pending_wake_count":int(core.get("pending_wake_count") or 0) if integrity=="VERIFIED" else 0,"clock_blocked":bool(core.get("clock_blocked")),"governance_event_count":len(rows),"governed_task_count":len(bound),"intent_erased_count":len(erased),"residency_mode":"IN_PROCESS_ONLY","background_guaranteed":False,"same_cognitive_runtime_required":True,"time_is_not_authority":True,"read_only_projection":True,"presentation_is_authority":False,"epistemic_authority":0.0,"execution_authority":0.0}


class GovernedTemporalTaskRunner:
    """Canonical local poller after S20; advances only governed S6 tasks."""

    def __init__(self, root: str | Path, *, poll_interval_seconds: float = 1.0, clock_ms=None):
        self.root = Path(root).resolve()
        self.state_dir = self.root / ".ikant"
        self.poll_interval_seconds = max(0.05, float(poll_interval_seconds))
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tasks: GovernedTemporalTasks | None = None
        self._session: str | None = None

    def _active_session(self) -> str | None:
        runtime = read_json(self.state_dir / "runtime.json", {})
        if runtime.get("status") != "ACTIVE":
            return None
        sid = str(runtime.get("session_id") or "")
        if not sid:
            return None
        egress = read_json(self.state_dir / "egress.json", {})
        if egress.get("runtime_session_id") != sid or egress.get("state") != "DASHBOARD_LOCKED":
            return None
        return sid

    def tick(self) -> list[dict[str, Any]]:
        sid = self._active_session()
        if sid is None:
            return []
        if self._tasks is None or self._session != sid:
            self._tasks = GovernedTemporalTasks(self.state_dir, session_id=sid)
            self._session = sid
        return self._tasks.poll(now_ms=int(self.clock_ms()))

    def _run(self) -> None:
        deadline = time.monotonic_ns()
        step = int(self.poll_interval_seconds * 1_000_000_000)
        while not self._stop.is_set():
            try:
                self.tick()
            except RuntimeError:
                pass
            deadline += step
            self._stop.wait(max(0.0, (deadline - time.monotonic_ns()) / 1_000_000_000))

    def start(self) -> "GovernedTemporalTaskRunner":
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ikant-governed-temporal-tasks", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=max(1.0, self.poll_interval_seconds * 2))
