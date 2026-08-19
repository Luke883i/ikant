from __future__ import annotations
from typing import Any
from .plan_graph import inverse_predicate

WORLD_MODEL_SCHEMA = "ikant-counterfactual-world/v0.16-test"


def _contradictory(predicates: list[str]) -> bool:
    s = set(predicates)
    return any(inverse_predicate(p) in s for p in s)


def simulate_success_path(plan: dict[str, Any]) -> dict[str, Any]:
    """Simulate declared pre/postconditions only; this is not an observed world."""
    if not plan.get("structural_valid"):
        return {"schema": WORLD_MODEL_SCHEMA, "valid": False, "errors": ["structural invalid"], "states": [], "final_state": [], "authority": 0.0, "observed_world": False, "declared_counterfactual_only": True}
    by_id = {r["step_id"]: r for r in plan.get("steps", [])}
    state = set(plan.get("initial_conditions", []))
    errors: list[str] = []
    states = [{"after": "INITIAL", "state": sorted(state)}]
    for sid in plan.get("topological_order", []):
        step = by_id[sid]
        missing = sorted(set(step.get("preconditions", [])) - state)
        if missing:
            errors.append(f"unsatisfied precondition:{sid}:{','.join(missing)}")
            continue
        posts = list(step.get("postconditions", []))
        if _contradictory(posts):
            errors.append(f"contradictory postconditions:{sid}")
            continue
        for pred in posts:
            state.discard(inverse_predicate(pred))
            state.add(pred)
        states.append({"after": sid, "state": sorted(state)})
    return {"schema": WORLD_MODEL_SCHEMA, "valid": not errors, "errors": errors, "states": states, "final_state": sorted(state), "authority": 0.0, "observed_world": False, "declared_counterfactual_only": True}


def counterfactual_dependency(plan: dict[str, Any]) -> dict[str, Any]:
    steps = plan.get("steps", [])
    by_id = {r["step_id"]: r for r in steps}
    children = {sid: [] for sid in by_id}
    for sid, row in by_id.items():
        for dep in row.get("depends_on", []):
            if dep in children:
                children[dep].append(sid)
    assumptions = sorted(set(a for r in steps for a in r.get("assumptions", [])))
    material_ids = {r["step_id"] for r in steps if r.get("material")}
    rows = []
    for assumption in assumptions:
        directly = {r["step_id"] for r in steps if assumption in r.get("assumptions", [])}
        affected = set(directly); queue = list(directly)
        while queue:
            cur = queue.pop(0)
            for child in children.get(cur, []):
                if child not in affected:
                    affected.add(child); queue.append(child)
        affected_material = affected & material_ids
        denom = max(1, len(material_ids))
        rows.append({"assumption": assumption, "direct_steps": sorted(directly), "affected_steps": sorted(affected), "affected_material_steps": sorted(affected_material), "dependency_fraction": len(affected_material) / denom})
    max_dep = max((r["dependency_fraction"] for r in rows), default=0.0)
    return {"schema": "ikant-plan-assumption-ablation/v0.16-test", "assumptions": rows, "max_dependency": max_dep, "single_point_assumptions": sorted(r["assumption"] for r in rows if r["dependency_fraction"] >= 1.0 and material_ids), "authority": 0.0, "real_world_causality_claim": False}


def build_rollback_graph(plan: dict[str, Any]) -> dict[str, Any]:
    steps = plan.get("steps", [])
    material = [r for r in steps if r.get("material")]
    rollback_nodes = [{"rollback_id": f"rollback:{r['step_id']}", "step_id": r["step_id"], "instruction": r["rollback_plan"]} for r in material if r.get("rollback_plan")]
    rollback_ids = {r["step_id"]: r["rollback_id"] for r in rollback_nodes}
    edges = []
    for row in material:
        for dep in row.get("depends_on", []):
            if row["step_id"] in rollback_ids and dep in rollback_ids:
                edges.append({"from": rollback_ids[row["step_id"]], "to": rollback_ids[dep]})
    reversible = [r for r in material if r.get("reversibility") in {"REVERSIBLE", "PARTIAL"}]
    gaps = sorted(r["step_id"] for r in reversible if not r.get("rollback_plan"))
    irreversible = sorted(r["step_id"] for r in material if r.get("reversibility") == "IRREVERSIBLE")
    return {"schema": "ikant-rollback-graph/v0.16-test", "nodes": rollback_nodes, "edges": edges, "rollback_gap_steps": gaps, "irreversible_steps": irreversible, "coverage": (len(reversible)-len(gaps))/max(1,len(reversible)), "authority": 0.0, "rollback_instruction_is_not_proof_of_restoration": True}
