from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import threading
from typing import Any

EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.9-test"
FRAME_SCHEMA = "ikant-dashboard-frame/v0.9-test"
EXIT_COMMAND = "EXIT IKANT"
RESUME_COMMAND = "RESUME IKANT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EgressState(str, Enum):
    LOCKED = "DASHBOARD_LOCKED"
    RELEASE_PENDING = "RELEASE_PENDING"
    RELEASED = "RELEASED"
    BREACHED = "EGRESS_BREACHED"


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
    """Fail-closed human-visible egress state for an ACTIVE iKant runtime."""

    def __init__(self, path: str | Path, *, runtime_session_id: str):
        self.path = Path(path)
        self.runtime_session_id = str(runtime_session_id)
        if not self.runtime_session_id:
            raise ValueError("runtime_session_id required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.record = self._load_or_create()

    def _load_or_create(self) -> EgressRecord:
        if not self.path.exists():
            rec = EgressRecord(schema=EGRESS_SCHEMA,runtime_session_id=self.runtime_session_id,state=EgressState.LOCKED.value,epoch=1,frame_seq=0,last_frame_sha256=None,last_cycle_id=None,last_kind=None,updated_at=_now())
            self._write(rec);return rec
        raw = json.loads(self.path.read_text(encoding="utf-8"));rec = EgressRecord(**raw)
        if rec.schema != EGRESS_SCHEMA:raise EgressViolation("egress schema mismatch")
        if rec.runtime_session_id != self.runtime_session_id:raise EgressViolation("egress runtime session mismatch")
        if rec.state not in {x.value for x in EgressState}:raise EgressViolation("egress state invalid")
        return rec

    def _write(self, rec: EgressRecord) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(rec), ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8");tmp.replace(self.path)

    @property
    def state(self) -> EgressState:return EgressState(self.record.state)

    def require_locked(self) -> None:
        if self.state != EgressState.LOCKED:raise EgressViolation(f"iKant dashboard egress not locked: {self.state.value}")

    def classify_user_text(self, text: str) -> str:
        if text == EXIT_COMMAND:return "EXIT"
        if text == RESUME_COMMAND:return "RESUME"
        return "INTENT"

    def attach_projection(self, dashboard: dict[str, Any], *, notice: str | None = None) -> dict[str, Any]:
        out = dict(dashboard);out["session_egress"]={"schema":EGRESS_SCHEMA,"state":self.record.state,"epoch":self.record.epoch,"frame_seq":self.record.frame_seq,"exclusive_human_output":self.state in {EgressState.LOCKED,EgressState.RELEASE_PENDING},"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"notice":notice};return out

    def seal_frame(self, frame_text: str, *, kind: str, cycle_id: str | None = None, release_after_frame: bool = False) -> FrameReceipt:
        with self._lock:
            self.require_locked();text=str(frame_text)
            if not text.strip():raise EgressViolation("dashboard frame must not be empty")
            seq=self.record.frame_seq+1;dg=_sha(text);next_state=EgressState.RELEASE_PENDING.value if release_after_frame else EgressState.LOCKED.value
            rec=replace(self.record,state=next_state,frame_seq=seq,last_frame_sha256=dg,last_cycle_id=cycle_id,last_kind=str(kind),updated_at=_now(),breach_reason=None);self._write(rec);self.record=rec
            return FrameReceipt(schema=FRAME_SCHEMA,runtime_session_id=self.runtime_session_id,epoch=rec.epoch,frame_seq=seq,kind=str(kind),cycle_id=cycle_id,frame_sha256=dg,release_after_frame=bool(release_after_frame))

    def acknowledge_visible(self, receipt: FrameReceipt, actual_visible_text: str) -> bool:
        with self._lock:
            actual=str(actual_visible_text);ok=receipt.runtime_session_id==self.runtime_session_id and receipt.epoch==self.record.epoch and receipt.frame_seq==self.record.frame_seq and receipt.frame_sha256==self.record.last_frame_sha256 and _sha(actual)==receipt.frame_sha256
            if not ok:
                rec=replace(self.record,state=EgressState.BREACHED.value,updated_at=_now(),breach_reason="human-visible output differed from sealed dashboard frame");self._write(rec);self.record=rec;return False
            if self.state==EgressState.RELEASE_PENDING and receipt.release_after_frame:
                rec=replace(self.record,state=EgressState.RELEASED.value,updated_at=_now());self._write(rec);self.record=rec
            return True

    def resume(self, *, runtime_integrity_ok: bool) -> None:
        with self._lock:
            if self.state not in {EgressState.RELEASED,EgressState.BREACHED}:raise EgressViolation("resume only valid after release or egress breach")
            if not runtime_integrity_ok:raise EgressViolation("runtime integrity required to resume iKant")
            rec=replace(self.record,state=EgressState.LOCKED.value,epoch=self.record.epoch+1,frame_seq=0,last_frame_sha256=None,last_cycle_id=None,last_kind=None,updated_at=_now(),breach_reason=None);self._write(rec);self.record=rec


def egress_path(runtime: Any) -> Path:return Path(runtime.state_dir) / "egress.json"
def activate_runtime_egress(runtime: Any) -> DashboardEgressGuard:
    runtime.require_active();return DashboardEgressGuard(egress_path(runtime),runtime_session_id=str(runtime.runtime.get("session_id") or ""))
def existing_runtime_egress(runtime: Any) -> DashboardEgressGuard | None:
    path=egress_path(runtime)
    if not path.exists():return None
    return DashboardEgressGuard(path,runtime_session_id=str(runtime.runtime.get("session_id") or ""))
