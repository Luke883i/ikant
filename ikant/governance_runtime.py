from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Any

from .store import read_json
from .task_governance import GovernedTemporalTasks, TemporalTaskGovernanceError, TEMPORAL_TASK_PROJECTION_SCHEMA
from .temporal_autonomy import TemporalAutonomyError

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
        "presentation_is_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def task_governance_projection(state_dir: str | Path, *, session_id: str) -> dict[str, Any]:
    state = Path(state_dir)
    try:
        governed = GovernedTemporalTasks(state, session_id=session_id)
        core = governed.core.state()
        if core.tasks and not governed.events():
            return {"schema": TEMPORAL_TASK_PROJECTION_SCHEMA, "session_id": session_id, "integrity": "LEGACY_TASKS_BLOCKED", "task_count": len(core.tasks), "active_task_count": 0, "residency_mode": "IN_PROCESS_ONLY", "background_guaranteed": False, "same_cognitive_runtime_required": True, "time_is_not_authority": True, "epistemic_authority": 0.0, "execution_authority": 0.0}
        return governed.projection()
    except (TemporalTaskGovernanceError, TemporalAutonomyError, ValueError) as exc:
        return {"schema": TEMPORAL_TASK_PROJECTION_SCHEMA, "session_id": session_id, "integrity": "BLOCKED", "reason": type(exc).__name__, "task_count": 0, "active_task_count": 0, "residency_mode": "IN_PROCESS_ONLY", "background_guaranteed": False, "same_cognitive_runtime_required": True, "time_is_not_authority": True, "epistemic_authority": 0.0, "execution_authority": 0.0}


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
