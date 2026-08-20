from __future__ import annotations

import hashlib
from typing import Any

WEB_FRAME_SCHEMA = "ikant-web-human-frame/v0.20-test"
WEB_ACK_SCHEMA = "ikant-web-human-ack/v0.20-test"


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wrap_prepared_frame(prepared: dict[str, Any]) -> dict[str, Any]:
    """Wrap an existing sealed dashboard frame without changing its human-visible bytes.

    S2 intentionally keeps the v0.12 egress contract intact: the PWA renders `text` verbatim.
    The wrapper is transport metadata only and has zero epistemic/execution authority.
    """
    text = str(prepared.get("text") or "")
    receipt = dict(prepared.get("receipt") or {})
    expected = str(receipt.get("frame_sha256") or "")
    if not text or not expected or _sha_text(text) != expected:
        raise ValueError("prepared frame text/receipt digest mismatch")
    return {
        "schema": WEB_FRAME_SCHEMA,
        "text": text,
        "receipt": receipt,
        "delivery_state": str(prepared.get("delivery_state") or ""),
        "acknowledged": bool(prepared.get("acknowledged", False)),
        "recovery": bool(prepared.get("recovery", False)),
        "render_contract": {
            "mode": "VERBATIM_TEXT",
            "dom_text_content_must_equal_text": True,
            "visual_reformatting_of_semantic_payload_forbidden": True,
            "tts_of_active_output_enabled": False,
        },
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def build_web_ack(frame: dict[str, Any], visible_text: str) -> dict[str, Any]:
    if frame.get("schema") != WEB_FRAME_SCHEMA:
        raise ValueError("web frame schema mismatch")
    return {
        "schema": WEB_ACK_SCHEMA,
        "runtime_session_id": (frame.get("receipt") or {}).get("runtime_session_id"),
        "epoch": (frame.get("receipt") or {}).get("epoch"),
        "frame_seq": (frame.get("receipt") or {}).get("frame_seq"),
        "frame_sha256": (frame.get("receipt") or {}).get("frame_sha256"),
        "visible_text": str(visible_text),
        "visible_text_sha256": _sha_text(str(visible_text)),
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def validate_web_ack(frame: dict[str, Any], ack: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if frame.get("schema") != WEB_FRAME_SCHEMA:
        errors.append("frame schema")
    if ack.get("schema") != WEB_ACK_SCHEMA:
        errors.append("ack schema")
    receipt = dict(frame.get("receipt") or {})
    for key in ("runtime_session_id", "epoch", "frame_seq", "frame_sha256"):
        if ack.get(key) != receipt.get(key):
            errors.append("ack " + key)
    text = str(frame.get("text") or "")
    visible = str(ack.get("visible_text") or "")
    if visible != text:
        errors.append("visible text differs from sealed frame")
    if ack.get("visible_text_sha256") != _sha_text(visible):
        errors.append("visible text digest")
    if ack.get("frame_sha256") != _sha_text(text):
        errors.append("sealed frame digest")
    if ack.get("epistemic_authority") not in {0, 0.0} or ack.get("execution_authority") not in {0, 0.0}:
        errors.append("ack authority")
    return not errors, errors
