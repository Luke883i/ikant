from __future__ import annotations

from copy import deepcopy
import threading
from pathlib import Path
from typing import Any

from .advanced_web_shell import AdvancedWebShellError, AdvancedWebShellService
from .local_service import LOCAL_APP_SCHEMA, LocalAppError
from .managed_runtime import ManagedLocalRuntime, ManagedRuntimeError
from .voice_input import LocalVoiceInputBroker

PRODUCT_EXPERIENCE_SCHEMA = "ikant-product-experience/v0.27-test"
PRODUCT_VOICE_SCHEMA = "ikant-product-voice-candidate/v0.27-test"
_SETUP_PHASES = frozenset({"STARTING", "PLAN", "DOWNLOADING", "VERIFIED", "PREPARING", "READY", "BLOCKED", "STOPPED"})


def _safe_progress(event: Any) -> dict[str, Any]:
    src = event if isinstance(event, dict) else {}
    phase = str(src.get("phase") or "PREPARING").upper()
    if phase not in _SETUP_PHASES:
        phase = "PREPARING"
    target = str(src.get("target") or "local runtime")[:160]
    raw_bytes = src.get("bytes")
    size = int(raw_bytes) if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes >= 0 else 0
    return {"phase": phase, "target": target, "bytes": size}


class ProductExperienceService(AdvancedWebShellService):
    """S9 ACTIVE service: S8 remains the writer; voice remains an input candidate only."""

    def shell_voice_candidate(self, shell_id: object, client_id: object, audio: bytes, content_type: str) -> dict[str, Any]:
        self.require_web_conformance()
        session = self._active_session_id()
        # Reuse the exact S8 writer/session binding without advancing semantic operation sequence.
        with self.web_shell._lock:  # package-internal S9 adapter over the S8 control kernel
            self.web_shell._require_bound(session, shell_id, client_id)
            if self.web_shell._pending is not None:
                raise AdvancedWebShellError("voice capture unavailable while a sealed frame awaits exact ACK")
        transcript = self.transcribe(audio, content_type)
        text = str(transcript.get("text") or "").strip()
        if not text:
            raise LocalAppError("voice transcript missing")
        return {
            "schema": PRODUCT_VOICE_SCHEMA,
            "text": text,
            "source": "loopback_stt",
            "writer_bound": True,
            "auto_submit": False,
            "may_approve_capability_or_action": False,
            "authority_effect": "NONE",
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }


