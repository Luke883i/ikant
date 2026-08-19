from __future__ import annotations
from dataclasses import asdict
from typing import Any

from .chat_session import ChatController
from .dashboard_v05 import persist_dashboard, render_dashboard_ascii
from .host_v05 import conforming_turn, emit_incarnate_surface_a
from .session_egress import (
    DashboardEgressGuard,
    activate_runtime_egress,
    existing_runtime_egress,
)

SESSION_HOST_SCHEMA = "ikant-dashboard-session-host/v0.9-test"


def _guard(runtime: Any) -> DashboardEgressGuard:
    return existing_runtime_egress(runtime) or activate_runtime_egress(runtime)


def _controller(runtime: Any) -> ChatController:
    return ChatController(
        runtime,
        turn_fn=conforming_turn,
        emit_fn=emit_incarnate_surface_a,
        dashboard_fn=persist_dashboard,
    )


def canonical_human_frame(
    runtime: Any,
    dashboard: dict[str, Any],
    *,
    kind: str,
    cycle_id: str | None = None,
    release_after_frame: bool = False,
    notice: str | None = None,
    width: int = 96,
) -> dict[str, Any]:
    """Return the only string a conforming host may use as assistant-visible content."""
    guard = _guard(runtime)
    guard.require_locked()
    projected = guard.attach_projection(dashboard, notice=notice)
    frame = render_dashboard_ascii(projected, width=width)
    receipt = guard.seal_frame(frame, kind=kind, cycle_id=cycle_id, release_after_frame=release_after_frame)
    if not guard.acknowledge_visible(receipt, frame):
        raise RuntimeError("sealed dashboard frame failed candidate validation")
    return {"schema": SESSION_HOST_SCHEMA, "text": frame, "receipt": asdict(receipt)}


class DashboardOnlySession:
    """Reference adapter for ChatGPT-like hosts.

    Machine dictionaries never belong on the human-visible channel. A conforming host
    sets the entire assistant message body to the returned `human.text`, with no prefix,
    suffix, markdown wrapper, citation block, tool summary or other prose.
    """

    def __init__(self, runtime: Any):
        runtime.require_active()
        self.runtime = runtime
        self.guard = _guard(runtime)
        self.controller = _controller(runtime)

    def activation_frame(self, *, width: int = 96) -> dict[str, Any]:
        dash = persist_dashboard(self.runtime)
        return canonical_human_frame(self.runtime, dash, kind="INITIALIZE", notice="iKant ACTIVE. Canale umano vincolato alla dashboard.", width=width)

    def begin_user(self, intent: str, *, engine_label: str | None = None, width: int = 96, **kwargs: Any) -> dict[str, Any]:
        self.guard.require_locked()
        if self.guard.classify_user_text(intent) == "EXIT":
            dash = persist_dashboard(self.runtime)
            return {
                "control": "EXIT",
                "human": canonical_human_frame(
                    self.runtime,
                    dash,
                    kind="EXIT",
                    release_after_frame=True,
                    notice="Uscita da iKant confermata: dal prossimo turno risponde l'assistente locale. RESUME IKANT per rientrare se il runtime resta integro.",
                    width=width,
                ),
            }
        out = self.controller.begin(intent, engine_label=engine_label, **kwargs)
        return {"control": "TURN", "machine": out}

    def finalize(self, cycle_id: str, text: str, *, intention_node_id: str | None = None, width: int = 96) -> dict[str, Any]:
        self.guard.require_locked()
        self.controller.close(cycle_id, text, intention_node_id=intention_node_id)
        dash = persist_dashboard(self.runtime, surface_a_text=text, cycle_id=cycle_id, surface_a_validated=True)
        return canonical_human_frame(self.runtime, dash, kind="TURN", cycle_id=cycle_id, width=width)
