from __future__ import annotations

import hashlib
from typing import Any

ENDUSER_SCHEMA = "ikant-enduser-self-model/v1-test"
LOCAL_IDENTITY_SCHEMA = "ikant-local-thinking-identity/v1-test"
NEUROMODEL_SCHEMA = "ikant-synthetic-neuromodel-overview/v1-test"
AUDIT_SCHEMA = "ikant-enduser-audit-trail/v1-test"
TRACE_SCHEMA = "ikant-cognitive-trace-projection/v1.3"
STAGES = (
    ("UNDERSTAND", "Capisco"),
    ("CONNECT", "Collego"),
    ("CHECK", "Verifico"),
    ("GOVERN", "Valuto"),
    ("FORMULATE", "Formulo"),
    ("INTEGRATE", "Integro"),
)


def _text(value: object, limit: int = 160) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _session_fingerprint(session_id: object) -> str | None:
    value = _text(session_id, 512)
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def local_identity_projection(*, runtime_session_id: object, state: object) -> dict[str, Any]:
    session = _text(runtime_session_id, 512)
    active = bool(session)
    return {
        "schema": LOCAL_IDENTITY_SCHEMA,
        "status": "AVAILABLE" if active else "UNAVAILABLE",
        "label": "iKant locale",
        "fingerprint": _session_fingerprint(session),
        "runtime_state": _text(state, 48) or "UNKNOWN",
        "scope": "questa istanza runtime locale",
        "runtime_session_bound": True,
        "model_relation": "componente cognitivo sostituibile; non identità",
        "memory_relation": "memoria locale verificabile della sessione; non memoria umana",
        "consciousness_claimed": False,
        "biological_identity_claimed": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def synthetic_neuromodel_projection(experience: object) -> dict[str, Any]:
    exp = experience if isinstance(experience, dict) else {}
    trace = exp.get("trace") if isinstance(exp.get("trace"), dict) else {}
    source = trace.get("stages") if isinstance(trace.get("stages"), list) else []
    by_id = {str(row.get("id")): row for row in source if isinstance(row, dict)}
    stages = []
    for sid, label in STAGES:
        row = by_id.get(sid, {})
        status = _text(row.get("status"), 24)
        if status not in {"idle", "pending", "complete"}:
            status = "unknown"
        facts = row.get("facts") if isinstance(row.get("facts"), dict) else {}
        bounded_facts = {}
        for key, value in list(facts.items())[:4]:
            if isinstance(value, (str, int, float, bool)) or value is None:
                bounded_facts[_text(key, 48)] = value if not isinstance(value, str) else _text(value, 96)
        stages.append({"id": sid, "label": label, "status": status, "facts": bounded_facts})
    trace_ok = trace.get("schema") == TRACE_SCHEMA and all(stage["status"] != "unknown" for stage in stages)
    return {
        "schema": NEUROMODEL_SCHEMA,
        "status": "AVAILABLE" if trace else "NO_CYCLE",
        "cycle_id": _text(exp.get("cycle_id"), 160) or None,
        "trace_schema_valid": trace_ok,
        "stages": stages,
        "model_kind": "SYNTHETIC_RUNTIME_MODEL",
        "private_chain_of_thought_exposed": False,
        "biological_equivalence_claimed": False,
        "consciousness_claimed": False,
        "meaning": "Schema operativo sintetico del ciclo; non lettura biologica e non prova di coscienza.",
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _last_assistant_cycle(conversation: dict[str, Any]) -> str | None:
    rows = conversation.get("records") if isinstance(conversation.get("records"), list) else []
    for row in reversed(rows):
        if isinstance(row, dict) and row.get("role") == "ikant":
            return _text(row.get("cycle_id"), 160) or None
    return None


def audit_projection(*, conversation: object, experience: object, epistemic_value: object, capabilities: object) -> dict[str, Any]:
    conv = conversation if isinstance(conversation, dict) else {}
    exp = experience if isinstance(experience, dict) else {}
    epi = epistemic_value if isinstance(epistemic_value, dict) else {}
    caps = capabilities if isinstance(capabilities, dict) else {}
    trace = exp.get("trace") if isinstance(exp.get("trace"), dict) else {}
    cycle = _text(exp.get("cycle_id"), 160) or None
    cycle_refs = {
        "experience": cycle,
        "trace": _text(trace.get("cycle_id"), 160) or None,
        "epistemic": _text(epi.get("cycle_id"), 160) or None,
        "conversation": _last_assistant_cycle(conv),
        "capabilities": _text(caps.get("cycle_id"), 160) or None,
    }
    material_refs = [value for value in cycle_refs.values() if value]
    cycle_coherent = bool(cycle) and all(value == cycle for value in material_refs)
    session_exp = _text(exp.get("runtime_session_id"), 512) or None
    session_conv = _text(conv.get("runtime_session_id"), 512) or None
    session_caps = _text(caps.get("runtime_session_id"), 512) or None
    session_refs = [value for value in (session_exp, session_conv, session_caps) if value]
    session_coherent = bool(session_exp) and all(value == session_exp for value in session_refs)
    integrity = conv.get("integrity_verified") is True
    total = conv.get("record_count")
    visible = conv.get("visible_record_count")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = len(conv.get("records") or []) if isinstance(conv.get("records"), list) else 0
    if not isinstance(visible, int) or isinstance(visible, bool) or visible < 0:
        visible = len(conv.get("records") or []) if isinstance(conv.get("records"), list) else 0
    record_counts_coherent = total >= visible
    truncated = total > visible
    trace_valid = (
        trace.get("schema") == TRACE_SCHEMA
        and trace.get("private_chain_of_thought") is False
        and trace.get("raw_model_rationale") is False
    )
    truth_boundary = epi.get("truth_certified") is False
    consistency = integrity and cycle_coherent and session_coherent and trace_valid and truth_boundary and record_counts_coherent
    timing = exp.get("timing") if isinstance(exp.get("timing"), dict) else {}
    phases = timing.get("phases") if isinstance(timing.get("phases"), list) else []
    return {
        "schema": AUDIT_SCHEMA,
        "status": "CONSISTENT" if consistency else ("NO_CYCLE" if not cycle else "DEGRADED"),
        "cycle_id": cycle,
        "cycle_refs": cycle_refs,
        "cycle_coherent": cycle_coherent,
        "session_coherent": session_coherent,
        "conversation_integrity_verified": integrity,
        "conversation_last_sha256": _text(conv.get("last_sha256"), 128) or None,
        "record_count": total,
        "visible_record_count": visible,
        "conversation_truncated": truncated,
        "record_counts_coherent": record_counts_coherent,
        "generation_route": _text(exp.get("generation_route"), 48) or None,
        "timing_phase_count": min(len(phases), 24),
        "trace_contract_valid": trace_valid,
        "truth_certified": False,
        "hash_integrity_is_not_truth": True,
        "progressive_disclosure_only": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def enduser_projection(*, conversation: object, experience: object, epistemic_value: object, capabilities: object) -> dict[str, Any]:
    exp = experience if isinstance(experience, dict) else {}
    identity = local_identity_projection(runtime_session_id=exp.get("runtime_session_id"), state=exp.get("state"))
    neuromodel = synthetic_neuromodel_projection(exp)
    audit = audit_projection(
        conversation=conversation,
        experience=exp,
        epistemic_value=epistemic_value,
        capabilities=capabilities,
    )
    return {
        "schema": ENDUSER_SCHEMA,
        "identity": identity,
        "neuromodel": neuromodel,
        "audit": audit,
        "promise": {
            "identity_is_session_bound_operational_projection": True,
            "model_is_not_identity": True,
            "neuromodel_is_synthetic_not_biological": True,
            "audit_integrity_does_not_certify_truth": True,
            "private_chain_of_thought_never_exposed": True,
            "progressive_disclosure_never_changes_authority": True,
        },
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
