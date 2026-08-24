from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .human_frame import ActorSessionBinding, validate_human_frame, validate_interaction_receipt
from .store import append_jsonl, atomic_json_write, fsync_parent, read_json
from .temporal_autonomy import MAX_INTENT_BYTES, TemporalAutonomyError, TemporalAutonomyKernel, schedule_action_fingerprint, schedule_spec, validate_schedule_authorization

TEMPORAL_TASK_GOVERNANCE_SCHEMA = "ikant-temporal-task-governance/v1-test"
TEMPORAL_GOVERNED_SPEC_SCHEMA = "ikant-governed-temporal-spec/v1-test"
TEMPORAL_INTENT_CAPSULE_SCHEMA = "ikant-temporal-intent-capsule/v1-test"
TEMPORAL_TASK_GOVERNANCE_EVENT_SCHEMA = "ikant-temporal-task-governance-event/v1-test"
TEMPORAL_GOVERNED_WAKE_SCHEMA = "ikant-governed-temporal-wake/v1-test"
TEMPORAL_TASK_PROJECTION_SCHEMA = "ikant-temporal-task-projection/v1-test"
ZERO = "0" * 64
TOKEN_PREFIX = "capsule:v1:"


class TemporalTaskGovernanceError(RuntimeError):
    pass


class TemporalTaskGovernanceAuthorityError(PermissionError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text_sha(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _spec_copy(spec: dict[str, Any]) -> dict[str, Any]:
    raw = dict(spec or {})
    actual = raw.pop("sha256", None)
    if raw.get("schema") != TEMPORAL_GOVERNED_SPEC_SCHEMA or actual != _sha(raw):
        raise ValueError("governed temporal spec digest")
    return raw


def _deps(values: Iterable[object]) -> list[str]:
    out = sorted({str(x).strip() for x in values if str(x).strip()})
    if any(len(x) > 160 or any(ord(c) < 33 for c in x) for x in out):
        raise ValueError("memory_dependency_ids")
    return out


def governed_schedule_spec(*, session_id: str, intent_text: str, due_at_ms: int, interval_ms: int | None = None, max_fires: int = 1, retry_attempts: int = 3, retry_base_ms: int = 30_000, memory_dependency_ids: Iterable[object] = (), now_ms: int | None = None) -> dict[str, Any]:
    text = str(intent_text or "").strip()
    if not text or len(text.encode("utf-8")) > MAX_INTENT_BYTES:
        raise ValueError("intent_text")
    deps = _deps(memory_dependency_ids)
    binding = {
        "session_id": str(session_id),
        "intent_sha256": _text_sha(text),
        "due_at_ms": int(due_at_ms),
        "interval_ms": None if interval_ms is None else int(interval_ms),
        "max_fires": int(max_fires),
        "retry_attempts": int(retry_attempts),
        "retry_base_ms": int(retry_base_ms),
        "memory_dependency_ids": deps,
    }
    capsule_id = "ti-" + _sha(binding)[:24]
    token = TOKEN_PREFIX + capsule_id + ":" + binding["intent_sha256"]
    core = schedule_spec(
        session_id=str(session_id), intent_text=token, due_at_ms=due_at_ms,
        interval_ms=interval_ms, max_fires=max_fires, retry_attempts=retry_attempts,
        retry_base_ms=retry_base_ms, now_ms=now_ms,
    )
    raw = {
        "schema": TEMPORAL_GOVERNED_SPEC_SCHEMA,
        "session_id": str(session_id),
        "intent_text": text,
        "intent_sha256": binding["intent_sha256"],
        "capsule_id": capsule_id,
        "capsule_token": token,
        "memory_dependency_ids": deps,
        "core_spec": core,
        "raw_intent_in_core_journal": False,
        "capsule_is_single_persistent_plaintext_copy": True,
        "authority_effect": "NONE",
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    raw["sha256"] = _sha(raw)
    return raw


def governed_schedule_action_fingerprint(spec: dict[str, Any]) -> str:
    raw = _spec_copy(spec)
    core = raw.get("core_spec")
    if not isinstance(core, dict):
        raise ValueError("governed temporal core spec")
    return schedule_action_fingerprint(core)


def erase_intent_action_fingerprint(task_id: str) -> str:
    tid = str(task_id or "").strip()
    if not tid:
        raise ValueError("task_id")
    return "temporal:erase-intent:" + hashlib.sha256(tid.encode("utf-8")).hexdigest()


def _event_hash(row: dict[str, Any]) -> str:
    material = {k: row[k] for k in ("schema", "seq", "session_id", "event_type", "payload", "prev_sha256")}
    return _sha(material)


class GovernedTemporalTasks:
    """S20 wrapper over the S6 scheduler.

    The S6 journal remains the one temporal control scheduler. This layer binds a single
    erasable intent capsule, memory dependencies, epoch provenance and honest residency
    metadata without turning time, a wake or a future native/connector host into authority.
    """

    def __init__(self, state_dir: str | Path, *, session_id: str, durable: bool = True):
        self.state_dir = Path(state_dir)
        self.session_id = str(session_id)
        self.durable = bool(durable)
        self.core = TemporalAutonomyKernel(self.state_dir, session_id=self.session_id, durable=durable)
        self.capsule_dir = self.state_dir / "temporal-intents"
        self.journal_path = self.state_dir / "temporal-task-governance-events.jsonl"
        self._events_mem: list[dict[str, Any]] = []
        self.events()
        self._reconcile_erased_capsules()

    def events(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if self.durable and self.journal_path.exists():
            for lineno, line in enumerate(self.journal_path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise TemporalTaskGovernanceError(f"task governance malformed json line {lineno}") from exc
        rows.extend(self._events_mem)
        by: dict[int, dict[str, Any]] = {}
        for row in rows:
            seq = int(row.get("seq", 0))
            if seq < 1:
                raise TemporalTaskGovernanceError("task governance invalid sequence")
            if seq in by and by[seq] != row:
                raise TemporalTaskGovernanceError("task governance duplicate sequence divergence")
            by[seq] = row
        ordered = [by[k] for k in sorted(by)]
        prev = ZERO
        for seq, row in enumerate(ordered, 1):
            if row.get("schema") != TEMPORAL_TASK_GOVERNANCE_EVENT_SCHEMA or row.get("seq") != seq:
                raise TemporalTaskGovernanceError("task governance schema/sequence drift")
            if row.get("session_id") != self.session_id:
                raise TemporalTaskGovernanceError("task governance session drift")
            if row.get("event_type") not in {"TASK_BOUND", "TASK_BOUND_RECOVERED", "INTENT_ERASED"}:
                raise TemporalTaskGovernanceError("task governance event type")
            if row.get("prev_sha256") != prev or row.get("sha256") != _event_hash(row):
                raise TemporalTaskGovernanceError("task governance hash-chain drift")
            prev = row["sha256"]
        return ordered

    def _append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.events()
        row = {
            "schema": TEMPORAL_TASK_GOVERNANCE_EVENT_SCHEMA,
            "seq": len(rows) + 1,
            "session_id": self.session_id,
            "event_type": event_type,
            "payload": dict(payload),
            "prev_sha256": rows[-1]["sha256"] if rows else ZERO,
        }
        row["sha256"] = _event_hash(row)
        if self.durable:
            append_jsonl(self.journal_path, row)
        self._events_mem.append(row)
        self.events()
        return row

    def _epoch_receipt(self) -> dict[str, Any]:
        raw = read_json(self.state_dir / "runtime.json", {})
        epoch = raw.get("runtime_epoch") if isinstance(raw.get("runtime_epoch"), dict) else {}
        return {
            "epoch_id": str(epoch.get("epoch_id") or "") or None,
            "ordinal": epoch.get("ordinal") if isinstance(epoch.get("ordinal"), int) else None,
            "observed_only": True,
            "authority_effect": "NONE",
        }

    def _capsule_path(self, capsule_id: str) -> Path:
        return self.capsule_dir / (str(capsule_id) + ".json")

    def _capsule_material(self, spec: dict[str, Any], *, created_at_ms: int) -> dict[str, Any]:
        raw = _spec_copy(spec)
        return {
            "schema": TEMPORAL_INTENT_CAPSULE_SCHEMA,
            "capsule_id": raw["capsule_id"],
            "session_id": self.session_id,
            "intent_text": raw["intent_text"],
            "intent_sha256": raw["intent_sha256"],
            "memory_dependency_ids": list(raw["memory_dependency_ids"]),
            "core_schedule_sha256": raw["core_spec"]["schedule_sha256"],
            "created_at_ms": int(created_at_ms),
            "creation_epoch": self._epoch_receipt(),
            "retention_class": "USER_SCHEDULED_INTENT",
            "erase_scope": "TEMPORAL_INTENT_CAPSULE_ONLY",
            "journal_contains_plaintext_intent": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def _write_capsule(self, spec: dict[str, Any], *, created_at_ms: int) -> dict[str, Any]:
        material = self._capsule_material(spec, created_at_ms=created_at_ms)
        material["sha256"] = _sha(material)
        path = self._capsule_path(material["capsule_id"])
        if path.exists():
            current = json.loads(path.read_text(encoding="utf-8"))
            if current.get("schema") != TEMPORAL_INTENT_CAPSULE_SCHEMA:
                raise TemporalTaskGovernanceError("intent capsule schema drift")
            if current.get("intent_sha256") != material["intent_sha256"] or current.get("core_schedule_sha256") != material["core_schedule_sha256"] or current.get("memory_dependency_ids") != material["memory_dependency_ids"]:
                raise TemporalTaskGovernanceError("intent capsule binding drift")
            copy = dict(current); actual = copy.pop("sha256", None)
            if actual != _sha(copy):
                raise TemporalTaskGovernanceError("intent capsule digest mismatch")
            return current
        if self.durable:
            atomic_json_write(path, material)
        return material

    def _load_capsule(self, capsule_id: str, expected_sha: str | None = None) -> dict[str, Any]:
        path = self._capsule_path(capsule_id)
        if not path.is_file():
            raise TemporalTaskGovernanceError("intent capsule missing")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TemporalTaskGovernanceError("intent capsule unreadable") from exc
        if raw.get("schema") != TEMPORAL_INTENT_CAPSULE_SCHEMA or raw.get("session_id") != self.session_id:
            raise TemporalTaskGovernanceError("intent capsule schema/session drift")
        copy = dict(raw); actual = copy.pop("sha256", None)
        if actual != _sha(copy) or (expected_sha and actual != expected_sha):
            raise TemporalTaskGovernanceError("intent capsule digest mismatch")
        if _text_sha(str(raw.get("intent_text") or "")) != raw.get("intent_sha256"):
            raise TemporalTaskGovernanceError("intent capsule text digest mismatch")
        return raw

    @staticmethod
    def _parse_token(value: object) -> tuple[str, str]:
        text = str(value or "")
        if not text.startswith(TOKEN_PREFIX):
            raise TemporalTaskGovernanceError("ungoverned temporal intent token")
        parts = text.split(":", 3)
        if len(parts) != 4 or not parts[2] or len(parts[3]) != 64:
            raise TemporalTaskGovernanceError("temporal intent token malformed")
        return parts[2], parts[3]

    def _bindings(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for event in self.events():
            p = dict(event.get("payload") or {})
            tid = str(p.get("task_id") or "")
            if not tid:
                continue
            if event["event_type"] in {"TASK_BOUND", "TASK_BOUND_RECOVERED"}:
                out[tid] = {**out.get(tid, {}), **p, "intent_erased": False}
            elif event["event_type"] == "INTENT_ERASED":
                out[tid] = {**out.get(tid, {}), "intent_erased": True, "erasure_event_sha256": event["sha256"]}
        return out

    def _reconcile_erased_capsules(self) -> None:
        for binding in self._bindings().values():
            if not binding.get("intent_erased"):
                continue
            path = self._capsule_path(str(binding.get("capsule_id") or ""))
            if path.exists():
                path.unlink()
                fsync_parent(path)

    def _cleanup_orphan_capsules(self) -> list[str]:
        if not self.capsule_dir.exists():
            return []
        referenced = {str(x.get("capsule_id") or "") for x in self._bindings().values()}
        for task in self.core.state().tasks.values():
            try:
                capsule_id, _ = self._parse_token(task.get("intent_text"))
                referenced.add(capsule_id)
            except TemporalTaskGovernanceError:
                continue
        removed: list[str] = []
        for path in sorted(self.capsule_dir.glob("*.json")):
            if path.stem in referenced:
                continue
            path.unlink(); fsync_parent(path); removed.append(path.stem)
        return removed

    def reconcile(self) -> dict[str, Any]:
        self._reconcile_erased_capsules()
        bindings = self._bindings()
        recovered: list[str] = []
        for tid, task in sorted(self.core.state().tasks.items()):
            if tid in bindings:
                continue
            capsule_id, intent_sha = self._parse_token(task.get("intent_text"))
            capsule = self._load_capsule(capsule_id)
            if capsule.get("intent_sha256") != intent_sha or capsule.get("core_schedule_sha256") != task.get("schedule_sha256"):
                raise TemporalTaskGovernanceError("recoverable task/capsule binding drift")
            self._append("TASK_BOUND_RECOVERED", {
                "task_id": tid,
                "capsule_id": capsule_id,
                "capsule_sha256": capsule["sha256"],
                "memory_dependency_ids": list(capsule.get("memory_dependency_ids") or []),
                "creation_epoch": dict(capsule.get("creation_epoch") or {}),
                "residency_mode": "IN_PROCESS_ONLY",
                "recovered_after_restart": True,
            })
            recovered.append(tid)
        removed = self._cleanup_orphan_capsules()
        return {"schema": TEMPORAL_TASK_GOVERNANCE_SCHEMA, "ok": True, "recovered_task_ids": recovered, "removed_orphan_capsule_ids": removed, "authority_effect": "NONE"}

    def schedule(self, spec: dict[str, Any], frame: dict[str, Any], receipt: dict[str, Any], *, binding: ActorSessionBinding, secret: bytes, now_ms: int | None = None) -> dict[str, Any]:
        raw = _spec_copy(spec)
        if raw.get("session_id") != self.session_id:
            raise TemporalTaskGovernanceAuthorityError("governed schedule session mismatch")
        ok, errors = validate_schedule_authorization(raw["core_spec"], frame, receipt, binding=binding, secret=secret)
        if not ok:
            raise TemporalTaskGovernanceAuthorityError("invalid governed schedule authorization: " + "; ".join(errors))
        path = self._capsule_path(raw["capsule_id"]); existed = path.exists()
        created_at = int(time.time_ns() // 1_000_000 if now_ms is None else now_ms)
        capsule = self._write_capsule(spec, created_at_ms=created_at)
        try:
            task = self.core.schedule(raw["core_spec"], frame, receipt, binding=binding, secret=secret, now_ms=now_ms)
        except Exception:
            if not existed and path.exists(): path.unlink(); fsync_parent(path)
            raise
        bindings = self._bindings()
        if task["task_id"] not in bindings:
            self._append("TASK_BOUND", {
                "task_id": task["task_id"],
                "capsule_id": capsule["capsule_id"],
                "capsule_sha256": capsule["sha256"],
                "memory_dependency_ids": list(capsule["memory_dependency_ids"]),
                "creation_epoch": dict(capsule["creation_epoch"]),
                "residency_mode": "IN_PROCESS_ONLY",
                "future_connector_scope_revalidation_required": True,
                "future_transaction_approval_revalidation_required": True,
                "future_native_host_is_not_second_runtime": True,
            })
        self.reconcile()
        return self.task(task["task_id"])

    def _memory_status(self, deps: list[str]) -> tuple[bool, list[str]]:
        if not deps:
            return True, []
        path = self.state_dir / "temporal-memory.json"
        if not path.is_file():
            return False, list(deps)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False, list(deps)
        records = raw.get("records") if isinstance(raw.get("records"), dict) else {}
        summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
        calc = _sha({k: records[k] for k in sorted(records)})
        if summary.get("sha256") != calc:
            return False, list(deps)
        blocked = [nid for nid in deps if not isinstance(records.get(nid), dict) or records[nid].get("available") is not True]
        return not blocked, blocked

    def task(self, task_id: str) -> dict[str, Any]:
        tid = str(task_id)
        task = self.core.state().tasks.get(tid)
        if not task:
            raise TemporalTaskGovernanceError("task not found")
        binding = self._bindings().get(tid)
        if not binding:
            raise TemporalTaskGovernanceError("task governance binding missing")
        deps = list(binding.get("memory_dependency_ids") or [])
        memory_ok, blocked = self._memory_status(deps)
        intent_available = False
        if not binding.get("intent_erased"):
            try:
                self._load_capsule(str(binding.get("capsule_id") or ""), str(binding.get("capsule_sha256") or ""))
                intent_available = True
            except TemporalTaskGovernanceError:
                intent_available = False
        return {
            "task_id": tid,
            "status": task.get("status"),
            "next_due_at_ms": task.get("next_due_at_ms"),
            "fire_count": int(task.get("fire_count", 0)),
            "memory_dependency_ids": deps,
            "blocked_memory_dependency_ids": blocked,
            "memory_dependencies_current": memory_ok,
            "intent_available": intent_available,
            "intent_erased": bool(binding.get("intent_erased")),
            "creation_epoch": dict(binding.get("creation_epoch") or {}),
            "current_epoch": self._epoch_receipt(),
            "residency": {
                "mode": "IN_PROCESS_ONLY",
                "background_guaranteed": False,
                "requires_active_locked_runtime": True,
                "native_resident_host_attested": False,
                "second_cognitive_runtime_allowed": False,
            },
            "future_boundaries": {
                "connector_scope_revalidation_required": True,
                "transaction_approval_revalidation_required": True,
                "wake_may_not_reuse_pre_wake_authority": True,
            },
            "raw_intent_in_core_journal": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def projection(self) -> dict[str, Any]:
        self.reconcile()
        rows = [self.task(tid) for tid in sorted(self.core.state().tasks)]
        return {
            "schema": TEMPORAL_TASK_PROJECTION_SCHEMA,
            "session_id": self.session_id,
            "tasks": rows,
            "task_count": len(rows),
            "active_task_count": sum(1 for x in rows if x["status"] == "ACTIVE"),
            "residency_mode": "IN_PROCESS_ONLY",
            "background_guaranteed": False,
            "same_cognitive_runtime_required": True,
            "time_is_not_authority": True,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def task_impacts(self, node_ids: Iterable[object]) -> dict[str, Any]:
        targets = {str(x) for x in node_ids}
        projection = self.projection()
        dependent = [t["task_id"] for t in projection["tasks"] if targets & set(t["memory_dependency_ids"])]
        independent = [t["task_id"] for t in projection["tasks"] if t["status"] == "ACTIVE" and not (targets & set(t["memory_dependency_ids"]))]
        return {"dependent_task_ids": sorted(dependent), "independent_task_ids": sorted(independent)}

    def _govern_wake(self, wake: dict[str, Any]) -> dict[str, Any]:
        task_id = str(wake.get("task_id") or "")
        binding = self._bindings().get(task_id)
        if not binding:
            return {"schema": TEMPORAL_GOVERNED_WAKE_SCHEMA, "wake_id": wake.get("wake_id"), "task_id": task_id, "governance_status": "BLOCKED_UNBOUND", "claimable": False, "epistemic_authority": 0.0, "execution_authority": 0.0}
        deps = list(binding.get("memory_dependency_ids") or [])
        memory_ok, blocked = self._memory_status(deps)
        capsule = None
        capsule_error = None
        if binding.get("intent_erased"):
            capsule_error = "INTENT_ERASED"
        else:
            try:
                capsule = self._load_capsule(str(binding.get("capsule_id") or ""), str(binding.get("capsule_sha256") or ""))
            except TemporalTaskGovernanceError as exc:
                capsule_error = str(exc)
        ready = bool(capsule is not None and memory_ok)
        return {
            "schema": TEMPORAL_GOVERNED_WAKE_SCHEMA,
            "wake_id": wake.get("wake_id"),
            "task_id": task_id,
            "scheduled_for_ms": wake.get("scheduled_for_ms"),
            "occurrence": wake.get("occurrence"),
            "governance_status": "READY_CONTROL" if ready else "BLOCKED_GOVERNANCE",
            "claimable": ready,
            "intent_text": capsule.get("intent_text") if capsule else None,
            "intent_sha256": capsule.get("intent_sha256") if capsule else None,
            "blocked_memory_dependency_ids": blocked,
            "capsule_error": capsule_error,
            "creation_epoch": dict(binding.get("creation_epoch") or {}),
            "current_epoch": self._epoch_receipt(),
            "residency_mode": "IN_PROCESS_ONLY",
            "background_guaranteed": False,
            "future_connector_scope_revalidation_required": True,
            "future_transaction_approval_revalidation_required": True,
            "fresh_human_interaction_required_for_material_execution": True,
            "wake_is_not_approval": True,
            "wake_is_not_execution": True,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def poll(self, *, now_ms: int | None = None) -> list[dict[str, Any]]:
        self.reconcile()
        return [self._govern_wake(w) for w in self.core.poll(now_ms=now_ms)]

    def pending_wakes(self) -> list[dict[str, Any]]:
        self.reconcile()
        return [self._govern_wake(w) for w in self.core.pending_wakes()]

    def claim_wake(self, wake_id: str, *, worker_id: str, now_ms: int | None = None) -> dict[str, Any]:
        self.reconcile()
        raw = next((w for w in self.core.pending_wakes() if str(w.get("wake_id")) == str(wake_id)), None)
        if raw is None:
            raise TemporalAutonomyError("wake not found")
        governed = self._govern_wake(raw)
        if governed.get("claimable") is not True:
            raise TemporalTaskGovernanceError("wake blocked by S20 governance")
        return self.core.claim_wake(str(wake_id), worker_id=worker_id, now_ms=now_ms)

    def complete_wake(self, wake_id: str, *, worker_id: str, delivered: bool, reason: str = "", now_ms: int | None = None) -> dict[str, Any]:
        return self.core.complete_wake(str(wake_id), worker_id=worker_id, delivered=delivered, reason=reason, now_ms=now_ms)

    def cancel(self, task_id: str, frame: dict[str, Any], receipt: dict[str, Any], *, binding: ActorSessionBinding, secret: bytes, now_ms: int | None = None) -> dict[str, Any]:
        out = self.core.cancel(str(task_id), frame, receipt, binding=binding, secret=secret, now_ms=now_ms)
        return {"core": out, "projection": self.task(str(task_id))}

    def erase_intent(self, task_id: str, frame: dict[str, Any], receipt: dict[str, Any], *, binding: ActorSessionBinding, secret: bytes) -> dict[str, Any]:
        tid = str(task_id)
        task = self.core.state().tasks.get(tid)
        if not task:
            raise TemporalTaskGovernanceError("task not found")
        if task.get("status") not in {"CANCELLED", "EXHAUSTED", "PAUSED_FAILURE"}:
            raise TemporalTaskGovernanceAuthorityError("active temporal task must be cancelled or exhausted before intent erasure")
        errors: list[str] = []
        ok, fe = validate_human_frame(frame)
        if not ok: errors.extend("frame:" + x for x in fe)
        ok, re = validate_interaction_receipt(frame, receipt, binding=binding, secret=secret)
        if not ok: errors.extend("receipt:" + x for x in re)
        if frame.get("purpose") != "ACTION_CONFIRMATION" or receipt.get("decision") != "APPROVE": errors.append("explicit intent erasure approval")
        if frame.get("session_id") != self.session_id or binding.session_id != self.session_id: errors.append("intent erasure session")
        if frame.get("action_fingerprint") != erase_intent_action_fingerprint(tid): errors.append("intent erasure fingerprint")
        if frame.get("handoff_id") not in {None, ""}: errors.append("intent erasure may not bind handoff")
        if errors:
            raise TemporalTaskGovernanceAuthorityError("invalid intent erasure authorization: " + "; ".join(dict.fromkeys(errors)))
        current = self._bindings().get(tid)
        if not current:
            raise TemporalTaskGovernanceError("task governance binding missing")
        if not current.get("intent_erased"):
            self._append("INTENT_ERASED", {"task_id": tid, "capsule_id": current.get("capsule_id"), "capsule_sha256": current.get("capsule_sha256"), "receipt_mac_sha256": receipt.get("mac_sha256"), "history_rewrite": False})
        self._reconcile_erased_capsules()
        return {"schema": TEMPORAL_TASK_GOVERNANCE_SCHEMA, "task_id": tid, "intent_erased": True, "history_rewrite": False, "journal_preserved": True, "epistemic_authority": 0.0, "execution_authority": 0.0}
