from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .human_frame import ActorSessionBinding, validate_human_frame, validate_interaction_receipt
from .store import acquire_writer_lock, atomic_json_write, read_json

TEMPORAL_AUTONOMY_SCHEMA = "ikant-temporal-autonomy/v0.24-test"
TEMPORAL_EVENT_SCHEMA = "ikant-temporal-autonomy-event/v0.24-test"
TEMPORAL_TASK_SCHEMA = "ikant-temporal-task/v0.24-test"
TEMPORAL_WAKE_SCHEMA = "ikant-temporal-wake/v0.24-test"
TEMPORAL_PROJECTION_SCHEMA = "ikant-temporal-autonomy-projection/v0.24-test"

MAX_INTENT_BYTES = 16 * 1024
MIN_INTERVAL_MS = 60_000
MAX_INTERVAL_MS = 366 * 24 * 60 * 60 * 1000
MAX_FIRES = 1000
MAX_FUTURE_MS = 5 * 366 * 24 * 60 * 60 * 1000
MAX_RETRY_ATTEMPTS = 5
MAX_RETRY_BASE_MS = 60 * 60 * 1000
CLAIM_TTL_MS = 30_000
CLOCK_ROLLBACK_TOLERANCE_MS = 2_000


class TemporalAutonomyError(RuntimeError):
    pass


