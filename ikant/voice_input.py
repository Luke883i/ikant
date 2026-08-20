from __future__ import annotations

import json
import secrets
from typing import Any, Callable
from urllib.request import Request, urlopen

from .local_security import require_loopback_url

VOICE_INPUT_SCHEMA = "ikant-local-voice-input/v0.20-test"
_MAX_AUDIO_BYTES = 8 * 1024 * 1024
_ALLOWED_AUDIO = {
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
}


class LocalVoiceError(RuntimeError):
    pass


class LocalVoiceInputBroker:
    """Optional local STT adapter. Voice is input observation only, never an approval modality."""

    def __init__(self, endpoint: str | None, *, timeout: float = 45.0, opener: Callable[..., Any] = urlopen):
        self.endpoint = None if not endpoint else require_loopback_url(str(endpoint))
        self.timeout = float(timeout)
        self.opener = opener

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)

    def status(self) -> dict[str, Any]:
        return {
            "schema": VOICE_INPUT_SCHEMA,
            "configured": self.configured,
            "endpoint_scope": "LOOPBACK_ONLY" if self.configured else "DISABLED",
            "voice_is_input_only": True,
            "voice_can_approve_authority": False,
            "tts_active_output_enabled": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def transcribe(self, audio: bytes, content_type: str) -> dict[str, Any]:
        if not self.endpoint:
            raise LocalVoiceError("local STT endpoint not configured")
        raw = bytes(audio)
        media_type = str(content_type or "").split(";", 1)[0].strip().lower()
        if media_type not in _ALLOWED_AUDIO:
            raise LocalVoiceError("unsupported audio content type")
        if not raw or len(raw) > _MAX_AUDIO_BYTES:
            raise LocalVoiceError("audio payload outside bound")
        boundary = "----ikant" + secrets.token_hex(12)
        filename = "voice.webm" if media_type == "audio/webm" else "voice.bin"
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {media_type}\r\n\r\n'.encode()
        )
        body.extend(raw)
        body.extend(b"\r\n")
        for name, value in (("temperature", "0.0"), ("response_format", "json")):
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        body.extend(f"--{boundary}--\r\n".encode())
        req = Request(
            self.endpoint,
            data=bytes(body),
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            with self.opener(req, timeout=self.timeout) as response:
                data = response.read(1024 * 1024 + 1)
        except Exception as exc:
            raise LocalVoiceError("local STT request failed") from exc
        if len(data) > 1024 * 1024:
            raise LocalVoiceError("local STT response exceeds bound")
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise LocalVoiceError("local STT returned invalid JSON") from exc
        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise LocalVoiceError("local STT response text missing")
        text = text.strip()
        if len(text.encode("utf-8")) > 65536:
            raise LocalVoiceError("transcript exceeds input bound")
        return {
            "schema": VOICE_INPUT_SCHEMA,
            "text": text,
            "source": "local_stt",
            "voice_is_input_only": True,
            "authority_effect": "NONE",
            "may_fill_intent_field": True,
            "may_approve_capability_or_action": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
