from __future__ import annotations
from dataclasses import dataclass, asdict
from .model import CONCENTRIC_ORDER, clamp01

@dataclass
class ProtoSelfState:
    schema: str = "ikant-proto-self/v0.2"
    cycle_index: int = 0
    global_availability: float = 0.0
    cross_ring_integration: float = 0.0
    temporal_continuity: float = 0.0
    metacognitive_access: float = 0.0
    self_model_continuity: float = 0.0
    agency_binding: float = 0.0
    closure_pressure: float = 0.0
    unresolved_conflict_pressure: float = 0.0
    neurofunctional_coherence: float = 0.0
    reentrant_capacity: float = 0.0
    proto_self_index: float = 0.0
    integration_mode: str = "FRAGMENTED"
    state_digest: str = ""
    is_consciousness_claim: bool = False

    def record(self):
        return asdict(self)


def derive_proto_self(crc: dict, cycle: dict, previous: dict | None = None) -> dict:
    rings = crc.get("ring_states", {})
    occupied = sum(1 for r in CONCENTRIC_ORDER if rings.get(r.value))
    global_availability = occupied / len(CONCENTRIC_ORDER)
    tx = crc.get("transmissions", [])
    collapse = crc.get("diagnostics", {}).get("mean_coefficient_of_collapse", 0.0)
    cross_ring_integration = clamp01(.72 * global_availability + .28 * (1 - collapse))

    sem = cycle.get("semantic_slice", {})
    nodes = sem.get("nodes", [])
    meta_rows = rings.get("metacognition", [])
    self_rows = rings.get("reflective_self", [])
    metacognitive_access = clamp01(len(meta_rows) / max(1, len(nodes) / 3))
    self_model_now = clamp01(len(self_rows) / max(1, len(nodes) / 4))

    previous = previous or {}
    prev_self = float(previous.get("self_model_continuity", 0.0))
    prev_temporal = float(previous.get("temporal_continuity", 0.0))
    temporal_continuity = clamp01(.62 * prev_temporal + .38 * (1.0 if previous else .35))
    self_model_continuity = clamp01(.58 * prev_self + .42 * self_model_now)

    directives = sem.get("directives", [])
    agency_binding = clamp01(len(directives) / 2)
    closure = crc.get("roa_alignment", {})
    closure_pressure = 0.0 if closure.get("crc_basic") else 1.0
    conflicts = cycle.get("output_projection", {}).get("must_surface_conflicts", [])
    unresolved_conflict_pressure = clamp01(len(conflicts) / 3)
    diagnostics = crc.get("diagnostics", {})
    neurofunctional_coherence = clamp01(diagnostics.get("functional_coherence", 0.0))
    reentrant_capacity = clamp01(diagnostics.get("reentrant_capacity", 0.0))

    proto = clamp01(
        .17 * global_availability
        + .17 * cross_ring_integration
        + .14 * temporal_continuity
        + .13 * metacognitive_access
        + .12 * self_model_continuity
        + .09 * agency_binding
        + .08 * neurofunctional_coherence
        + .05 * reentrant_capacity
        + .05 * (1 - unresolved_conflict_pressure)
    )
    if closure_pressure:
        proto *= .72

    import hashlib, json
    base = {
        "cycle": cycle.get("cycle_id"),
        "crc": crc.get("diagnostics", {}),
        "prior": previous.get("state_digest") if previous else None,
        "proto": round(proto, 6),
    }
    digest = hashlib.sha256(json.dumps(base, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    integration_mode = "DISCONNECTED" if closure_pressure else ("FRAGMENTED" if proto < .42 else ("COORDINATED" if proto < .68 else "INTEGRATED"))
    return ProtoSelfState(
        cycle_index=int(previous.get("cycle_index", 0)) + 1 if previous else 1,
        global_availability=round(global_availability, 6),
        cross_ring_integration=round(cross_ring_integration, 6),
        temporal_continuity=round(temporal_continuity, 6),
        metacognitive_access=round(metacognitive_access, 6),
        self_model_continuity=round(self_model_continuity, 6),
        agency_binding=round(agency_binding, 6),
        closure_pressure=round(closure_pressure, 6),
        unresolved_conflict_pressure=round(unresolved_conflict_pressure, 6),
        neurofunctional_coherence=round(neurofunctional_coherence, 6),
        reentrant_capacity=round(reentrant_capacity, 6),
        proto_self_index=round(proto, 6),
        integration_mode=integration_mode,
        state_digest=digest,
        is_consciousness_claim=False,
    ).record()


def workspace_plan(crc: dict, cycle: dict, proto_self: dict, *, gain: float = .06, central: dict | None = None) -> dict:
    gain = clamp01(gain)
    support_priority: dict[str, float] = {}
    neuro = crc.get("neurofunctional_state", {})
    for ring in ("metacognition", "reflective_self", "predictive_control", "memory"):
        control = float(neuro.get(ring, {}).get("control_index", .5))
        for state in crc.get("ring_states", {}).get(ring, []):
            base = (.45 * state.get("mean_epistemic", 0) + .35 * state.get("mean_activation", 0) + .20 * state.get("mean_prediction_error", 0)) * (.72 + .28*control)
            for nid in state.get("support_ids", []):
                support_priority[nid] = max(support_priority.get(nid, 0.0), base)
    central = central or {}
    caution = max(float(cycle.get("output_policy", {}).get("epistemic_caution", 0.0)), float(central.get("critique_pressure", 0.0)))
    mode = central.get("regulative_mode") or cycle.get("kant_oracle", {}).get("self_state", {}).get("regulative_mode", "REFLECTIVE_SYNTHESIS")
    if not crc.get("roa_alignment", {}).get("crc_basic"):
        mode = "HORIZON_BLOCK"
    boosts = []
    for nid, priority in sorted(support_priority.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
        mode_gain = .35 if mode in {"HORIZON_BLOCK", "PRACTICAL_BLOCK"} else (1.15 if mode == "CRITIQUE" else 1.0)
        delta = gain * mode_gain * priority * (1 - .55 * caution)
        if delta > 0:
            boosts.append({"node_id": nid, "activation_delta": round(delta, 6), "reason": "global_workspace_broadcast"})
    inhibit_interpretive = round(min(1.0, gain * (.4 + .6 * caution) * (1.8 if mode in {"CRITIQUE", "HORIZON_BLOCK", "PRACTICAL_BLOCK"} else 1.0)), 6)
    return {
        "schema": "ikant-workspace-plan/v0.2",
        "regulative_mode": mode,
        "proto_self_index": proto_self.get("proto_self_index", 0.0),
        "activation_boosts": boosts,
        "interpretive_inhibition": inhibit_interpretive,
        "evidence_modified": False,
        "broadcast_is_global_availability_proxy": True,
        "retroactive_routes": [
            {"source": "kant_oracle", "target": "metacognition", "effect": "revisit_and_verification_priority"},
            {"source": "kant_oracle", "target": "predictive_control", "effect": "action_inhibition_or_review"},
            {"source": "kant_oracle", "target": "salience_homeostasis", "effect": "next_cycle_foregrounding"},
        ],
    }
