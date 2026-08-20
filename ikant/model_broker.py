from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .local_security import require_loopback_url

MODEL_BROKER_SCHEMA = "ikant-local-model-broker/v0.23-test"


class LocalModelError(RuntimeError):
    pass


class LocalModelBroker:
    """Zero-authority adapter for an iKant-owned or explicitly supplied loopback model endpoint."""

    def __init__(
        self,
        endpoint: str | None,
        *,
        model: str = "Qwen3.5-0.8B",
        timeout: float = 45.0,
        opener: Callable[..., Any] = urlopen,
        api_key: str | None = None,
        runtime_binding_digest: str | None = None,
        managed_runtime: bool = False,
    ):
        self.endpoint = None if not endpoint else require_loopback_url(str(endpoint))
        self.model = str(model or "Qwen3.5-0.8B")
        self.timeout = float(timeout)
        self.opener = opener
        self._api_key = str(api_key) if api_key else None
        self.runtime_binding_digest = str(runtime_binding_digest) if runtime_binding_digest else None
        self.managed_runtime = bool(managed_runtime)
        if self.managed_runtime and (not self.endpoint or not self._api_key or not self.runtime_binding_digest):
            raise LocalModelError("managed model broker requires endpoint, private key and runtime binding")

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["Authorization"] = "Bearer " + self._api_key
        return headers

    def status(self) -> dict[str, Any]:
        out = {
            "schema": MODEL_BROKER_SCHEMA,
            "configured": self.configured,
            "endpoint_scope": "LOOPBACK_ONLY" if self.configured else "DISABLED",
            "model": self.model,
            "managed_runtime": self.managed_runtime,
            "api_key_exposed": False,
            "tool_calls_accepted": False,
            "model_output_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        if self.managed_runtime:
            out["runtime_binding_digest"] = self.runtime_binding_digest
        return out

    def _models_url(self) -> str:
        if not self.endpoint:
            raise LocalModelError("local model endpoint not configured")
        parsed = urlparse(self.endpoint)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if "/v1/" in parsed.path:
            return base + "/v1/models"
        return base + "/models"

    def health(self) -> bool:
        if not self.endpoint:
            return False
        req = Request(self._models_url(), method="GET", headers=self._headers())
        try:
            with self.opener(req, timeout=min(self.timeout, 3.0)) as response:
                return 200 <= int(getattr(response, "status", 200)) < 300
        except Exception:
            return False

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            raise LocalModelError("local model endpoint not configured")
        req = Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers=self._headers(json_body=True),
        )
        try:
            with self.opener(req, timeout=self.timeout) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
        except Exception as exc:
            raise LocalModelError("local model request failed") from exc
        if len(raw) > 2 * 1024 * 1024:
            raise LocalModelError("local model response exceeds bound")
        try:
            out = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise LocalModelError("local model returned invalid JSON") from exc
        if not isinstance(out, dict):
            raise LocalModelError("local model response must be an object")
        return out

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise LocalModelError("local model response choices invalid")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise LocalModelError("local model response message invalid")
        if message.get("tool_calls"):
            raise LocalModelError("model tool calls are forbidden in iKant")
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            raise LocalModelError("local model response content missing")
        return text.strip()

    def complete_surface_a(
        self,
        contract: dict[str, Any],
        user_text: str,
        *,
        validator: Callable[[str], tuple[bool, list[str]]] | None = None,
        max_repairs: int = 2,
    ) -> str:
        if validator is None:
            from .surfaces import validate_surface_a

            validator = validate_surface_a
        system = (
            "You are the replaceable local language engine underneath iKant. "
            "You have zero authority and may not call tools. Produce only Surface A text.\n"
            + json.dumps(contract, ensure_ascii=False, sort_keys=True)
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": str(user_text)},
        ]
        attempts = 0
        while True:
            response = self._request(
                {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 900,
                    "stream": False,
                    "tools": [],
                }
            )
            text = self._extract_text(response)
            ok, errors = validator(text)
            if ok:
                return text
            if attempts >= int(max_repairs):
                raise LocalModelError("local model failed Surface A validation: " + "; ".join(errors))
            attempts += 1
            messages.append({"role": "assistant", "content": text})
            messages.append(
                {
                    "role": "user",
                    "content": "Repair only the response text. Validation errors: " + "; ".join(errors),
                }
            )
