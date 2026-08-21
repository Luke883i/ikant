from __future__ import annotations

from dataclasses import dataclass
import re
import threading

MAX_STDERR_TAIL_BYTES = 4096
MAX_STDERR_CAPTURE_BYTES = 64 * 1024

_SECRET_PATTERNS = (
    re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*[^\s]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+"),
)


def _redact(text: str) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def bounded_stderr_tail(raw: bytes, *, limit: int = MAX_STDERR_TAIL_BYTES) -> str:
    """Return a redacted UTF-8 suffix whose encoded form never exceeds limit."""
    if limit <= 0:
        return ""
    # Redact the bounded capture before taking the public tail so a credential
    # marker just before the final 4096 bytes cannot be sliced away first.
    encoded = _redact(raw.decode("utf-8", errors="replace")).encode("utf-8", errors="replace")
    if len(encoded) > limit:
        encoded = encoded[-limit:]
    return encoded.decode("utf-8", errors="ignore")


@dataclass(frozen=True, slots=True)
class EngineExitDiagnostic:
    """Zero-authority facts observed when a managed engine process terminates."""

    kind: str
    returncode: int | None
    signal: int | None
    stderr_tail: str

    @classmethod
    def capture(cls, returncode: int | None, stderr: bytes) -> "EngineExitDiagnostic":
        if returncode is None:
            kind = "UNKNOWN"
            signal = None
        elif returncode < 0:
            kind = "SIGNAL"
            signal = -returncode
        else:
            kind = "EXIT_STATUS"
            signal = None
        return cls(kind=kind, returncode=returncode, signal=signal, stderr_tail=bounded_stderr_tail(stderr))

    def as_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "returncode": self.returncode, "signal": self.signal, "stderr_tail": self.stderr_tail}


class BoundedStderrCapture:
    """Continuously drain stderr while retaining only a bounded raw suffix."""

    def __init__(self, *, limit: int = MAX_STDERR_CAPTURE_BYTES) -> None:
        self.limit = max(MAX_STDERR_TAIL_BYTES, int(limit))
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def feed(self, chunk: bytes) -> None:
        if not chunk:
            return
        with self._lock:
            if len(chunk) >= self.limit:
                self._buffer[:] = chunk[-self.limit:]
                return
            self._buffer.extend(chunk)
            overflow = len(self._buffer) - self.limit
            if overflow > 0:
                del self._buffer[:overflow]

    def start(self, stream) -> None:
        if stream is None:
            return
        def drain() -> None:
            try:
                while True:
                    chunk = stream.read(8192)
                    if not chunk:
                        break
                    self.feed(chunk)
            finally:
                try:
                    stream.close()
                except Exception:
                    pass
        self._thread = threading.Thread(target=drain, name="ikant-engine-stderr-drain", daemon=True)
        self._thread.start()

    def finish(self, *, timeout: float = 1.0) -> None:
        if self._thread is not None:
            self._thread.join(timeout=max(0.0, float(timeout)))

    def snapshot(self) -> bytes:
        with self._lock:
            return bytes(self._buffer)
