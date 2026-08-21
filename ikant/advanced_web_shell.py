from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import secrets
import threading
from typing import Any, Callable

from .managed_runtime import ManagedLocalEmbodimentService
from .web_frame import WEB_ACK_SCHEMA, WEB_FRAME_SCHEMA

ADVANCED_WEB_SHELL_SCHEMA = "ikant-advanced-web-shell/v0.26-test"
SHELL_COMMAND_SCHEMA = "ikant-advanced-web-shell-command/v0.26-test"
SHELL_ACK_SCHEMA = "ikant-advanced-web-shell-ack/v0.26-test"
SHELL_OPS = frozenset({"SYNC", "TURN", "EXIT", "RESUME"})
MAX_TURN_BYTES = 65536
MAX_ID_BYTES = 160
MAX_SHELL_OPERATIONS = 4096
_ID_RE = re.compile(r"^[A-Za-z0-9._~-]{16,160}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class AdvancedWebShellError(PermissionError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bounded_id(value: object, label: str) -> str:
    text = str(value or "")
    if len(text.encode("utf-8")) > MAX_ID_BYTES or not _ID_RE.fullmatch(text):
        raise AdvancedWebShellError(f"invalid {label}")
    return text


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise AdvancedWebShellError(f"invalid {label}")
    return value


def _frame_identity_from_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise AdvancedWebShellError("frame receipt required")
    session = str(receipt.get("runtime_session_id") or "")
    sha = str(receipt.get("frame_sha256") or "")
    epoch = _positive_int(receipt.get("epoch"), "frame epoch")
    seq = _positive_int(receipt.get("frame_seq"), "frame sequence")
    if not session or not _SHA_RE.fullmatch(sha):
        raise AdvancedWebShellError("invalid frame identity")
    return {"runtime_session_id": session, "epoch": epoch, "frame_seq": seq, "frame_sha256": sha}


def _frame_identity(frame: Any) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != WEB_FRAME_SCHEMA:
        raise AdvancedWebShellError("canonical web frame required")
    return _frame_identity_from_receipt(frame.get("receipt"))


def _expected_frame(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"runtime_session_id", "epoch", "frame_seq", "frame_sha256"}:
        raise AdvancedWebShellError("invalid expected frame binding")
    return _frame_identity_from_receipt(value)


def _validate_payload(op: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AdvancedWebShellError("shell payload must be object")
    if op == "TURN":
        if set(payload) != {"text"} or not isinstance(payload.get("text"), str):
            raise AdvancedWebShellError("TURN payload must contain exact text field")
        text = payload["text"]
        if not text.strip() or "\x00" in text or len(text.encode("utf-8")) > MAX_TURN_BYTES:
            raise AdvancedWebShellError("TURN text outside bound")
        return {"text": text}
    if payload:
        raise AdvancedWebShellError(f"{op} payload must be empty")
    return {}


class AdvancedWebShellController:
    """Process-local, zero-authority single-writer protocol for the canonical PWA.

    The shell never creates grants, leases or execution authority. It makes browser retry,
    concurrency and exact-frame acknowledgement explicit around existing S2/S7 methods.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._shell_id: str | None = None
        self._client_id: str | None = None
        self._runtime_session_id: str | None = None
        self._next_seq = 1
        self._pending: dict[str, Any] | None = None
        self._last_acked_frame: dict[str, Any] | None = None
        self._last_ack: dict[str, Any] | None = None
        self._used_keys: dict[str, str] = {}

    @property
    def claimed(self) -> bool:
        with self._lock:
            return self._shell_id is not None

    def _require_bound(self, runtime_session_id: str, shell_id: object, client_id: object) -> tuple[str, str]:
        if not self._shell_id or not self._client_id or not self._runtime_session_id:
            raise AdvancedWebShellError("advanced web shell not open")
        shell = _bounded_id(shell_id, "shell id")
        client = _bounded_id(client_id, "client id")
        if shell != self._shell_id or client != self._client_id:
            raise AdvancedWebShellError("shell writer binding mismatch")
        if str(runtime_session_id or "") != self._runtime_session_id:
            raise AdvancedWebShellError("runtime session drift")
        return shell, client

    def _base_projection(self) -> dict[str, Any]:
        return {
            "schema": ADVANCED_WEB_SHELL_SCHEMA,
            "shell_id": self._shell_id,
            "client_id": self._client_id,
            "runtime_session_id": self._runtime_session_id,
            "next_seq": self._next_seq,
            "max_operations": MAX_SHELL_OPERATIONS,
            "single_writer": True,
            "paired_transport_required": True,
            "expected_frame_binding_required": self._next_seq > 1,
            "pending_operation": self._pending is not None,
            "pending_seq": self._pending.get("seq") if self._pending else None,
            "last_acked_frame": deepcopy(self._last_acked_frame),
            "semantic_output_channel": "HSPV2_SEALED_DASHBOARD_ONLY",
            "browser_is_authority": False,
            "shell_state_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def open(self, runtime_session_id: str, client_id: object) -> dict[str, Any]:
        with self._lock:
            session = str(runtime_session_id or "")
            client = _bounded_id(client_id, "client id")
            if not session:
                raise AdvancedWebShellError("runtime session required")
            if self._shell_id is None:
                self._shell_id = secrets.token_urlsafe(24)
                self._client_id = client
                self._runtime_session_id = session
            else:
                if session != self._runtime_session_id:
                    raise AdvancedWebShellError("runtime session drift")
                if client != self._client_id:
                    raise AdvancedWebShellError("advanced web shell writer already claimed")
            out = self._base_projection()
            out["pending_response"] = deepcopy(self._pending.get("response")) if self._pending else None
            return out

    def execute(
        self,
        runtime_session_id: str,
        command: dict[str, Any],
        execute_fn: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        with self._lock:
            if not isinstance(command, dict) or set(command) != {
                "schema", "shell_id", "client_id", "seq", "op", "idempotency_key", "expected_frame", "payload"
            }:
                raise AdvancedWebShellError("invalid shell command shape")
            if command.get("schema") != SHELL_COMMAND_SCHEMA:
                raise AdvancedWebShellError("shell command schema mismatch")
            shell, client = self._require_bound(runtime_session_id, command.get("shell_id"), command.get("client_id"))
            seq = _positive_int(command.get("seq"), "shell sequence")
            op = str(command.get("op") or "").upper()
            if op not in SHELL_OPS:
                raise AdvancedWebShellError("unsupported shell operation")
            idem = _bounded_id(command.get("idempotency_key"), "idempotency key")
            expected = _expected_frame(command.get("expected_frame"))
            payload = _validate_payload(op, command.get("payload"))
            canonical_command = {
                "schema": SHELL_COMMAND_SCHEMA,
                "shell_id": shell,
                "client_id": client,
                "seq": seq,
                "op": op,
                "idempotency_key": idem,
                "expected_frame": expected,
                "payload": payload,
            }
            command_sha = _digest(canonical_command)

            if self._pending is not None:
                p = self._pending
                if seq == p["seq"] and idem == p["idempotency_key"] and command_sha == p["command_sha256"]:
                    out = deepcopy(p["response"])
                    out["operation"]["replay"] = True
                    return out
                raise AdvancedWebShellError("another shell operation is awaiting exact ACK")

            if seq != self._next_seq:
                raise AdvancedWebShellError("shell sequence drift")
            if seq > MAX_SHELL_OPERATIONS:
                raise AdvancedWebShellError("shell operation budget exhausted; restart runtime for a fresh shell session")
            if idem in self._used_keys:
                raise AdvancedWebShellError("idempotency key reuse")
            if self._next_seq == 1:
                if op != "SYNC" or expected is not None:
                    raise AdvancedWebShellError("first shell operation must be unbound SYNC")
            elif expected != self._last_acked_frame:
                raise AdvancedWebShellError("expected frame does not match last exact ACK")

            frame = execute_fn(op, payload)
            if not isinstance(frame, dict):
                raise AdvancedWebShellError("shell operation returned invalid response")
            if frame.get("released") is True:
                if op != "SYNC":
                    raise AdvancedWebShellError("only SYNC may observe already released egress without a frame")
                self._remember_key(idem, command_sha)
                self._next_seq += 1
                out = {
                    **self._base_projection(),
                    "status": "RELEASED",
                    "operation": {"seq": seq, "op": op, "idempotency_key": idem, "command_sha256": command_sha, "replay": False},
                    "frame": None,
                    "released": True,
                }
                out["next_seq"] = self._next_seq
                return out

            identity = _frame_identity(frame)
            if identity["runtime_session_id"] != self._runtime_session_id:
                raise AdvancedWebShellError("returned frame runtime session mismatch")
            response = {
                **self._base_projection(),
                "status": "FRAME_PENDING",
                "operation": {"seq": seq, "op": op, "idempotency_key": idem, "command_sha256": command_sha, "replay": False},
                "expected_ack": identity,
                "frame": deepcopy(frame),
                "released": False,
                "pending_operation": True,
                "pending_seq": seq,
            }
            self._remember_key(idem, command_sha)
            self._pending = {
                "seq": seq,
                "idempotency_key": idem,
                "command_sha256": command_sha,
                "frame_identity": identity,
                "response": deepcopy(response),
            }
            return response

    def acknowledge(
        self,
        runtime_session_id: str,
        envelope: dict[str, Any],
        acknowledge_fn: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        with self._lock:
            if not isinstance(envelope, dict) or set(envelope) != {
                "schema", "shell_id", "client_id", "seq", "idempotency_key", "frame_ack"
            }:
                raise AdvancedWebShellError("invalid shell ACK shape")
            if envelope.get("schema") != SHELL_ACK_SCHEMA:
                raise AdvancedWebShellError("shell ACK schema mismatch")
            shell, client = self._require_bound(runtime_session_id, envelope.get("shell_id"), envelope.get("client_id"))
            seq = _positive_int(envelope.get("seq"), "ACK sequence")
            idem = _bounded_id(envelope.get("idempotency_key"), "ACK idempotency key")
            frame_ack = envelope.get("frame_ack")
            if not isinstance(frame_ack, dict) or frame_ack.get("schema") != WEB_ACK_SCHEMA:
                raise AdvancedWebShellError("canonical web ACK required")
            ack_material = {"shell_id": shell, "client_id": client, "seq": seq, "idempotency_key": idem, "frame_ack": frame_ack}
            ack_sha = _digest(ack_material)

            if self._pending is None:
                if self._last_ack and seq == self._last_ack["seq"] and idem == self._last_ack["idempotency_key"] and ack_sha == self._last_ack["ack_sha256"]:
                    out = deepcopy(self._last_ack["response"])
                    out["replay"] = True
                    return out
                raise AdvancedWebShellError("no shell operation awaits ACK")

            pending = self._pending
            if seq != pending["seq"] or idem != pending["idempotency_key"]:
                raise AdvancedWebShellError("shell ACK operation binding mismatch")
            if _frame_identity_from_receipt(frame_ack) != pending["frame_identity"]:
                raise AdvancedWebShellError("shell ACK frame binding mismatch")

            result = acknowledge_fn(frame_ack)
            if not isinstance(result, dict) or result.get("acknowledged") is not True:
                raise AdvancedWebShellError("underlying exact frame ACK failed")
            self._last_acked_frame = deepcopy(pending["frame_identity"])
            self._pending = None
            self._next_seq += 1
            status = "RELEASED" if str(result.get("delivery_state") or "") == "RELEASED" else "READY"
            response = {
                **self._base_projection(),
                "status": status,
                "acknowledged": True,
                "acked_seq": seq,
                "last_acked_frame": deepcopy(self._last_acked_frame),
                "replay": False,
            }
            self._last_ack = {"seq": seq, "idempotency_key": idem, "ack_sha256": ack_sha, "response": deepcopy(response)}
            return response

    def _remember_key(self, key: str, command_sha: str) -> None:
        self._used_keys[key] = command_sha


class AdvancedWebShellService(ManagedLocalEmbodimentService):
    """S8 service adapter. S2/S5 behavior remains inherited; S8 wraps canonical PWA operations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.web_shell = AdvancedWebShellController()

    def shell_claimed(self) -> bool:
        return self.web_shell.claimed

    def _active_session_id(self) -> str:
        from .runtime import Runtime
        rt = Runtime(self.state_dir)
        try:
            rt.require_active()
            session = str((rt.runtime or {}).get("session_id") or "")
            if not session:
                raise AdvancedWebShellError("ACTIVE runtime session missing")
            return session
        finally:
            rt.close()

    def shell_open(self, client_id: object) -> dict[str, Any]:
        self.require_web_conformance()
        return self.web_shell.open(self._active_session_id(), client_id)

    def shell_command(self, command: dict[str, Any]) -> dict[str, Any]:
        self.require_web_conformance()
        session = self._active_session_id()

        def execute(op: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                if op == "SYNC":
                    return self.frame()
                if op == "TURN":
                    return self.turn(payload["text"])
                if op == "EXIT":
                    return self.turn("EXIT IKANT")
                if op == "RESUME":
                    return self.resume("RESUME IKANT")
                raise AdvancedWebShellError("unsupported shell operation")
            except AdvancedWebShellError:
                raise
            except Exception as exc:
                try:
                    from .runtime import Runtime
                    from .session_egress import EgressState, existing_runtime_egress
                    rt = Runtime(self.state_dir)
                    try:
                        guard = existing_runtime_egress(rt)
                        pending = bool(guard and guard.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING})
                    finally:
                        rt.close()
                    if pending:
                        return self.frame()
                except Exception:
                    pass
                return self.notice(str(exc), kind="ADVANCED_WEB_SHELL_ERROR")

        return self.web_shell.execute(session, command, execute)

    def shell_ack(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.require_web_conformance()
        return self.web_shell.acknowledge(self._active_session_id(), envelope, self.acknowledge)