class ProductBootstrapCoordinator:
    """Opens the local product before the model is ready and owns setup/retry lifecycle.

    Browser-visible progress is a redacted control projection. It cannot make the runtime READY,
    issue authority, or bypass the existing admission/probe/initialize path.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        runtime: ManagedLocalRuntime,
        voice_endpoint: str | None,
        readiness_timeout: float = 45.0,
    ) -> None:
        self.root = Path(root).resolve()
        self.runtime = runtime
        self.voice_endpoint = str(voice_endpoint or "") or None
        self.readiness_timeout = float(readiness_timeout)
        self._lock = threading.RLock()
        self._delegate: ProductExperienceService | None = None
        self._web_adapter = None
        self._thread: threading.Thread | None = None
        self._stage = "STARTING"
        self._progress = {"phase": "STARTING", "target": "iKant local runtime", "bytes": 0}
        self._planned_bytes = 0
        self._attempt = 0
        self._error_code: str | None = None
        self._stopping = False

    @property
    def state_dir(self) -> Path:
        return self.root / ".ikant"

    def bind_web_adapter(self, adapter) -> None:
        with self._lock:
            self._web_adapter = adapter
            delegate = self._delegate
        if delegate is not None:
            delegate.bind_web_adapter(adapter)

    def start_async(self) -> dict[str, Any]:
        with self._lock:
            if self._stopping:
                raise LocalAppError("product runtime is stopping")
            if self._delegate is not None:
                return self.product_status()
            if self._thread is not None and self._thread.is_alive():
                return self.product_status()
            self._attempt += 1
            self._stage = "PREPARING"
            self._progress = {"phase": "PREPARING", "target": "verified local runtime", "bytes": 0}
            self._planned_bytes = 0
            self._error_code = None
            t = threading.Thread(target=self._prepare, name="ikant-product-bootstrap", daemon=True)
            self._thread = t
            t.start()
        return self.product_status()

    def _on_progress(self, event: Any) -> None:
        progress = _safe_progress(event)
        with self._lock:
            if progress["phase"] == "PLAN":
                self._planned_bytes = max(self._planned_bytes, int(progress["bytes"]))
            self._progress = progress
            if progress["phase"] in {"PLAN", "DOWNLOADING", "VERIFIED", "PREPARING"}:
                self._stage = "PREPARING"

    def _prepare(self) -> None:
        try:
            model = self.runtime.start(progress=self._on_progress, readiness_timeout=self.readiness_timeout)
            voice = LocalVoiceInputBroker(self.voice_endpoint)
            delegate = ProductExperienceService(self.root, model=model, voice=voice)
            with self._lock:
                adapter = self._web_adapter
            if adapter is not None:
                delegate.bind_web_adapter(adapter)
            with self._lock:
                if self._stopping:
                    raise ManagedRuntimeError("product runtime stopping")
                self._delegate = delegate
                self._stage = "READY"
                self._progress = {"phase": "READY", "target": "verified local runtime", "bytes": max(self._planned_bytes, int(self._progress.get("bytes") or 0))}
                self._error_code = None
        except Exception as exc:
            with self._lock:
                self._delegate = None
                self._stage = "BLOCKED"
                self._error_code = type(exc).__name__
                self._progress = {"phase": "BLOCKED", "target": "verified local runtime", "bytes": int(self._progress.get("bytes") or 0)}

    def retry_setup(self) -> dict[str, Any]:
        with self._lock:
            if self._stage != "BLOCKED" or (self._thread is not None and self._thread.is_alive()):
                raise LocalAppError("setup retry requires a blocked, idle runtime")
        self.runtime.stop(persist=False)
        return self.start_async()

    def stop(self) -> None:
        with self._lock:
            self._stopping = True
            self._stage = "STOPPED"
            self._delegate = None
        self.runtime.stop()

    def _delegate_or_raise(self) -> ProductExperienceService:
        with self._lock:
            delegate = self._delegate
        if delegate is None:
            raise LocalAppError("verified local runtime is still preparing")
        return delegate

    def product_status(self) -> dict[str, Any]:
        with self._lock:
            stage = self._stage
            progress = deepcopy(self._progress)
            planned = self._planned_bytes
            attempt = self._attempt
            error_code = self._error_code
            delegate = self._delegate
        current = int(progress.get("bytes") or 0)
        fraction = None
        if planned > 0:
            fraction = max(0.0, min(1.0, current / planned))
        voice = delegate.voice.status() if delegate is not None else {
            "configured": bool(self.voice_endpoint),
            "endpoint_scope": "LOOPBACK_ONLY" if self.voice_endpoint else "DISABLED",
            "voice_is_input_only": True,
            "voice_can_approve_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        return {
            "schema": PRODUCT_EXPERIENCE_SCHEMA,
            "stage": stage,
            "runtime_ready": delegate is not None and stage == "READY",
            "attempt": attempt,
            "progress": {**progress, "planned_bytes": planned or None, "fraction": fraction},
            "diagnostics": {
                "error_code": error_code,
                "retry_available": stage == "BLOCKED",
                "component_presence_is_authority": False,
                "runtime_readiness_is_authority": False,
                "browser_may_mark_ready": False,
                "browser_model_transport": False,
            },
            "voice": voice,
            "experience": {
                "primary_surface": "CHAT_WITH_ONE_HSPV2_SEALED_VIEWPORT",
                "progressive_disclosure": True,
                "traditional_controls_on_demand": True,
                "command_palette": True,
                "epistemic_inspector_default_open": False,
                "voice_input_auto_submit": False,
                "voice_output_source": "POST_ACK_SEALED_SURFACE_A_ONLY",
                "voice_output_local_service_required": True,
            },
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }

    def shell_claimed(self) -> bool:
        with self._lock:
            return bool(self._delegate and self._delegate.shell_claimed())

    # Legacy/S8 service surface delegates only after verified runtime readiness.
    def lifecycle(self): return self._delegate_or_raise().lifecycle()
    def admission_view(self): return self._delegate_or_raise().admission_view()
    def accept(self, phrase, digest): return self._delegate_or_raise().accept(phrase, digest)
    def probe(self): return self._delegate_or_raise().probe()
    def initialize(self): return self._delegate_or_raise().initialize()
    def frame(self): return self._delegate_or_raise().frame()
    def acknowledge(self, ack): return self._delegate_or_raise().acknowledge(ack)
    def turn(self, text): return self._delegate_or_raise().turn(text)
    def notice(self, message, *, kind="LOCAL_WEB_NOTICE"): return self._delegate_or_raise().notice(message, kind=kind)
    def resume(self, text): return self._delegate_or_raise().resume(text)
    def transcribe(self, audio, content_type): return self._delegate_or_raise().transcribe(audio, content_type)
    def shell_open(self, client_id): return self._delegate_or_raise().shell_open(client_id)
    def shell_command(self, command): return self._delegate_or_raise().shell_command(command)
    def shell_ack(self, envelope): return self._delegate_or_raise().shell_ack(envelope)
    def shell_voice_candidate(self, shell_id, client_id, audio, content_type):
        return self._delegate_or_raise().shell_voice_candidate(shell_id, client_id, audio, content_type)
