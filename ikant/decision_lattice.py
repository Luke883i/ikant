from __future__ import annotations
from typing import Any

DECISION_LATTICE_SCHEMA = "ikant-decision-lattice/v0.16-test"
_STATUS_RANK = {"PLAN_HOST_REVALIDATION_REQUIRED":0,"PLAN_HUMAN_EXECUTION_REQUIRED":1,"PLAN_REVIEW_REQUIRED":2,"PLAN_BLOCKED":3,"PLAN_PROPOSABLE":0}


def decision_vector(plan: dict[str, Any]) -> dict[str, float | int]:
    steps = plan.get("steps", [])
    caps = set(c for r in steps for c in r.get("required_capabilities", []))
    return {"governance": _STATUS_RANK.get(str(plan.get("status")),4), "irreversible": len((plan.get("rollback") or {}).get("irreversible_steps",[])), "rollback_gaps": len((plan.get("rollback") or {}).get("rollback_gap_steps",[])), "high_impact": sum(str(r.get("impact_level")) in {"HIGH","CRITICAL"} for r in steps if r.get("material")), "assumption_dependency": round(float((plan.get("counterfactual") or {}).get("max_dependency",0.0)),8), "capability_surface": len(caps), "material_steps": sum(bool(r.get("material")) for r in steps)}


def _dominates(a: dict[str, float | int], b: dict[str, float | int]) -> bool:
    keys = tuple(a)
    return all(a[k] <= b[k] for k in keys) and any(a[k] < b[k] for k in keys)


def build_decision_lattice(plans: list[dict[str, Any]]) -> dict[str, Any]:
    rows=[]; groups: dict[str,list[tuple[str,dict[str,float|int]]]]={}
    for plan in plans:
        pid=str(plan.get("plan_id"));problem=str(plan.get("decision_problem_id") or pid);vec=decision_vector(plan)
        rows.append({"plan_id":pid,"decision_problem_id":problem,"vector":vec});groups.setdefault(problem,[]).append((pid,vec))
    edges=[];nondominated=[]
    for problem,members in sorted(groups.items()):
        dominated=set()
        for aid,avec in members:
            for bid,bvec in members:
                if aid!=bid and _dominates(avec,bvec):edges.append({"decision_problem_id":problem,"dominates":aid,"dominated":bid});dominated.add(bid)
        nondominated.extend(pid for pid,_ in members if pid not in dominated)
    return {"schema":DECISION_LATTICE_SCHEMA,"plans":sorted(rows,key=lambda r:r["plan_id"]),"dominance_edges":sorted(edges,key=lambda r:(r["decision_problem_id"],r["dominates"],r["dominated"])),"nondominated_plan_ids":sorted(nondominated),"scalar_utility_used":False,"cross_problem_comparison":False,"authority":0.0}
