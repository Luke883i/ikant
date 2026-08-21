from __future__ import annotations

from dataclasses import dataclass
import re

MAX_STDERR_TAIL_BYTES = 4096

_SECRET_PATTERNS = (
    re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*[^\s]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]+"),
)


def _redact(text: str) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def bounded_stderr_tail(raw: bytes, *, limit: int = MAX_STDERR_TAIL_BYTES) -> str:
    """Return a redacted UTF-8 tail whose encoded representation never exceeds limit."""
    if limit <= 0:
        return ""
    text = raw[-limit:].decode("utf-8", errors="replace")
    encoded = _redact(text).encode("utf-8", errors="replace")
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
        return cls(
            kind=kind,
            returncode=returncode,
            signal=signal,
            stderr_tail=bounded_stderr_tail(stderr),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "returncode": self.returncode,
            "signal": self.signal,
            "stderr_tail": self.stderr_tail,
        }
