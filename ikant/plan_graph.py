from __future__ import annotations

import re
from typing import Any

PLAN_GRAPH_SCHEMA = "ikant-plan-graph/v0.16-test"
_PRED = re.compile(r"^!?[a-z0-9][a-z0-9_.:-]{0,95}$")


def normalize_predicate(value: object) -> str:
    pred = str(value).strip().casefold()
    if not _PRED.fullmatch(pred) or pred in {"!", ""}:
        raise ValueError(f"invalid predicate: {value!r}")
    return pred


def inverse_predicate(pred: str) -> str:
    pred = normalize_predicate(pred)
    return pred[1:] if pred.startswith("!") else "!" + pred


def _meta(runtime: Any, node_id: str) -> dict[str, Any]:
    node = getattr(runtime, "nodes", {}).get(node_id)
    return dict(getattr(node, "metadata", {}) or {}) if node is not None else {}


def _norm_list(values: object, *, predicates: bool = False) -> list[str]:
    out: list[str] = []
    for raw in values or []:
        value = normalize_predicate(raw) if predicates else str(raw).strip()
        if value and value not in out:
            out.append(value)
    return sorted(out)


def _topological(step_ids: list[str], deps: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    unknown = sorted({dep for sid in step_ids for dep in deps.get(sid, []) if dep not in step_ids})
    if unknown:
        return [], [f"unknown dependency:{x}" for x in unknown]
    indeg = {sid: 0 for sid in step_ids}
    children = {sid: [] for sid in step_ids}
    for sid in step_ids:
        for dep in deps.get(sid, []):
            indeg[sid] += 1
            children[dep].append(sid)
    ready = sorted(sid for sid, n in indeg.items() if n == 0)
    order: list[str] = []
    while ready:
        sid = ready.pop(0)
        order.append(sid)
        for child in sorted(children[sid]):
            indeg[child] -= 1
            if indeg[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(step_ids):
        return [], ["dependency cycle"]
    return order, []


def build_plan_graph(runtime: Any, action_ledger: dict[str, Any]) -> dict[str, Any]:
    """Build explicit plan DAGs from v0.15 action candidates.

    Multi-step ordering is never inferred. Missing plan metadata creates only a singleton
    plan for that action. Planning metadata is a zero-authority control projection.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in action_ledger.get("candidates", []) or []:
        node_id = str(candidate.get("node_id") or "")
        if not node_id:
            continue
        meta = _meta(runtime, node_id)
        plan_id = str(meta.get("plan_id") or f"singleton:{node_id}")
        step_id = str(meta.get("plan_step_id") or node_id)
        problem_id = str(meta.get("decision_problem_id") or plan_id)
        row = {
            "plan_id": plan_id,
            "decision_problem_id": problem_id,
            "step_id": step_id,
            "action_node_id": node_id,
            "material": bool(candidate.get("material", True)),
            "action_status": str((candidate.get("decision") or {}).get("status") or "UNKNOWN"),
            "required_capabilities": sorted(set(candidate.get("required_capabilities", []) or [])),
            "impact_level": str(candidate.get("impact_level") or "UNKNOWN"),
            "reversibility": str(candidate.get("reversibility") or "UNKNOWN"),
            "rollback_plan": str(candidate.get("rollback_plan") or ""),
            "depends_on": _norm_list(meta.get("plan_depends_on", [])),
            "preconditions": _norm_list(meta.get("plan_preconditions", []), predicates=True),
            "postconditions": _norm_list(meta.get("plan_postconditions", []), predicates=True),
            "initial_conditions": _norm_list(meta.get("plan_initial_conditions", []), predicates=True),
            "assumptions": _norm_list(meta.get("plan_assumptions", [])),
        }
        grouped.setdefault(plan_id, []).append(row)

    plans = []
    for plan_id in sorted(grouped):
        rows = grouped[plan_id]
        errors: list[str] = []
        ids = [r["step_id"] for r in rows]
        if len(ids) != len(set(ids)):
            errors.append("duplicate step id")
        problem_ids = sorted(set(r["decision_problem_id"] for r in rows))
        if len(problem_ids) != 1:
            errors.append("mixed decision problem")
        deps = {r["step_id"]: r["depends_on"] for r in rows}
        order, dep_errors = _topological(sorted(set(ids)), deps)
        errors.extend(dep_errors)
        initial = sorted(set(x for r in rows for x in r["initial_conditions"]))
        initial_set = set(initial)
        if any(inverse_predicate(p) in initial_set for p in initial):
            errors.append("contradictory initial conditions")
        by_id = {r["step_id"]: r for r in rows}
        plans.append({
            "schema": PLAN_GRAPH_SCHEMA,
            "plan_id": plan_id,
            "decision_problem_id": problem_ids[0] if len(problem_ids) == 1 else "",
            "step_count": len(rows),
            "material_step_count": sum(bool(r["material"]) for r in rows),
            "steps": [by_id[sid] for sid in sorted(by_id)],
            "topological_order": order,
            "initial_conditions": initial,
            "structural_valid": not errors,
            "structural_errors": sorted(set(errors)),
            "authority": 0.0,
        })
    return {
        "schema": PLAN_GRAPH_SCHEMA,
        "plans": plans,
        "plan_count": len(plans),
        "authority": 0.0,
        "boundaries": {
            "no_multi_step_order_inference": True,
            "planning_metadata_is_not_world_evidence": True,
            "plan_structure_cannot_upgrade_action_governance": True,
        },
    }