class TemporalAuthorityError(PermissionError):
    pass


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _now_ms(value: int | None = None) -> int:
    return int(time.time_ns() // 1_000_000 if value is None else value)


def _require_int(value: Any, name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(name)
    if minimum is not None and value < minimum:
        raise ValueError(name)
    if maximum is not None and value > maximum:
        raise ValueError(name)
    return value


def schedule_spec(
    *,
    session_id: str,
    intent_text: str,
    due_at_ms: int,
    interval_ms: int | None = None,
    max_fires: int = 1,
    retry_attempts: int = 3,
    retry_base_ms: int = 30_000,
    now_ms: int | None = None,
) -> dict[str, Any]:
    sid = str(session_id or "").strip()
    text = str(intent_text or "").strip()
    if not sid:
        raise ValueError("session_id")
    if not text or len(text.encode("utf-8")) > MAX_INTENT_BYTES:
        raise ValueError("intent_text")
    now = _now_ms(now_ms)
    due = _require_int(due_at_ms, "due_at_ms", minimum=0)
    if due > now + MAX_FUTURE_MS:
        raise ValueError("due_at_ms too far in future")
    fires = _require_int(max_fires, "max_fires", minimum=1, maximum=MAX_FIRES)
    if interval_ms is None:
        if fires != 1:
            raise ValueError("one-shot schedule requires max_fires=1")
        interval = None
    else:
        interval = _require_int(interval_ms, "interval_ms", minimum=MIN_INTERVAL_MS, maximum=MAX_INTERVAL_MS)
    attempts = _require_int(retry_attempts, "retry_attempts", minimum=1, maximum=MAX_RETRY_ATTEMPTS)
    base = _require_int(retry_base_ms, "retry_base_ms", minimum=1000, maximum=MAX_RETRY_BASE_MS)
    intent_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    spec = {
        "schema": TEMPORAL_TASK_SCHEMA,
        "session_id": sid,
        "intent_text": text,
        "intent_sha256": intent_sha,
        "due_at_ms": due,
        "interval_ms": interval,
        "max_fires": fires,
        "retry_policy": {"max_attempts": attempts, "base_ms": base, "exponential": True},
        "miss_policy": "COALESCE",
        "authority_effect": "NONE",
        "time_is_not_authority": True,
        "scheduled_work_is_control_only": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    spec["schedule_sha256"] = _digest(spec)
    return spec


def schedule_action_fingerprint(spec: dict[str, Any]) -> str:
    raw = dict(spec or {})
    sha = raw.get("schedule_sha256")
    copy = dict(raw)
    copy.pop("schedule_sha256", None)
    if not isinstance(sha, str) or sha != _digest(copy):
        raise ValueError("schedule digest")
    return "temporal:schedule:" + sha


def cancel_action_fingerprint(task_id: str) -> str:
    tid = str(task_id or "").strip()
    if not tid:
        raise ValueError("task_id")
    return "temporal:cancel:" + hashlib.sha256(tid.encode("utf-8")).hexdigest()


def validate_schedule_authorization(
    spec: dict[str, Any],
    frame: dict[str, Any],
    receipt: dict[str, Any],
    *,
    binding: ActorSessionBinding,
    secret: bytes,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    ok, frame_errors = validate_human_frame(frame)
    if not ok:
        errors.extend("frame:" + x for x in frame_errors)
    ok, receipt_errors = validate_interaction_receipt(frame, receipt, binding=binding, secret=secret)
    if not ok:
        errors.extend("receipt:" + x for x in receipt_errors)
    try:
        expected = schedule_action_fingerprint(spec)
    except ValueError:
        expected = ""
        errors.append("schedule digest")
    if frame.get("purpose") != "ACTION_CONFIRMATION" or receipt.get("decision") != "APPROVE":
        errors.append("explicit schedule approval")
    if frame.get("session_id") != spec.get("session_id") or frame.get("session_id") != binding.session_id:
        errors.append("schedule session")
    if frame.get("action_fingerprint") != expected:
        errors.append("schedule fingerprint")
    if frame.get("handoff_id") not in {None, ""}:
        errors.append("schedule may not bind execution handoff")
    entitlements = frame.get("requested_entitlements")
    if entitlements not in (None, (), []):
        errors.append("schedule may not carry entitlements")
    return not errors, list(dict.fromkeys(errors))


def validate_cancel_authorization(
    task_id: str,
    frame: dict[str, Any],
    receipt: dict[str, Any],
    *,
    session_id: str,
    binding: ActorSessionBinding,
    secret: bytes,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    ok, frame_errors = validate_human_frame(frame)
    if not ok:
        errors.extend("frame:" + x for x in frame_errors)
    ok, receipt_errors = validate_interaction_receipt(frame, receipt, binding=binding, secret=secret)
    if not ok:
        errors.extend("receipt:" + x for x in receipt_errors)
    if frame.get("purpose") != "ACTION_CONFIRMATION" or receipt.get("decision") != "APPROVE":
        errors.append("explicit cancellation approval")
    if frame.get("session_id") != session_id or binding.session_id != session_id:
        errors.append("cancel session")
    if frame.get("action_fingerprint") != cancel_action_fingerprint(task_id):
        errors.append("cancel fingerprint")
    if frame.get("handoff_id") not in {None, ""}:
        errors.append("cancel may not bind execution handoff")
    return not errors, list(dict.fromkeys(errors))


@dataclass(frozen=True)
class TemporalState:
    tasks: dict[str, dict[str, Any]]
    wakes: dict[str, dict[str, Any]]
    events: int
    journal_sha256: str
    last_wall_ms: int | None
    clock_blocked: bool
    clock_floor_ms: int | None


class TemporalAutonomyJournal:
    def __init__(self, path: str | Path, *, session_id: str):
        self.path = Path(path)
        self.session_id = str(session_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for lineno, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise TemporalAutonomyError(f"malformed temporal-autonomy journal line {lineno}") from exc
        return out

    def verify(self) -> dict[str, Any]:
        rows = self.rows()
        prev = "0" * 64
        last_wall: int | None = None
        for seq, row in enumerate(rows, 1):
            if row.get("schema") != TEMPORAL_EVENT_SCHEMA:
                raise TemporalAutonomyError("temporal event schema mismatch")
            if row.get("seq") != seq:
                raise TemporalAutonomyError("temporal event sequence non-contiguous")
            if row.get("session_id") != self.session_id:
                raise TemporalAutonomyError("temporal event session mismatch")
            if row.get("prev_sha256") != prev:
                raise TemporalAutonomyError("temporal event predecessor mismatch")
            wall = row.get("wall_ms")
            if isinstance(wall, bool) or not isinstance(wall, int) or wall < 0:
                raise TemporalAutonomyError("temporal event wall clock invalid")
            material = dict(row)
            actual = material.pop("sha256", None)
            if actual != _digest(material):
                raise TemporalAutonomyError("temporal event digest mismatch")
            prev = actual
            last_wall = wall
        return {"ok": True, "events": len(rows), "last_sha256": prev, "last_wall_ms": last_wall}

    def append(self, event_type: str, payload: dict[str, Any], *, wall_ms: int) -> dict[str, Any]:
        rows = self.rows()
        verified = self.verify()
        row = {
            "schema": TEMPORAL_EVENT_SCHEMA,
            "seq": len(rows) + 1,
            "session_id": self.session_id,
            "wall_ms": _require_int(wall_ms, "wall_ms", minimum=0),
            "event_type": str(event_type),
            "payload": dict(payload),
            "prev_sha256": verified["last_sha256"],
        }
        row["sha256"] = _digest(row)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return row


class TemporalAutonomyKernel:
    """Durable control-only scheduler.

    A due clock edge can create a wake envelope, never permission, approval, a capability
    grant, execution lease, host revalidation, material execution, or world evidence.
    """

    def __init__(self, state_dir: str | Path, *, session_id: str, durable: bool = True):
        self.state_dir = Path(state_dir)
        self.session_id = str(session_id)
        if not self.session_id:
            raise ValueError("session_id")
        self.durable = bool(durable)
        self.journal = TemporalAutonomyJournal(self.state_dir / "temporal-autonomy-events.jsonl", session_id=self.session_id)
        self.projection_path = self.state_dir / "temporal-autonomy.json"
        self.lock_path = self.state_dir / "temporal-autonomy.writer.lock"
        self.journal.verify()
        self._persist_projection()

    def _locked(self):
        return acquire_writer_lock(self.lock_path)

    def state(self) -> TemporalState:
        tasks: dict[str, dict[str, Any]] = {}
        wakes: dict[str, dict[str, Any]] = {}
        last = "0" * 64
        last_wall: int | None = None
        clock_blocked = False
        clock_floor: int | None = None
        rows = self.journal.rows()
        for row in rows:
            last = row["sha256"]
            last_wall = row["wall_ms"]
            typ = row["event_type"]
            p = dict(row.get("payload") or {})
            if typ == "TASK_SCHEDULED":
                tasks[p["task_id"]] = dict(p)
            elif typ == "TASK_CANCELLED":
                tid = p["task_id"]
                if tid not in tasks:
                    raise TemporalAutonomyError("cancel references missing task")
                tasks[tid] = {**tasks[tid], "status": "CANCELLED", "cancelled_at_ms": p["at_ms"]}
            elif typ == "WAKE_ISSUED":
                if p["task_id"] not in tasks:
                    raise TemporalAutonomyError("wake references missing task")
                wakes[p["wake_id"]] = dict(p)
            elif typ == "WAKE_CLAIMED":
                wid = p["wake_id"]
                if wid not in wakes:
                    raise TemporalAutonomyError("claim references missing wake")
                wakes[wid] = {**wakes[wid], "status": "CLAIMED", "attempt": p["attempt"], "worker_id": p["worker_id"], "claimed_at_ms": p["at_ms"], "claim_deadline_ms": p["claim_deadline_ms"]}
            elif typ == "WAKE_RETRY":
                wid = p["wake_id"]
                if wid not in wakes:
                    raise TemporalAutonomyError("retry references missing wake")
                wakes[wid] = {**wakes[wid], "status": "RETRY_PENDING", "attempt": p["attempt"], "not_before_ms": p["not_before_ms"], "worker_id": None, "claim_deadline_ms": None}
            elif typ in {"WAKE_DELIVERED", "WAKE_FAILED", "WAKE_CANCELLED"}:
                wid = p["wake_id"]
                if wid not in wakes:
                    raise TemporalAutonomyError("terminal wake references missing wake")
                status = "DELIVERED" if typ == "WAKE_DELIVERED" else ("FAILED" if typ == "WAKE_FAILED" else "CANCELLED")
                wakes[wid] = {**wakes[wid], "status": status, "terminal_at_ms": p["at_ms"], "terminal_reason": p.get("reason")}
                tid = wakes[wid]["task_id"]
                task = tasks[tid]
                if status == "DELIVERED":
                    fire_count = int(task.get("fire_count", 0)) + 1
                    interval = task.get("interval_ms")
                    max_fires = int(task["max_fires"])
                    if fire_count >= max_fires or interval is None:
                        tasks[tid] = {**task, "fire_count": fire_count, "status": "EXHAUSTED", "next_due_at_ms": None}
                    else:
                        next_due = int(wakes[wid]["next_due_at_ms"])
                        tasks[tid] = {**task, "fire_count": fire_count, "status": "ACTIVE", "next_due_at_ms": next_due}
                elif status == "FAILED":
                    tasks[tid] = {**task, "status": "PAUSED_FAILURE", "failed_wake_id": wid}
            elif typ == "CLOCK_BLOCKED":
                clock_blocked = True
                floor = p.get("last_wall_ms")
                if isinstance(floor, int):
                    clock_floor = max(clock_floor or 0, floor)
            elif typ == "CLOCK_RESUMED":
                clock_blocked = False
                clock_floor = None
            else:
                raise TemporalAutonomyError("unknown temporal-autonomy event type")
        return TemporalState(tasks, wakes, len(rows), last, last_wall, clock_blocked, clock_floor)

    def projection(self) -> dict[str, Any]:
        st = self.state()
        return {
            "schema": TEMPORAL_PROJECTION_SCHEMA,
            "session_id": self.session_id,
            "task_count": len(st.tasks),
            "active_task_count": sum(1 for t in st.tasks.values() if t.get("status") == "ACTIVE"),
            "pending_wake_count": sum(1 for w in st.wakes.values() if w.get("status") in {"PENDING", "RETRY_PENDING", "CLAIMED"}),
            "clock_blocked": st.clock_blocked,
            "journal_events": st.events,
            "journal_sha256": st.journal_sha256,
            "time_is_not_authority": True,
            "scheduled_work_is_control_only": True,
            "fresh_human_interaction_required_for_material_execution": True,
            "pre_wake_grant_reuse_allowed": False,
            "pre_wake_lease_reuse_allowed": False,
            "automatic_material_retry_allowed": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def _persist_projection(self) -> None:
        if self.durable:
            expected = self.projection()
            try:
                current = read_json(self.projection_path, {})
            except Exception:
                current = {}
            if current != expected:
                atomic_json_write(self.projection_path, expected)

    def _append_unlocked(self, typ: str, payload: dict[str, Any], *, wall_ms: int) -> dict[str, Any]:
        row = self.journal.append(typ, payload, wall_ms=wall_ms)
        self._persist_projection()
        return row

    def verify(self) -> dict[str, Any]:
        self.journal.verify()
        self.state()
        return {**self.projection(), "ok": True}

    def schedule(
        self,
        spec: dict[str, Any],
        frame: dict[str, Any],
        receipt: dict[str, Any],
        *,
        binding: ActorSessionBinding,
        secret: bytes,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        ok, errors = validate_schedule_authorization(spec, frame, receipt, binding=binding, secret=secret)
        if not ok:
            raise TemporalAuthorityError("invalid schedule authorization: " + "; ".join(errors))
        if spec.get("session_id") != self.session_id:
            raise TemporalAuthorityError("schedule kernel session mismatch")
        now = _now_ms(now_ms)
        rebuilt = schedule_spec(
            session_id=self.session_id,
            intent_text=spec["intent_text"],
            due_at_ms=spec["due_at_ms"],
            interval_ms=spec.get("interval_ms"),
            max_fires=spec["max_fires"],
            retry_attempts=spec["retry_policy"]["max_attempts"],
            retry_base_ms=spec["retry_policy"]["base_ms"],
            now_ms=now,
        )
        if rebuilt != spec:
            raise TemporalAuthorityError("schedule canonicalization drift")
        task_id = "tt-" + _digest({"schedule_sha256": spec["schedule_sha256"], "frame_sha256": frame["sha256"], "receipt_mac_sha256": receipt["mac_sha256"]})[:24]
        lock = self._locked()
        try:
            st = self.state()
            if task_id in st.tasks:
                return dict(st.tasks[task_id])
            task = {
                **spec,
                "task_id": task_id,
                "created_at_ms": now,
                "status": "ACTIVE",
                "fire_count": 0,
                "next_due_at_ms": int(spec["due_at_ms"]),
                "authorization_frame_sha256": frame["sha256"],
                "authorization_receipt_mac_sha256": receipt["mac_sha256"],
            }
            task["sha256"] = _digest(task)
            self._append_unlocked("TASK_SCHEDULED", task, wall_ms=now)
            return task
        finally:
            lock.release()

    def cancel(
        self,
        task_id: str,
        frame: dict[str, Any],
        receipt: dict[str, Any],
        *,
        binding: ActorSessionBinding,
        secret: bytes,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        tid = str(task_id)
        ok, errors = validate_cancel_authorization(tid, frame, receipt, session_id=self.session_id, binding=binding, secret=secret)
        if not ok:
            raise TemporalAuthorityError("invalid cancellation authorization: " + "; ".join(errors))
        now = _now_ms(now_ms)
        lock = self._locked()
        try:
            st = self.state()
            task = st.tasks.get(tid)
            if not task:
                raise TemporalAuthorityError("temporal task not found")
            if task.get("status") == "CANCELLED":
                return dict(task)
            if task.get("status") not in {"ACTIVE", "PAUSED_FAILURE"}:
                raise TemporalAuthorityError("terminal temporal task cannot be cancelled")
            for wake_id, wake in sorted(st.wakes.items()):
                if wake.get("task_id") == tid and wake.get("status") in {"PENDING", "RETRY_PENDING", "CLAIMED"}:
                    self._append_unlocked("WAKE_CANCELLED", {"wake_id": wake_id, "at_ms": now, "reason": "EXPLICIT_TASK_CANCELLATION"}, wall_ms=now)
            self._append_unlocked("TASK_CANCELLED", {"task_id": tid, "at_ms": now, "frame_sha256": frame["sha256"], "receipt_mac_sha256": receipt["mac_sha256"]}, wall_ms=now)
            return dict(self.state().tasks[tid])
        finally:
            lock.release()

    @staticmethod
    def _coalesced_next_due(task: dict[str, Any], now_ms: int) -> tuple[int | None, int]:
        due = int(task["next_due_at_ms"])
        interval = task.get("interval_ms")
        if interval is None:
            return None, 0
        interval = int(interval)
        if now_ms < due:
            return due, 0
        missed = max(0, (now_ms - due) // interval)
        return due + (missed + 1) * interval, int(missed)

    def _clock_guard_unlocked(self, st: TemporalState, now: int) -> bool:
        floor = st.clock_floor_ms if st.clock_blocked else st.last_wall_ms
        rolled_back = floor is not None and now + CLOCK_ROLLBACK_TOLERANCE_MS < floor
        if rolled_back:
            if not st.clock_blocked:
                self._append_unlocked("CLOCK_BLOCKED", {"observed_wall_ms": now, "last_wall_ms": floor, "reason": "WALL_CLOCK_ROLLBACK"}, wall_ms=now)
            return False
        if st.clock_blocked:
            self._append_unlocked("CLOCK_RESUMED", {"observed_wall_ms": now, "clock_floor_ms": st.clock_floor_ms, "reason": "WALL_CLOCK_CAUGHT_UP"}, wall_ms=now)
        return True

    def poll(self, *, now_ms: int | None = None) -> list[dict[str, Any]]:
        now = _now_ms(now_ms)
        lock = self._locked()
        try:
            st = self.state()
            if not self._clock_guard_unlocked(st, now):
                return []
            st = self.state()
            self._recover_stale_claims_unlocked(st, now)
            st = self.state()
            issued: list[dict[str, Any]] = []
            pending_by_task = {w["task_id"] for w in st.wakes.values() if w.get("status") in {"PENDING", "RETRY_PENDING", "CLAIMED"}}
            for task_id in sorted(st.tasks):
                task = st.tasks[task_id]
                if task.get("status") != "ACTIVE" or task_id in pending_by_task:
                    continue
                due = task.get("next_due_at_ms")
                if not isinstance(due, int) or now < due:
                    continue
                next_due, missed = self._coalesced_next_due(task, now)
                occurrence = int(task.get("fire_count", 0)) + 1
                wake_id = "tw-" + _digest({"task_id": task_id, "occurrence": occurrence, "scheduled_for_ms": due})[:24]
                wake = {
                    "schema": TEMPORAL_WAKE_SCHEMA,
                    "wake_id": wake_id,
                    "task_id": task_id,
                    "session_id": self.session_id,
                    "intent_text": task["intent_text"],
                    "intent_sha256": task["intent_sha256"],
                    "occurrence": occurrence,
                    "scheduled_for_ms": due,
                    "observed_due_at_ms": now,
                    "missed_intervals_coalesced": missed,
                    "next_due_at_ms": next_due,
                    "status": "PENDING",
                    "attempt": 0,
                    "not_before_ms": now,
                    "retry_policy": dict(task["retry_policy"]),
                    "freshness_barrier": {
                        "requires_new_human_interaction_before_material_execution": True,
                        "pre_wake_approval_reusable": False,
                        "pre_wake_grant_reusable": False,
                        "pre_wake_lease_reusable": False,
                        "fresh_host_revalidation_required": True,
                        "execution_eligible": False,
                        "material_execution_bridge": False,
                    },
                    "time_is_not_authority": True,
                    "wake_is_not_approval": True,
                    "wake_is_not_execution": True,
                    "epistemic_authority": 0.0,
                    "execution_authority": 0.0,
                }
                wake["sha256"] = _digest(wake)
                self._append_unlocked("WAKE_ISSUED", wake, wall_ms=now)
                issued.append(wake)
            return issued
        finally:
            lock.release()

    def claim_wake(self, wake_id: str, *, worker_id: str, now_ms: int | None = None) -> dict[str, Any]:
        wid = str(wake_id)
        worker = str(worker_id or "").strip()
        if not worker or len(worker) > 128:
            raise ValueError("worker_id")
        now = _now_ms(now_ms)
        lock = self._locked()
        try:
            st = self.state()
            if not self._clock_guard_unlocked(st, now):
                raise TemporalAutonomyError("clock rollback blocks wake claims")
            st = self.state()
            wake = st.wakes.get(wid)
            if not wake:
                raise TemporalAutonomyError("wake not found")
            task = st.tasks.get(str(wake.get("task_id") or ""))
            if not task or task.get("status") != "ACTIVE":
                raise TemporalAutonomyError("wake task is not active")
            if wake.get("status") not in {"PENDING", "RETRY_PENDING"}:
                raise TemporalAutonomyError("wake not claimable")
            if int(wake.get("not_before_ms", 0)) > now:
                raise TemporalAutonomyError("wake retry backoff not elapsed")
            attempt = int(wake.get("attempt", 0)) + 1
            max_attempts = int(wake["retry_policy"]["max_attempts"])
            if attempt > max_attempts:
                raise TemporalAutonomyError("wake retry budget exhausted")
            self._append_unlocked("WAKE_CLAIMED", {"wake_id": wid, "attempt": attempt, "worker_id": worker, "at_ms": now, "claim_deadline_ms": now + CLAIM_TTL_MS}, wall_ms=now)
            return dict(self.state().wakes[wid])
        finally:
            lock.release()

    def complete_wake(self, wake_id: str, *, worker_id: str, delivered: bool, reason: str = "", now_ms: int | None = None) -> dict[str, Any]:
        wid = str(wake_id)
        worker = str(worker_id or "").strip()
        now = _now_ms(now_ms)
        lock = self._locked()
        try:
            st = self.state()
            if not self._clock_guard_unlocked(st, now):
                raise TemporalAutonomyError("clock rollback blocks wake completion")
            st = self.state()
            wake = st.wakes.get(wid)
            if not wake or wake.get("status") != "CLAIMED":
                raise TemporalAutonomyError("wake is not claimed")
            if wake.get("worker_id") != worker:
                raise TemporalAutonomyError("wake worker mismatch")
            deadline = wake.get("claim_deadline_ms")
            if isinstance(deadline, int) and now >= deadline:
                self._retry_or_fail_unlocked(wake, now, reason="EXPIRED_CONTROL_CLAIM")
                raise TemporalAutonomyError("wake claim expired")
            if delivered:
                self._append_unlocked("WAKE_DELIVERED", {"wake_id": wid, "at_ms": now, "reason": str(reason or "CONTROL_DELIVERED")}, wall_ms=now)
            else:
                self._retry_or_fail_unlocked(wake, now, reason=str(reason or "CONTROL_DELIVERY_FAILED"))
            return dict(self.state().wakes[wid])
        finally:
            lock.release()

    def _retry_or_fail_unlocked(self, wake: dict[str, Any], now: int, *, reason: str) -> None:
        attempt = int(wake.get("attempt", 0))
        policy = wake["retry_policy"]
        max_attempts = int(policy["max_attempts"])
        if attempt >= max_attempts:
            self._append_unlocked("WAKE_FAILED", {"wake_id": wake["wake_id"], "at_ms": now, "reason": reason}, wall_ms=now)
            return
        base = int(policy["base_ms"])
        backoff = min(MAX_RETRY_BASE_MS, base * (2 ** max(0, attempt - 1)))
        self._append_unlocked("WAKE_RETRY", {"wake_id": wake["wake_id"], "attempt": attempt, "not_before_ms": now + backoff, "reason": reason}, wall_ms=now)

    def _recover_stale_claims_unlocked(self, st: TemporalState, now: int) -> None:
        for wake_id in sorted(st.wakes):
            wake = st.wakes[wake_id]
            if wake.get("status") == "CLAIMED" and isinstance(wake.get("claim_deadline_ms"), int) and now >= int(wake["claim_deadline_ms"]):
                self._retry_or_fail_unlocked(wake, now, reason="STALE_CONTROL_CLAIM")

    def pending_wakes(self) -> list[dict[str, Any]]:
        return [dict(w) for _, w in sorted(self.state().wakes.items()) if w.get("status") in {"PENDING", "RETRY_PENDING", "CLAIMED"}]


class TemporalAutonomyRunner:
    """Background poller that only advances the durable control plane.

    It never calls the model, web/native hosts, AgencyKernel, execution protocol, or dashboard egress.
    """

    def __init__(self, root: str | Path, *, poll_interval_seconds: float = 1.0, clock_ms: Callable[[], int] | None = None):
        self.root = Path(root).resolve()
        self.state_dir = self.root / ".ikant"
        self.poll_interval_seconds = max(0.05, float(poll_interval_seconds))
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._kernel: TemporalAutonomyKernel | None = None
        self._kernel_session: str | None = None

    def _active_session(self) -> str | None:
        state = read_json(self.state_dir / "runtime.json", {})
        if state.get("status") != "ACTIVE":
            return None
        sid = str(state.get("session_id") or "")
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
        if self._kernel is None or self._kernel_session != sid:
            self._kernel = TemporalAutonomyKernel(self.state_dir, session_id=sid)
            self._kernel_session = sid
        return self._kernel.poll(now_ms=int(self.clock_ms()))

    def _run(self) -> None:
        deadline = time.monotonic_ns()
        step = int(self.poll_interval_seconds * 1_000_000_000)
        while not self._stop.is_set():
            try:
                self.tick()
            except RuntimeError:
                pass
            deadline += step
            remaining = max(0.0, (deadline - time.monotonic_ns()) / 1_000_000_000)
            self._stop.wait(remaining)

    def start(self) -> "TemporalAutonomyRunner":
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ikant-temporal-autonomy", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=max(1.0, self.poll_interval_seconds * 2))


def temporal_dashboard_projection(state_dir: str | Path, *, session_id: str) -> dict[str, Any]:
    path = Path(state_dir) / "temporal-autonomy.json"
    raw = read_json(path, {})
    if not raw:
        return {
            "schema": TEMPORAL_PROJECTION_SCHEMA,
            "session_id": session_id,
            "task_count": 0,
            "active_task_count": 0,
            "pending_wake_count": 0,
            "clock_blocked": False,
            "time_is_not_authority": True,
            "execution_authority": 0.0,
        }
    if raw.get("schema") != TEMPORAL_PROJECTION_SCHEMA or raw.get("session_id") != session_id:
        return {"schema": TEMPORAL_PROJECTION_SCHEMA, "session_id": session_id, "integrity": "BLOCKED", "time_is_not_authority": True, "execution_authority": 0.0}
    return raw
