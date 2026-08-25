from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from .plan_graph import build_plan_graph
from .world_model import simulate_success_path,counterfactual_dependency,build_rollback_graph
from .decision_lattice import build_decision_lattice

PLANNING_SCHEMA="ikant-planning/v0.16-test"
PLAN_LEDGER_SCHEMA="ikant-plan-ledger/v0.16-test"
_GOOD={"HOST_EXECUTION_ELIGIBLE"};_HUMAN={"HUMAN_EXECUTION_REQUIRED"};_BLOCK={"CENTRAL_BLOCKED"}


def _status(plan:dict[str,Any],world:dict[str,Any])->str:
    material=[r for r in plan.get("steps",[]) if r.get("material")];statuses=[r.get("action_status") for r in material]
    if any(s in _BLOCK for s in statuses):return "PLAN_BLOCKED"
    if not plan.get("structural_valid") or not world.get("valid"):return "PLAN_REVIEW_REQUIRED"
    if not material:return "PLAN_PROPOSABLE"
    if any(s not in _GOOD|_HUMAN for s in statuses):return "PLAN_REVIEW_REQUIRED"
    if any(s in _HUMAN for s in statuses):return "PLAN_HUMAN_EXECUTION_REQUIRED"
    if all(s in _GOOD for s in statuses):return "PLAN_HOST_REVALIDATION_REQUIRED"
    return "PLAN_REVIEW_REQUIRED"


def finalize_planning(runtime:Any,cycle:dict[str,Any],practical:dict[str,Any],*,central:dict[str,Any],planner_action_ledger:dict[str,Any]|None=None,intent_reconciliation:dict[str,Any]|None=None)->dict[str,Any]:
    before={nid:float(getattr(node,"evidence",0.0)) for nid,node in getattr(runtime,"nodes",{}).items()}
    source=planner_action_ledger if planner_action_ledger is not None else practical.get("action_ledger",{})
    graph=build_plan_graph(runtime,source);plans=[]
    for raw in graph.get("plans",[]):
        world=simulate_success_path(raw);cf=counterfactual_dependency(raw);rollback=build_rollback_graph(raw)
        plan={**raw,"world":world,"counterfactual":cf,"rollback":rollback};plan["status"]=_status(plan,world);plan["host_revalidation_required"]=plan["status"]=="PLAN_HOST_REVALIDATION_REQUIRED";plan["execution_eligible"]=False;plan["execution_performed"]=False;plans.append(plan)
    lattice=build_decision_lattice(plans)
    after={nid:float(getattr(node,"evidence",0.0)) for nid,node in getattr(runtime,"nodes",{}).items()}
    if before!=after:raise RuntimeError("planning modified evidence")
    statuses=[p["status"] for p in plans];overall="NONE"
    if "PLAN_BLOCKED" in statuses:overall="PLAN_BLOCKED"
    elif "PLAN_REVIEW_REQUIRED" in statuses:overall="PLAN_REVIEW_REQUIRED"
    elif "PLAN_HUMAN_EXECUTION_REQUIRED" in statuses:overall="PLAN_HUMAN_EXECUTION_REQUIRED"
    elif "PLAN_HOST_REVALIDATION_REQUIRED" in statuses:overall="PLAN_HOST_REVALIDATION_REQUIRED"
    elif "PLAN_PROPOSABLE" in statuses:overall="PLAN_PROPOSABLE"
    reconciliation_status=str((intent_reconciliation or {}).get("status") or "")
    if reconciliation_status=="BLOCK":overall="PLAN_BLOCKED"
    ledger={"schema":PLAN_LEDGER_SCHEMA,"cycle_id":cycle.get("cycle_id"),"intent_sha256":(cycle.get("semantic_slice") or {}).get("intent_sha256"),"source_action_ledger_sha256":(practical.get("action_ledger") or {}).get("sha256"),"planner_input_sha256":(intent_reconciliation or {}).get("planner_input_sha256"),"intent_reconciliation_sha256":(intent_reconciliation or {}).get("sha256"),"intent_reconciliation_status":reconciliation_status or None,"canonical_planner_entrypoint":"ikant.planning.finalize_planning","reactive_graph_is_planner":False,"plan_count":len(plans),"plans":plans,"decision_lattice":lattice,"overall_status":overall,"epistemic_authority":0.0,"execution_authority":0.0,"execution_performed":False,"approval_reusable_across_steps_or_turns":False,"boundaries":{"action_governance_cannot_be_upgraded":True,"intent_reconciliation_can_only_preserve_or_downgrade":True,"same_turn_approval_is_not_plan_execution_token":True,"symbolic_world_is_not_observed_world":True,"counterfactual_sensitivity_is_not_real_world_causality":True,"pareto_lattice_has_no_scalar_utility":True,"host_revalidates_each_material_step":True}}
    raw=json.dumps(ledger,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8");ledger["sha256"]=hashlib.sha256(raw).hexdigest()
    if getattr(runtime,"durable",False):
        from .store import atomic_json_write
        path=Path(runtime.state_dir)/"plan-ledger.json";atomic_json_write(path,ledger);ledger["path"]=str(path)
    state=getattr(runtime,"runtime",{}).setdefault("planning",{});state["last"]={"schema":PLANNING_SCHEMA,"cycle_id":cycle.get("cycle_id"),"plan_ledger_sha256":ledger["sha256"],"overall_status":overall,"intent_reconciliation_status":reconciliation_status or None,"nondominated_plan_ids":lattice.get("nondominated_plan_ids",[]),"authority":0.0}
    if hasattr(runtime,"_write_runtime"):runtime._write_runtime()
    return {"schema":PLANNING_SCHEMA,"plan_graph_schema":graph.get("schema"),"plan_ledger":ledger,"overall_status":overall,"boundaries":ledger["boundaries"]}
