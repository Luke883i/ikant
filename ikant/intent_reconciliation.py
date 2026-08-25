from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .reactive_hybrid import build_graph
from .temporal_memory import temporal_available

INTENT_ENVELOPE_SCHEMA = "ikant-intent-envelope/v1-test"
INTENT_RECONCILIATION_SCHEMA = "ikant-intent-plan-reconciliation/v1-test"
PLANNER_INPUT_SCHEMA = "ikant-intent-planner-input/v1-test"

_TOKEN = re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9_.'+-]{0,63}")
_REMINDER = re.compile(r"\b(?:ricordami|promemoria|remind\s+me|reminder)\b", re.I)
_MEMORY = re.compile(r"\b(?:ricorda\s+che|remember\s+that|memorizza|salva\s+(?:questa\s+)?(?:informazione|preferenza|memoria)|dimentica|forget)\b", re.I)
_TEMPORAL = re.compile(r"\b(?:oggi|domani|dopodomani|stasera|stanotte|today|tomorrow|tonight|alle\s+\d{1,2}(?::\d{2})?|at\s+\d{1,2}(?::\d{2})?|tra\s+\d+\s+(?:minut|or|giorn)|in\s+\d+\s+(?:minute|hour|day)|ogni\s+\w+|every\s+\w+|schedule|programma)\w*", re.I)
_MATERIAL = re.compile(r"\b(?:compra|acquista|paga|invia|manda|send|purchase|buy|pay|delete|cancella|execute|esegui|apri|open|avvia|launch|riavvia|restart|prenota|book|invita|invite|pubblica|post|carica|upload|installa|install|modifica|update|sposta|move)\w*", re.I)
_STOP = frozenset({"the","a","an","and","or","to","of","for","in","on","il","lo","la","i","gli","le","un","una","e","o","di","da","per","su","con","poi","please","per favore"})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _terms(text: object) -> set[str]:
    return {x.casefold() for x in _TOKEN.findall(str(text or "")) if len(x) > 1 and x.casefold() not in _STOP}


def _bound_to_intent(intent_terms: set[str], candidate: dict[str, Any]) -> bool:
    terms = _terms(candidate.get("text"))
    if not terms:
        return False
    overlap = len(intent_terms & terms)
    required = 1 if len(terms) <= 2 else max(1, int(math.ceil(len(terms) * 0.5)))
    return overlap >= required


def _candidate_refs(runtime: Any, candidate: dict[str, Any]) -> set[str]:
    refs = {str(x) for x in candidate.get("governing_commitment_ids", []) or [] if str(x)}
    node = getattr(runtime, "nodes", {}).get(str(candidate.get("node_id") or ""))
    meta = dict(getattr(node, "metadata", {}) or {}) if node is not None else {}
    refs.update(str(x) for x in meta.get("memory_dependency_ids", []) or [] if str(x))
    return refs


def _unavailable_refs(runtime: Any, candidates: list[dict[str, Any]]) -> list[str]:
    unavailable: set[str] = set()
    for candidate in candidates:
        for ref in _candidate_refs(runtime, candidate):
            node = getattr(runtime, "nodes", {}).get(ref)
            if node is not None and not temporal_available(node):
                unavailable.add(ref)
    return sorted(unavailable)


