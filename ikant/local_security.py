from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import ipaddress
import os
import secrets
import threading
from urllib.parse import urlparse

PAIRING_SCHEMA = "ikant-local-pairing/v0.20-test"


class LocalSecurityError(PermissionError):
    pass


def _host_only(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith("["):
        end = raw.find("]")
        return raw[: end + 1] if end >= 0 else raw
    return raw.split(":", 1)[0]


def is_loopback_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = str(hostname).strip().strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_loopback_url(url: str, *, allowed_paths: tuple[str, ...] = ()) -> str:
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "http" or not is_loopback_hostname(parsed.hostname):
        raise ValueError("local adapter endpoint must use http on loopback")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("adapter endpoint credentials/fragments forbidden")
    if allowed_paths and parsed.path not in allowed_paths:
        raise ValueError("adapter endpoint path not allowed")
    return parsed.geturl()


def codespaces_host(port: int, env: dict[str, str] | None = None) -> str | None:
    env = dict(os.environ if env is None else env)
    name = str(env.get("CODESPACE_NAME") or "").strip()
    domain = str(env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN") or "").strip().strip(".")
    if not name or not domain:
        return None
    return f"{name}-{int(port)}.{domain}".lower()


def allowed_hostnames(port: int, *, bind_host: str, env: dict[str, str] | None = None) -> frozenset[str]:
    out = {"localhost", "127.0.0.1", "[::1]"}
    if is_loopback_hostname(bind_host):
        out.add(_host_only(bind_host))
    cs = codespaces_host(port, env)
    if cs:
        out.add(cs)
    return frozenset(x for x in out if x)


def origin_allowed(origin: str | None, host_header: str, *, scheme: str = "http") -> bool:
    if origin in {None, ""}:
        return False
    try:
        parsed = urlparse(str(origin))
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    expected = str(host_header or "").strip().lower()
    actual = str(parsed.netloc or "").strip().lower()
    if not expected or actual != expected:
        return False
    host = _host_only(expected).strip("[]")
    if is_loopback_hostname(host):
        return parsed.scheme == "http"
    return parsed.scheme == "https"


@dataclass
class PairingSession:
    code: str
    bearer_token: str | None
    paired: bool
    failed_attempts: int
    max_attempts: int
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def create(cls, *, max_attempts: int = 6) -> "PairingSession":
        # 12 URL-safe random bytes are human-copyable while still high entropy for a local one-time code.
        return cls(secrets.token_urlsafe(12), None, False, 0, int(max_attempts))

    def pair(self, candidate: str) -> str:
        with self._lock:
            if self.paired:
                raise LocalSecurityError("pairing code already consumed")
            if self.failed_attempts >= self.max_attempts:
                raise LocalSecurityError("pairing locked after failed attempts")
            if not hmac.compare_digest(str(candidate or ""), self.code):
                self.failed_attempts += 1
                raise LocalSecurityError("invalid pairing code")
            self.paired = True
            self.code = ""
            self.bearer_token = secrets.token_urlsafe(32)
            return self.bearer_token

    def authenticate(self, authorization: str | None) -> bool:
        with self._lock:
            if not self.paired or not self.bearer_token:
                return False
            prefix = "Bearer "
            raw = str(authorization or "")
            if not raw.startswith(prefix):
                return False
            return hmac.compare_digest(raw[len(prefix) :], self.bearer_token)

    def public_status(self) -> dict[str, object]:
        return {
            "schema": PAIRING_SCHEMA,
            "paired": self.paired,
            "pairing_locked": self.failed_attempts >= self.max_attempts,
            "failed_attempts": self.failed_attempts,
            "max_attempts": self.max_attempts,
        }
