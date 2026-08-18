from __future__ import annotations

import hashlib
import json
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CHAT_SCHEMA = "ikant-chat-record/v0.4-test"
CHAT_INDEX_SCHEMA = "ikant-chat-index/v0.4-test"
_ALLOWED_ROLES = {"user", "ikant"}
_ANSI_RE = re.compile(r"\x1b(?:[@-_][0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNICODE_SPOOF_RE = re.compile("[\u200b\u200c\u200d\u2060\u202a-\u202e\u2066-\u2069]")
_PROMPT_SPOOF_RE = re.compile(r"^\s*>\s*(?:ikant|user)\s*:", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def sanitize_terminal_text(text: str) -> str:
    """Remove terminal/control spoofing sequences for rendering only."""
    text = _ANSI_RE.sub("", str(text))
    text = _CONTROL_RE.sub("", text)
    return _UNICODE_SPOOF_RE.sub("", text)


def sanitize_shell_content(text: str) -> str:
    clean = sanitize_terminal_text(text)
    lines=[]
    for line in clean.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _PROMPT_SPOOF_RE.match(line):
            line = "[prompt-like text] " + line.lstrip()
        lines.append(line)
    return "\n".join(lines)


class ChatIntegrityError(RuntimeError):
    pass


class ChatLog:
    """Append-only visible chat transcript. Stores no hidden reasoning or evidence claims."""

    def __init__(self, path: str | Path, *, runtime_session_id: str):
        self.path = Path(path)
        self.runtime_session_id = str(runtime_session_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._indexed = False
        self._last_seq = 0
        self._last_sha256 = "0" * 64
        self._roles_by_seq: dict[int, str] = {}
        self._replied_user_seqs: set[int] = set()

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for lineno, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ChatIntegrityError(f"malformed chat json at line {lineno}") from exc
            rows.append(row)
        return rows

    def verify(self) -> dict[str, Any]:
        rows = self.rows()
        prev = "0" * 64
        roles: dict[int, str] = {}
        replied: set[int] = set()
        for expected_seq, row in enumerate(rows, 1):
            if row.get("schema") != CHAT_SCHEMA:
                raise ChatIntegrityError("chat schema mismatch")
            if row.get("seq") != expected_seq:
                raise ChatIntegrityError("chat sequence non-contiguous")
            if row.get("runtime_session_id") != self.runtime_session_id:
                raise ChatIntegrityError("chat runtime session binding mismatch")
            if row.get("role") not in _ALLOWED_ROLES:
                raise ChatIntegrityError("chat role invalid")
            roles[expected_seq] = row["role"]
            if row["role"] == "ikant":
                target = row.get("reply_to_seq")
                if not isinstance(target, int) or target < 1 or target >= expected_seq or roles.get(target) != "user":
                    raise ChatIntegrityError("chat reply binding invalid")
                if target in replied:
                    raise ChatIntegrityError("duplicate iKant reply binding")
                replied.add(target)
            elif row.get("reply_to_seq") is not None:
                raise ChatIntegrityError("user reply binding invalid")
            if row.get("prev_sha256") != prev:
                raise ChatIntegrityError("chat hash chain predecessor mismatch")
            supplied = row.get("sha256")
            material = dict(row)
            material.pop("sha256", None)
            if supplied != _digest(material):
                raise ChatIntegrityError("chat record digest mismatch")
            prev = supplied
        self._indexed = True
        self._last_seq = len(rows)
        self._last_sha256 = prev
        self._roles_by_seq = roles
        self._replied_user_seqs = replied
        return {
            "schema": CHAT_INDEX_SCHEMA,
            "ok": True,
            "records": len(rows),
            "last_sha256": prev,
            "runtime_session_id": self.runtime_session_id,
        }

    def append(
        self,
        role: str,
        text: str,
        *,
        cycle_id: str | None = None,
        response_id: str | None = None,
        intention_node_id: str | None = None,
        reply_to_seq: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        role = str(role)
        if role not in _ALLOWED_ROLES:
            raise ValueError("chat role must be user or ikant")
        text = str(text)
        if not text.strip():
            raise ValueError("chat text must not be empty")
        if len(text.encode("utf-8")) > 65536:
            raise ValueError("chat text exceeds 64 KiB record bound")
        if not self._indexed:
            self.verify()
        seq = self._last_seq + 1
        prev = self._last_sha256
        if role == "ikant":
            if reply_to_seq is None or not 1 <= int(reply_to_seq) < seq:
                raise ValueError("iKant record requires a valid earlier reply_to_seq")
            if self._roles_by_seq.get(int(reply_to_seq)) != "user":
                raise ValueError("iKant reply target must be a user record")
            if int(reply_to_seq) in self._replied_user_seqs:
                raise ValueError("user record already has an iKant reply")
        elif reply_to_seq is not None:
            raise ValueError("user record cannot reply_to_seq")
        record: dict[str, Any] = {
            "schema": CHAT_SCHEMA,
            "seq": seq,
            "at": _now(),
            "runtime_session_id": self.runtime_session_id,
            "role": role,
            "text": text,
            "cycle_id": cycle_id,
            "response_id": response_id,
            "intention_node_id": intention_node_id,
            "reply_to_seq": reply_to_seq,
            "metadata": dict(metadata or {}),
            "prev_sha256": prev,
        }
        record["sha256"] = _digest(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._last_seq = seq
        self._last_sha256 = record["sha256"]
        self._roles_by_seq[seq] = role
        if role == "ikant": self._replied_user_seqs.add(int(reply_to_seq))
        return record

    def render(self, *, limit: int = 20, width: int = 96) -> str:
        if width < 48:
            raise ValueError("shell width must be >= 48")
        rows = self.rows()[-max(1, int(limit)):]
        out = ["=" * width, " iKant persistent chat ".center(width, "-"), "=" * width]
        for row in rows:
            prefix = "> iKant:" if row["role"] == "ikant" else "> user:"
            clean = sanitize_shell_content(row["text"])
            logical_lines = clean.split("\n") or [""]
            first = True
            for logical in logical_lines:
                chunks = textwrap.wrap(logical, width=max(12, width - len(prefix) - 1), replace_whitespace=False, drop_whitespace=False) or [""]
                for chunk in chunks:
                    out.append(f"{prefix if first else ' ' * len(prefix)} {chunk}".rstrip())
                    first = False
        out.extend(["-" * width, "> iKant:"])
        return "\n".join(out)


class ChatController:
    """Bind visible chat persistence to the v0.3 conforming host loop."""

    def __init__(
        self,
        runtime: Any,
        *,
        turn_fn: Callable[..., dict[str, Any]] | None = None,
        emit_fn: Callable[..., dict[str, Any]] | None = None,
        dashboard_fn: Callable[..., dict[str, Any]] | None = None,
    ):
        self.runtime = runtime
        session_id = str(runtime.runtime.get("session_id") or "")
        if not session_id:
            raise ValueError("runtime session_id required")
        state_dir = Path(runtime.state_dir)
        self.log = ChatLog(state_dir / "chat" / "transcript.jsonl", runtime_session_id=session_id)
        if turn_fn is None or emit_fn is None:
            from .host import conforming_turn, emit_conforming_surface_a
            turn_fn = turn_fn or conforming_turn
            emit_fn = emit_fn or emit_conforming_surface_a
        if dashboard_fn is None:
            from .dashboard import persist_dashboard
            dashboard_fn = persist_dashboard
        self.turn_fn = turn_fn
        self.emit_fn = emit_fn
        self.dashboard_fn = dashboard_fn

    def begin(self, intent: str, *, engine_label: str | None = None, **kwargs: Any) -> dict[str, Any]:
        if not self.log._indexed:
            self.log.verify()
        if self.runtime.runtime.get("cognitive", {}).get("pending_surface_a_cycle_id"):
            raise RuntimeError("pending Surface A must close before persisting another chat input")
        host = self.runtime.runtime.get("host", {})
        bound = str(host.get("engine_label") or "").strip()
        supplied = str(engine_label or os.environ.get("IKANT_HOST_ENGINE") or "").strip()
        if not bound and not supplied:
            raise PermissionError("host engine disclosure required before chat persistence")
        if bound and supplied and bound != supplied:
            raise PermissionError("host engine binding mismatch before chat persistence")
        out = self.turn_fn(self.runtime, intent, engine_label=engine_label, **kwargs)
        user = self.log.append(
            "user",
            intent,
            cycle_id=out.get("cycle", {}).get("cycle_id"),
            intention_node_id=out.get("intention_node_id"),
            metadata={"speech_act_not_evidence": True},
        )
        out.setdefault("chat", {})["user_seq"] = user["seq"]
        out["chat"]["shell_prompt"] = "> iKant:"
        self.dashboard_fn(self.runtime)
        return out

    def close(self, cycle_id: str, text: str, *, intention_node_id: str | None = None, user_seq: int | None = None) -> dict[str, Any]:
        if not self.log._indexed:
            self.log.verify()
        rows = self.log.rows()
        if user_seq is None:
            candidates = [r["seq"] for r in rows if r.get("role") == "user" and not any(x.get("role") == "ikant" and x.get("reply_to_seq") == r["seq"] for x in rows)]
            if not candidates:
                raise PermissionError("no unanswered user chat record")
            user_seq = candidates[-1]
        rec = self.emit_fn(self.runtime, cycle_id, text, intention_node_id=intention_node_id)
        response = self.log.append(
            "ikant",
            text,
            cycle_id=cycle_id,
            response_id=rec.get("response_id"),
            intention_node_id=intention_node_id,
            reply_to_seq=user_seq,
            metadata={"surface_a_validated": True, "speech_act_not_evidence": True},
        )
        dash = self.dashboard_fn(self.runtime)
        return {**rec, "chat_record": response, "dashboard": dash, "shell_prompt": "> iKant:"}