def build_intent_envelope(
    runtime: Any,
    cycle: dict[str, Any],
    action_ledger: dict[str, Any],
    *,
    intention_node_id: str,
) -> dict[str, Any]:
    candidates = list(action_ledger.get("candidates", []) or [])
    intention = getattr(runtime, "nodes", {}).get(str(intention_node_id or ""))
    text = str(getattr(intention, "text", "") or "") if intention is not None else ""
    classification_source = "USER_INTENTION_NODE"
    if not text:
        text = " ".join(str(x.get("text") or "") for x in candidates if str(x.get("text") or ""))
        classification_source = "ACTION_LEDGER_FALLBACK"

    graph = build_graph(text)
    semantic_nodes = list((cycle.get("semantic_slice") or {}).get("nodes", []) or [])
    semantic_kinds = sorted({str(x.get("kind") or "") for x in semantic_nodes if str(x.get("kind") or "")})
    reminder = bool(_REMINDER.search(text))
    memory_signal = bool(_MEMORY.search(text)) or "memory" in semantic_kinds
    temporal_signal = reminder or bool(_TEMPORAL.search(text))
    graph_material = any(str(x.get("authority") or "") == "MATERIAL_REVIEW_REQUIRED" for x in graph.get("units", []) or [])
    lexical_material = bool(_MATERIAL.search(text))
    fallback_material = classification_source == "ACTION_LEDGER_FALLBACK" and any(bool(x.get("material", True)) for x in candidates)
    material_signal = bool(graph_material or lexical_material or fallback_material)
    if reminder:
        # "remind me to buy" requests a reminder, not authority to perform the nested material verb.
        material_signal = False

    if material_signal:
        route_hint = "CANONICAL_PLANNER"
    elif temporal_signal:
        route_hint = "TEMPORAL_TASK_GOVERNANCE"
    elif memory_signal:
        route_hint = "MEMORY_GOVERNANCE"
    else:
        route_hint = "COGNITIVE"

    envelope = {
        "schema": INTENT_ENVELOPE_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "intent_sha256": (cycle.get("semantic_slice") or {}).get("intent_sha256"),
        "intention_node_id": str(intention_node_id or ""),
        "classification_source": classification_source,
        "work_graph_sha256": _sha(graph),
        "work_unit_count": len(graph.get("units", []) or []),
        "work_operations": sorted({str(x.get("operation") or "") for x in graph.get("units", []) or [] if str(x.get("operation") or "")}),
        "work_graph_truncated": bool(graph.get("truncated")),
        "reactive_command_present": bool(graph.get("command_plan")),
        "semantic_kinds": semantic_kinds,
        "signals": {
            "cognitive": not (material_signal or temporal_signal or memory_signal),
            "memory": memory_signal,
            "temporal": temporal_signal,
            "material": material_signal,
            "reminder": reminder,
        },
        "route_hint": route_hint,
        "reactive_graph_is_planner": False,
        "creates_plan": False,
        "creates_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    envelope["sha256"] = _sha(envelope)
    return envelope


def reconcile_intent(
    runtime: Any,
    cycle: dict[str, Any],
    action_ledger: dict[str, Any],
    *,
    temporal_core: dict[str, Any],
    intention_node_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    envelope = build_intent_envelope(runtime, cycle, action_ledger, intention_node_id=intention_node_id)
    candidates = list(action_ledger.get("candidates", []) or [])
    material = [x for x in candidates if bool(x.get("material", True))]
    intent_node = getattr(runtime, "nodes", {}).get(str(intention_node_id or ""))
    intent_text = str(getattr(intent_node, "text", "") or "") if intent_node is not None else ""
    if not intent_text:
        intent_text = " ".join(str(x.get("text") or "") for x in candidates)
    intent_terms = _terms(intent_text)
    matched = [str(x.get("node_id") or "") for x in material if _bound_to_intent(intent_terms, x) or envelope["classification_source"] == "ACTION_LEDGER_FALLBACK"]
    unmatched = [str(x.get("node_id") or "") for x in material if str(x.get("node_id") or "") not in set(matched)]
    unavailable = _unavailable_refs(runtime, candidates)
    reasons: list[str] = []

    if envelope.get("work_graph_truncated"):
        status = "BLOCK"
        reasons.append("reactive intent graph truncated")
    elif unavailable:
        status = "BLOCK"
        reasons.extend("forgotten_or_unavailable_reference:" + x for x in unavailable)
    elif envelope["signals"]["material"]:
        if not material:
            status = "BLOCK"
            reasons.append("material intent lacks canonical action candidate")
        elif unmatched:
            status = "BLOCK"
            reasons.extend("material candidate not bound to user intent:" + x for x in unmatched)
        else:
            status = "MATCH"
            reasons.append("material intent reconciled to canonical action ledger")
    elif material:
        status = "BLOCK"
        reasons.append("material action candidate present without material user-intent signal")
    else:
        status = "DEMOTE"
        reasons.append("intent remains non-material cognitive/memory/temporal work")

    planner_candidates = candidates if status == "MATCH" else []
    planner_input = {
        "schema": PLANNER_INPUT_SCHEMA,
        "source_action_ledger_sha256": action_ledger.get("sha256"),
        "intent_envelope_sha256": envelope.get("sha256"),
        "reconciliation_status": status,
        "candidate_count": len(planner_candidates),
        "candidates": planner_candidates,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
        "execution_performed": False,
    }
    planner_input["sha256"] = _sha(planner_input)

    result = {
        "schema": INTENT_RECONCILIATION_SCHEMA,
        "cycle_id": cycle.get("cycle_id"),
        "intent_envelope": envelope,
        "status": status,
        "route": envelope.get("route_hint") if status != "BLOCK" else "BLOCKED",
        "reasons": list(dict.fromkeys(reasons)),
        "matched_material_action_node_ids": sorted(x for x in matched if x),
        "unmatched_material_action_node_ids": sorted(x for x in unmatched if x),
        "unavailable_reference_node_ids": unavailable,
        "source_action_ledger_sha256": action_ledger.get("sha256"),
        "planner_input_sha256": planner_input["sha256"],
        "temporal_replay_sha256": (temporal_core.get("replay") or {}).get("sha256"),
        "planner_entrypoint": "ikant.planning.finalize_planning",
        "reactive_graph_is_planner": False,
        "reconciler_executes": False,
        "approval_created": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    result["sha256"] = _sha(result)
    return result, planner_input
