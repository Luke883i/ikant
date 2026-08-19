from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import threading
from typing import Any
from .store import atomic_json_write, append_jsonl
EGRESS_SCHEMA = 'ikant-dashboard-session-egress/v0.10-test'
LEGACY_EGRESS_SCHEMA = 'ikant-dashboard-session-egress/v0.9-test'
FRAME_SCHEMA = 'ikant-dashboard-frame/v0.10-test'
JOURNAL_SCHEMA = 'ikant-dashboard-egress-journal/v0.10-test'
EXIT_COMMAND = 'EXIT IKANT'
RESUME_COMMAND = 'RESUME IKANT'
MAX_FRAME_BYTES = 128 * 1024
_BIDI = {chr(x) for x in list(range(8234, 8239)) + list(range(8294, 8298))}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

class EgressState(str, Enum):
    LOCKED = 'DASHBOARD_LOCKED'
    FRAME_PENDING = 'FRAME_PENDING'
    RELEASE_PENDING = 'RELEASE_PENDING'
    RELEASED = 'RELEASED'
    BREACHED = 'EGRESS_BREACHED'

@dataclass(frozen=True)
class EgressRecord:
    schema: str
    runtime_session_id: str
    state: str
    epoch: int
    frame_seq: int
    last_frame_sha256: str | None
    last_cycle_id: str | None
    last_kind: str | None
    updated_at: str
    breach_reason: str | None = None
    journal_seq: int = 0
    last_journal_sha256: str = '0' * 64
    pending_frame_path: str | None = None

@dataclass(frozen=True)
class FrameReceipt:
    schema: str
    runtime_session_id: str
    epoch: int
    frame_seq: int
    kind: str
    cycle_id: str | None
    frame_sha256: str
    release_after_frame: bool

class EgressViolation(RuntimeError):
    pass

