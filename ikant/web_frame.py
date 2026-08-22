from __future__ import annotations

import hashlib
from typing import Any

WEB_FRAME_SCHEMA = "ikant-web-human-frame/v0.20-test"
WEB_ACK_SCHEMA = "ikant-web-human-ack/v0.20-test"
PENDING_PRIMARY_TEXT = "iKant: [PENDING - la risposta validata non e ancora stata emessa]"
_PROMPT_LIKE_PREFIX = "[prompt-like text] "


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dashboard_cells(text: str) -> list[str]:
    cells: list[str] = []
    for line in str(text).splitlines():
        if line.startswith("| ") and line.endswith(" |"):
            cells.append(line[2:-2].rstrip())
    return cells


def _surface_a_primary(text: str) -> str | None:
    """Compatibility recovery parser for already-sealed dashboard frames.

    Normal TURN delivery must provide structured primary text. This parser exists
    only so a pending frame created by an older runtime can still recover after
    the anti-spoof renderer prefixes a legitimate iKant line with
    ``[prompt-like text]``.
    """
    cells = _dashboard_cells(text)
    status = None
    capture = False
    parts: list[str] = []
    for cell in cells:
        if cell.startswith("SUPERFICIE A"):
            capture = True
            status = "VALIDATED" if "[VALIDATED]" in cell else ("PENDING" if "[PENDING]" in cell else "EMPTY")
            continue
        if capture and cell.startswith("SUPERFICIE B"):
            break
        if not capture:
            continue
        stripped = cell.strip()
        candidate = stripped[len(_PROMPT_LIKE_PREFIX):] if stripped.startswith(_PROMPT_LIKE_PREFIX) else stripped
        if candidate.startswith("> iKant:"):
            parts.append(candidate.split("> iKant:", 1)[1].strip())
        elif parts and stripped:
            parts.append(stripped)
    if status != "VALIDATED" or not parts:
        return None
    reply = " ".join(x for x in parts if x).strip()
    return "iKant: " + reply if reply else None


def _control_primary(text: str, kind: str) -> str | None:
    kind = str(kind or "").upper()
    if kind not in {"INITIALIZE", "NOTICE", "ERROR", "DEGRADED", "RECOVERY", "EXIT", "RESUME"}:
        return None
    wanted = {
        "INITIALIZE": ("Messaggio",),
        "NOTICE": ("Messaggio",),
        "ERROR": ("Dettaglio",),
        "DEGRADED": ("Dettaglio",),
        "RECOVERY": ("Recovery",),
        "EXIT": ("Uscita", "Messaggio"),
        "RESUME": ("Messaggio", "Recovery"),
    }[kind]
    for label in wanted:
        prefix = label + " "
        for cell in _dashboard_cells(text):
            stripped = cell.strip()
            if stripped.startswith(prefix):
                value = stripped[len(prefix):].strip()
                if value:
                    return "iKant: " + value
    return None


def project_primary_text(text: str, kind: str | None = None) -> str:
    """Compatibility projection from a sealed HSPv2 dashboard.

    Structured TURN output is preferred by ``wrap_prepared_frame``. This
    function remains deterministic for control frames and crash recovery, but
    presentation ASCII is no longer the source of truth for a live Surface A.
    """
    control = _control_primary(text, str(kind or ""))
    if control:
        return control
    surface = _surface_a_primary(text)
    if surface:
        return surface
    return PENDING_PRIMARY_TEXT


def _validated_explicit_primary(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.startswith("iKant: ") or text == "iKant: ":
        raise ValueError("explicit primary text must be a non-empty iKant line")
    if "\r" in text or "\x00" in text or "\x1b" in text:
        raise ValueError("explicit primary text contains forbidden control bytes")
    if len(text.encode("utf-8")) > 65536:
        raise ValueError("explicit primary text exceeds bound")
    return text


def wrap_prepared_frame(prepared: dict[str, Any], *, primary_text: str | None = None) -> dict[str, Any]:
    """Wrap one sealed dashboard plus a zero-authority primary projection.

    A validated live TURN supplies ``primary_text`` from the structured chat
    record / Surface A value. Parsing the ASCII dashboard is compatibility-only
    for control frames and recoverable historical pending frames.
    """
    text = str(prepared.get("text") or "")
    receipt = dict(prepared.get("receipt") or {})
    expected = str(receipt.get("frame_sha256") or "")
    if not text or not expected or _sha_text(text) != expected:
        raise ValueError("prepared frame text/receipt digest mismatch")
    explicit = _validated_explicit_primary(primary_text)
    if explicit is not None:
        projected = explicit
        projection_source = "STRUCTURED_SURFACE_A"
    else:
        projected = project_primary_text(text, receipt.get("kind"))
        projection_source = "SEALED_DASHBOARD_COMPAT"
    return {
        "schema": WEB_FRAME_SCHEMA,
        "text": text,
        "primary_text": projected,
        "primary_projection_source": projection_source,
        "receipt": receipt,
        "delivery_state": str(prepared.get("delivery_state") or ""),
        "acknowledged": bool(prepared.get("acknowledged", False)),
        "recovery": bool(prepared.get("recovery", False)),
        "render_contract": {
            "mode": "VERBATIM_TEXT",
            "primary_mode": "PRIMARY_WITH_PROGRESSIVE_DISCLOSURE",
            "primary_text_is_derivative": True,
            "structured_primary_preferred": True,
            "dashboard_parsing_is_compatibility_only": True,
            "details_text_must_equal_text": True,
            "details_collapsed_by_default": True,
            "canonical_frame_available_on_demand": True,
            "canonical_frame_ack_remains_exact": True,
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
