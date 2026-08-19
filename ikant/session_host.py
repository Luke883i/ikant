from __future__ import annotations
from dataclasses import asdict
from typing import Any

from .chat_session import ChatController
from .dashboard_v05 import persist_dashboard, render_dashboard_ascii
from .host_v05 import conforming_turn, emit_incarnate_surface_a
from .session_egress import (
    DashboardEgressGuard, FrameReceipt, EgressState, EgressViolation,
    activate_runtime_egress, existing_runtime_egress,
)

SESSION_HOST_SCHEMA = "ikant-dashboard-session-host/v0.10-test"


def _guard(runtime: Any) -> DashboardEgressGuard:
    return existing_runtime_egress(runtime) or activate_runtime_egress(runtime)


def _controller(runtime: Any) -> ChatController:
    return ChatController(runtime, turn_fn=conforming_turn, emit_fn=emit_incarnate_surface_a, dashboard_fn=persist_dashboard)


def prepare_text_frame(runtime: Any, frame_text: str, *, kind: str, cycle_id: str | None = None, release_after_frame: bool = False) -> dict[str, Any]:
    """Seal but do not acknowledge a human-visible frame."""
    guard = _guard(runtime)
    guard.require_locked()
    receipt = guard.seal_frame(frame_text, kind=kind, cycle_id=cycle_id, release_after_frame=release_after_frame)
    return {"schema": SESSION_HOST_SCHEMA, "text": frame_text, "receipt": asdict(receipt), "delivery_state": guard.state.value, "acknowledged": False}


def prepare_human_frame(runtime: Any, dashboard: dict[str, Any], *, kind: str, cycle_id: str | None = None, release_after_frame: bool = False, notice: str | None = None, width: int = 96) -> dict[str, Any]:
    guard = _guard(runtime)
    guard.require_locked()
    projected = guard.attach_projection(dashboard, notice=notice)
    frame = render_dashboard_ascii(projected, width=width)
    return prepare_text_frame(runtime, frame, kind=kind, cycle_id=cycle_id, release_after_frame=release_after_frame)


def acknowledge_prepared_frame(runtime: Any, prepared: dict[str, Any], actual_visible_text: str) -> dict[str, Any]:
    guard = _guard(runtime)
    receipt = FrameReceipt(**dict(prepared["receipt"]))
    if not guard.acknowledge_visible(receipt, actual_visible_text):
        raise EgressViolation("visible dashboard delivery acknowledgement failed")
    return {**prepared, "delivery_state": guard.state.value, "acknowledged": True}


def recover_prepared_frame(runtime: Any) -> dict[str, Any] | None:
    guard = _guard(runtime)
    pending = guard.pending_frame()
    if pending is None:
        return None
    receipt, text = pending
    return {"schema": SESSION_HOST_SCHEMA, "text": text, "receipt": asdict(receipt), "delivery_state": guard.state.value, "acknowledged": False, "recovery": True}


def canonical_human_frame(runtime: Any, dashboard: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Compatibility name: v0.10 prepares a frame and intentionally leaves it pending."""
    return prepare_human_frame(runtime, dashboard, **kwargs)


class DashboardOnlySession:
    """Reference adapter for ChatGPT-like hosts with explicit prepare/deliver/ack phases."""

    def __init__(self, runtime: Any):
        runtime.require_active()
        self.runtime = runtime
        self.guard = _guard(runtime)
        self.controller = _controller(runtime)

    def pending_recovery(self) -> dict[str, Any] | None:
        return recover_prepared_frame(self.runtime)

    def acknowledge(self, prepared: dict[str, Any], actual_visible_text: str) -> dict[str, Any]:
        return acknowledge_prepared_frame(self.runtime, prepared, actual_visible_text)

    def activation_frame(self, *, width: int = 96) -> dict[str, Any]:
        dash = persist_dashboard(self.runtime)
        return prepare_human_frame(self.runtime, dash, kind="INITIALIZE", notice="iKant ACTIVE. Canale umano vincolato alla dashboard.", width=width)

    def begin_user(self, intent: str, *, engine_label: str | None = None, width: int = 96, **kwargs: Any) -> dict[str, Any]:
        if self.guard.state in {EgressState.FRAME_PENDING, EgressState.RELEASE_PENDING}:
            return {"control": "RECOVER", "human": recover_prepared_frame(self.runtime)}
        self.guard.require_locked()
        if self.guard.classify_user_text(intent) == "EXIT":
            dash = persist_dashboard(self.runtime)
            return {"control": "EXIT", "human": prepare_human_frame(self.runtime, dash, kind="EXIT", release_after_frame=True, notice="Uscita da iKant confermata: dal prossimo turno risponde l'assistente locale. RESUME IKANT per rientrare se il runtime resta integro.", width=width)}
        out = self.controller.begin(intent, engine_label=engine_label, **kwargs)
        return {"control": "TURN", "machine": out}

    def finalize(self, cycle_id: str, text: str, *, intention_node_id: str | None = None, width: int = 96) -> dict[str, Any]:
        self.guard.require_locked()
        self.controller.close(cycle_id, text, intention_node_id=intention_node_id)
        dash = persist_dashboard(self.runtime, surface_a_text=text, cycle_id=cycle_id, surface_a_validated=True)
        return prepare_human_frame(self.runtime, dash, kind="TURN", cycle_id=cycle_id, width=width)

    def resume_frame(self, user_text: str, *, width: int = 96) -> dict[str, Any]:
        if user_text != "RESUME IKANT":
            raise EgressViolation("exact RESUME IKANT required outside iKant")
        integrity = self.runtime.integrity()
        self.guard.resume(runtime_integrity_ok=bool(integrity.get("ok")))
        dash = persist_dashboard(self.runtime)
        return prepare_human_frame(self.runtime, dash, kind="RESUME", notice="iKant riattivato: output umano nuovamente vincolato alla dashboard.", width=width)