class DashboardEgressGuard:
    """Crash-recoverable, fail-closed human-visible egress state for ACTIVE iKant."""

    def __init__(self, path: str | Path, *, runtime_session_id: str):
        self.path = Path(path)
        self.runtime_session_id = str(runtime_session_id)
        if not self.runtime_session_id:
            raise ValueError('runtime_session_id required')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.journal_path = self.path.with_name('egress-events.jsonl')
        self.frames_dir = self.path.with_name('egress-frames')
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.record = self._load_or_create()
        self.verify()

    def _new(self) -> EgressRecord:
        return EgressRecord(schema=EGRESS_SCHEMA, runtime_session_id=self.runtime_session_id, state=EgressState.LOCKED.value, epoch=1, frame_seq=0, last_frame_sha256=None, last_cycle_id=None, last_kind=None, updated_at=_now())

    def _write(self, rec: EgressRecord) -> None:
        atomic_json_write(self.path, asdict(rec))

    def _journal(self, rec: EgressRecord, event: str, payload: dict[str, Any] | None=None) -> EgressRecord:
        seq = rec.journal_seq + 1
        body = {'schema': JOURNAL_SCHEMA, 'seq': seq, 'at': _now(), 'runtime_session_id': self.runtime_session_id, 'event': str(event), 'state': rec.state, 'epoch': rec.epoch, 'frame_seq': rec.frame_seq, 'payload': dict(payload or {}), 'prev_sha256': rec.last_journal_sha256}
        body['sha256'] = _sha_payload(body)
        append_jsonl(self.journal_path, body)
        return replace(rec, journal_seq=seq, last_journal_sha256=body['sha256'], updated_at=body['at'])

    def _migrate_legacy(self, raw: dict[str, Any]) -> EgressRecord:
        state = str(raw.get('state') or '')
        unsafe = state in {EgressState.FRAME_PENDING.value, EgressState.RELEASE_PENDING.value}
        rec = EgressRecord(schema=EGRESS_SCHEMA, runtime_session_id=self.runtime_session_id, state=EgressState.BREACHED.value if unsafe else state, epoch=max(1, int(raw.get('epoch', 1))), frame_seq=max(0, int(raw.get('frame_seq', 0))), last_frame_sha256=raw.get('last_frame_sha256'), last_cycle_id=raw.get('last_cycle_id'), last_kind=raw.get('last_kind'), updated_at=_now(), breach_reason='legacy pending frame is not crash-recoverable' if unsafe else raw.get('breach_reason'))
        if rec.state not in {x.value for x in EgressState}:
            raise EgressViolation('legacy egress state invalid')
        rec = self._journal(rec, 'MIGRATE_V09', {'legacy_state': state, 'unsafe_pending': unsafe})
        self._write(rec)
        return rec

    def _load_or_create(self) -> EgressRecord:
        if not self.path.exists():
            rec = self._new()
            rec = self._journal(rec, 'CREATE')
            self._write(rec)
            return rec
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise EgressViolation('egress state unreadable') from exc
        if raw.get('schema') == LEGACY_EGRESS_SCHEMA:
            return self._migrate_legacy(raw)
        try:
            rec = EgressRecord(**raw)
        except (TypeError, ValueError) as exc:
            raise EgressViolation('egress state shape invalid') from exc
        if rec.schema != EGRESS_SCHEMA:
            raise EgressViolation('egress schema mismatch')
        if rec.runtime_session_id != self.runtime_session_id:
            raise EgressViolation('egress runtime session mismatch')
        if rec.state not in {x.value for x in EgressState}:
            raise EgressViolation('egress state invalid')
        return rec

    @property
    def state(self) -> EgressState:
        return EgressState(self.record.state)

    def require_locked(self) -> None:
        if self.state != EgressState.LOCKED:
            raise EgressViolation(f'iKant dashboard egress not locked: {self.state.value}')

    def classify_user_text(self, text: str) -> str:
        if text == EXIT_COMMAND:
            return 'EXIT'
        if text == RESUME_COMMAND:
            return 'RESUME'
        return 'INTENT'

    def _validate_frame_text(self, text: str) -> None:
        if not text.strip():
            raise EgressViolation('dashboard frame must not be empty')
        data = text.encode('utf-8')
        if len(data) > MAX_FRAME_BYTES:
            raise EgressViolation('dashboard frame exceeds 128 KiB bound')
        if '\r' in text or '\x1b' in text or '\x00' in text:
            raise EgressViolation('dashboard frame contains forbidden control bytes')
        if any((ch in _BIDI for ch in text)):
            raise EgressViolation('dashboard frame contains bidi control characters')

    def _pending_path(self, epoch: int, seq: int) -> Path:
        return self.frames_dir / f'epoch-{epoch:04d}-frame-{seq:08d}.txt'

    def _persist_pending_frame(self, path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + '.tmp')
        with tmp.open('w', encoding='utf-8', newline='\n') as h:
            h.write(text)
            h.flush()
            import os
            os.fsync(h.fileno())
        tmp.replace(path)

    def seal_frame(self, frame_text: str, *, kind: str, cycle_id: str | None=None, release_after_frame: bool=False) -> FrameReceipt:
        with self._lock:
            self.require_locked()
            text = str(frame_text)
            self._validate_frame_text(text)
            seq = self.record.frame_seq + 1
            dg = _sha_text(text)
            p = self._pending_path(self.record.epoch, seq)
            self._persist_pending_frame(p, text)
            next_state = EgressState.RELEASE_PENDING.value if release_after_frame else EgressState.FRAME_PENDING.value
            rec = replace(self.record, state=next_state, frame_seq=seq, last_frame_sha256=dg, last_cycle_id=cycle_id, last_kind=str(kind), breach_reason=None, pending_frame_path=str(p))
            rec = self._journal(rec, 'SEAL_FRAME', {'kind': str(kind), 'cycle_id': cycle_id, 'frame_sha256': dg, 'release': bool(release_after_frame)})
            self._write(rec)
            self.record = rec
            return FrameReceipt(schema=FRAME_SCHEMA, runtime_session_id=self.runtime_session_id, epoch=rec.epoch, frame_seq=seq, kind=str(kind), cycle_id=cycle_id, frame_sha256=dg, release_after_frame=bool(release_after_frame))

    def pending_frame(self) -> tuple[FrameReceipt, str] | None:
        with self._lock:
            if self.state not in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
                return None
            if not self.record.pending_frame_path:
                self._breach('pending frame path missing')
                raise EgressViolation('pending frame path missing')
            path = Path(self.record.pending_frame_path)
            try:
                text = path.read_text(encoding='utf-8')
            except OSError as exc:
                self._breach('pending frame artifact unreadable')
                raise EgressViolation('pending frame artifact unreadable') from exc
            if _sha_text(text) != self.record.last_frame_sha256:
                self._breach('pending frame artifact digest mismatch')
                raise EgressViolation('pending frame artifact digest mismatch')
            receipt = FrameReceipt(schema=FRAME_SCHEMA, runtime_session_id=self.runtime_session_id, epoch=self.record.epoch, frame_seq=self.record.frame_seq, kind=str(self.record.last_kind or 'RECOVERY'), cycle_id=self.record.last_cycle_id, frame_sha256=str(self.record.last_frame_sha256), release_after_frame=self.state == EgressState.RELEASE_PENDING)
            return (receipt, text)

    def _breach(self, reason: str) -> None:
        rec = replace(self.record, state=EgressState.BREACHED.value, breach_reason=str(reason), pending_frame_path=None)
        rec = self._journal(rec, 'BREACH', {'reason': str(reason)})
        self._write(rec)
        self.record = rec

    def acknowledge_visible(self, receipt: FrameReceipt, actual_visible_text: str) -> bool:
        with self._lock:
            if self.state not in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
                self._breach('acknowledgement without pending frame')
                return False
            actual = str(actual_visible_text)
            ok = receipt.schema == FRAME_SCHEMA and receipt.runtime_session_id == self.runtime_session_id and (receipt.epoch == self.record.epoch) and (receipt.frame_seq == self.record.frame_seq) and (receipt.frame_sha256 == self.record.last_frame_sha256) and (_sha_text(actual) == receipt.frame_sha256) and (bool(receipt.release_after_frame) == (self.state == EgressState.RELEASE_PENDING))
            if not ok:
                self._breach('human-visible output differed from sealed dashboard frame')
                return False
            path = Path(self.record.pending_frame_path) if self.record.pending_frame_path else None
            if self.state == EgressState.RELEASE_PENDING:
                rec = replace(self.record, state=EgressState.RELEASED.value, pending_frame_path=None)
                event = 'ACK_RELEASE'
            else:
                rec = replace(self.record, state=EgressState.LOCKED.value, pending_frame_path=None)
                event = 'ACK_FRAME'
            rec = self._journal(rec, event, {'frame_sha256': receipt.frame_sha256})
            self._write(rec)
            self.record = rec
            if path:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            return True

    def resume(self, *, runtime_integrity_ok: bool) -> None:
        with self._lock:
            if self.state not in {EgressState.RELEASED, EgressState.BREACHED}:
                raise EgressViolation('resume only valid after release or egress breach')
            if not runtime_integrity_ok:
                raise EgressViolation('runtime integrity required to resume iKant')
            rec = replace(self.record, state=EgressState.LOCKED.value, epoch=self.record.epoch + 1, frame_seq=0, last_frame_sha256=None, last_cycle_id=None, last_kind=None, breach_reason=None, pending_frame_path=None)
            rec = self._journal(rec, 'RESUME', {'runtime_integrity_ok': True})
            self._write(rec)
            self.record = rec

    def verify(self) -> dict[str, Any]:
        rows = []
        if self.journal_path.exists():
            for n, line in enumerate(self.journal_path.read_text(encoding='utf-8').splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EgressViolation(f'egress journal malformed at line {n}') from exc
                rows.append(row)
        prev = '0' * 64
        for seq, row in enumerate(rows, 1):
            if row.get('schema') != JOURNAL_SCHEMA or row.get('seq') != seq:
                raise EgressViolation('egress journal sequence/schema mismatch')
            if row.get('runtime_session_id') != self.runtime_session_id:
                raise EgressViolation('egress journal session mismatch')
            if row.get('prev_sha256') != prev:
                raise EgressViolation('egress journal predecessor mismatch')
            supplied = row.get('sha256')
            material = dict(row)
            material.pop('sha256', None)
            if supplied != _sha_payload(material):
                raise EgressViolation('egress journal digest mismatch')
            prev = supplied
        if self.record.journal_seq != len(rows) or self.record.last_journal_sha256 != prev:
            raise EgressViolation('egress state/journal divergence')
        if self.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
            self.pending_frame()
        elif self.record.pending_frame_path is not None:
            raise EgressViolation('non-pending state references pending artifact')
        return {'schema': 'ikant-dashboard-egress-integrity/v0.10-test', 'ok': True, 'state': self.record.state, 'epoch': self.record.epoch, 'frame_seq': self.record.frame_seq, 'journal_seq': self.record.journal_seq, 'pending_recoverable': self.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}}

    def attach_projection(self, dashboard: dict[str, Any], *, notice: str | None=None) -> dict[str, Any]:
        out = dict(dashboard)
        out['session_egress'] = {'schema': EGRESS_SCHEMA, 'state': self.record.state, 'epoch': self.record.epoch, 'frame_seq': self.record.frame_seq, 'journal_seq': self.record.journal_seq, 'exclusive_human_output': self.state in {EgressState.LOCKED, EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}, 'recovery_required': self.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}, 'exit_command': EXIT_COMMAND, 'resume_command': RESUME_COMMAND, 'notice': notice}
        return out

def egress_path(runtime: Any) -> Path:
    return Path(runtime.state_dir) / 'egress.json'

def activate_runtime_egress(runtime: Any) -> DashboardEgressGuard:
    runtime.require_active()
    return DashboardEgressGuard(egress_path(runtime), runtime_session_id=str(runtime.runtime.get('session_id') or ''))

def existing_runtime_egress(runtime: Any) -> DashboardEgressGuard | None:
    path = egress_path(runtime)
    if not path.exists():
        return None
    return DashboardEgressGuard(path, runtime_session_id=str(runtime.runtime.get('session_id') or ''))
