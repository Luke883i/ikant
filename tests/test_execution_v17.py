import copy
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from ikant.execution_handoff import build_execution_ledger
from ikant.execution_receipts import (
    EXECUTION_RECEIPT_SCHEMA,
    REVALIDATION_RECEIPT_SCHEMA,
    record_execution_receipt,
    seal_receipt,
    validate_execution_receipt,
    validate_revalidation_receipt,
)
from ikant.execution_protocol import accept_and_reconcile, finalize_execution_protocol
from ikant.outcome_reconciliation import reconcile_execution_outcome


@dataclass
class N:
    evidence: float = .83


class R:
    def __init__(self, durable=False, root=None):
        self.nodes = {"A": N(), "B": N()}
        self.runtime = {"session_id": "S"}
        self.durable = durable
        self.state_dir = Path(root or ".")
    def _write_runtime(self):
        pass


def candidate(node="A", status="HOST_EXECUTION_ELIGIBLE", *, fingerprint="f-A", approval="ap-A"):
    return {
        "node_id": node,
        "fingerprint": fingerprint,
        "required_capabilities": ["deploy.write"],
        "decision": {
            "status": status,
            "approval": {"receipt_sha256": approval} if approval else None,
        },
    }


def fixture(*, plan_status="PLAN_HOST_REVALIDATION_REQUIRED", action_status="HOST_EXECUTION_ELIGIBLE", dependent=False, drift=False, fingerprint="f-A", approval="ap-A"):
    rt = R()
    cand = candidate("A", action_status, fingerprint=fingerprint, approval=approval)
    step_status = "APPROVAL_REQUIRED" if drift else action_status
    steps = [{
        "step_id": "a", "action_node_id": "A", "material": True,
        "action_status": step_status, "depends_on": [],
        "preconditions": ["service.ready"], "postconditions": ["service.healthy"],
    }]
    cands = [cand]
    if dependent:
        cands.append(candidate("B", action_status, fingerprint="f-B", approval="ap-B"))
        steps.append({
            "step_id": "b", "action_node_id": "B", "material": True,
            "action_status": action_status, "depends_on": ["a"],
            "preconditions": ["service.healthy"], "postconditions": ["traffic.restored"],
        })
    practical = {
        "action_ledger": {"sha256": "ACTION", "candidates": cands},
        "planning": {"plan_ledger": {"sha256": "PLAN", "plans": [{
            "plan_id": "P", "decision_problem_id": "D", "status": plan_status, "steps": steps,
        }]}},
    }
    cycle = {"cycle_id": "C", "semantic_slice": {"intent_sha256": "I"}}
    return rt, cycle, practical


def revalidation(env, **overrides):
    payload = {
        "schema": REVALIDATION_RECEIPT_SCHEMA,
        "actor_type": "host",
        "session_id": env["session_id"], "cycle_id": env["cycle_id"], "intent_sha256": env["intent_sha256"],
        "handoff_id": env["handoff_id"], "idempotency_key": env["idempotency_key"],
        "action_fingerprint": env["action_fingerprint"],
        "action_ledger_sha256": env["action_ledger_sha256"], "plan_ledger_sha256": env["plan_ledger_sha256"],
        "system_safety_law_checked": True, "tool_capability_checked": True,
        "current_action_status": "HOST_EXECUTION_ELIGIBLE",
        "grants_runtime_execution_authority": False, "executes_action": False,
    }
    payload.update(overrides)
    return seal_receipt(payload)


def receipt(env, *, outcome="EXECUTED", actor=None, observed=None, execution_ref="tool:1", **overrides):
    payload = {
        "schema": EXECUTION_RECEIPT_SCHEMA,
        "actor_type": actor or ("human" if env["handoff_kind"] == "HUMAN" else "host"),
        "session_id": env["session_id"], "cycle_id": env["cycle_id"], "intent_sha256": env["intent_sha256"],
        "handoff_id": env["handoff_id"], "idempotency_key": env["idempotency_key"],
        "action_fingerprint": env["action_fingerprint"],
        "action_ledger_sha256": env["action_ledger_sha256"], "plan_ledger_sha256": env["plan_ledger_sha256"],
        "outcome": outcome, "execution_ref": execution_ref if outcome in {"EXECUTED", "FAILED"} else "",
        "observed_predicates": observed if observed is not None else list(env["declared_postconditions"]),
        "runtime_epistemic_authority": 0.0,
        "grants_runtime_execution_authority": False,
        "causes_runtime_execution": False,
    }
    payload.update(overrides)
    return seal_receipt(payload)


class HandoffTests(unittest.TestCase):
    def test_host_handoff_requires_revalidation(self):
        rt,c,p=fixture(); e=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertEqual(e["handoff_state"],"HOST_REVALIDATION_REQUIRED"); self.assertEqual(e["handoff_kind"],"HOST"); self.assertFalse(e["execution_eligible"])
    def test_human_action_stays_human(self):
        rt,c,p=fixture(plan_status="PLAN_HUMAN_EXECUTION_REQUIRED",action_status="HUMAN_EXECUTION_REQUIRED");e=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertEqual(e["handoff_state"],"HUMAN_EXECUTION_REQUIRED");self.assertTrue(e["requires_human_execution"])
    def test_review_plan_not_handoffable(self):
        rt,c,p=fixture(plan_status="PLAN_REVIEW_REQUIRED");self.assertEqual(build_execution_ledger(rt,c,p)["handoffs"][0]["handoff_state"],"NOT_HANDOFFABLE")
    def test_block_plan_not_handoffable(self):
        rt,c,p=fixture(plan_status="PLAN_BLOCKED");self.assertEqual(build_execution_ledger(rt,c,p)["handoffs"][0]["handoff_state"],"NOT_HANDOFFABLE")
    def test_dependent_step_requires_predecessor(self):
        rt,c,p=fixture(dependent=True);e=build_execution_ledger(rt,c,p)["handoffs"][1]
        self.assertEqual(e["handoff_state"],"PREDECESSOR_RECONCILIATION_REQUIRED")
    def test_action_plan_status_drift_fails_closed(self):
        rt,c,p=fixture(drift=True);e=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertEqual(e["handoff_state"],"NOT_HANDOFFABLE");self.assertIn("plan/action status drift",e["binding_errors"])
    def test_missing_fingerprint_fails_closed(self):
        rt,c,p=fixture(fingerprint="");e=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertIn("action fingerprint missing",e["binding_errors"])
    def test_missing_approval_binding_fails_closed(self):
        rt,c,p=fixture(approval="");e=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertIn("approval receipt binding missing",e["binding_errors"])
    def test_idempotency_is_deterministic(self):
        rt,c,p=fixture();a=build_execution_ledger(rt,c,p)["handoffs"][0];b=build_execution_ledger(rt,c,p)["handoffs"][0]
        self.assertEqual(a["idempotency_key"],b["idempotency_key"]);self.assertEqual(a["handoff_id"],b["handoff_id"])
    def test_evidence_unchanged(self):
        rt,c,p=fixture();before={k:v.evidence for k,v in rt.nodes.items()};build_execution_ledger(rt,c,p);self.assertEqual(before,{k:v.evidence for k,v in rt.nodes.items()})
    def test_durable_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            rt,c,p=fixture();rt.durable=True;rt.state_dir=Path(td);build_execution_ledger(rt,c,p);self.assertTrue((Path(td)/"execution-ledger.json").exists())


class ReceiptTests(unittest.TestCase):
    def env(self, **kwargs):
        rt,c,p=fixture(**kwargs);return rt,build_execution_ledger(rt,c,p)["handoffs"][0]
    def test_valid_revalidation(self):
        _,e=self.env();self.assertTrue(validate_revalidation_receipt(e,revalidation(e))[0])
    def test_revalidation_binding_drift_rejected(self):
        _,e=self.env();self.assertFalse(validate_revalidation_receipt(e,revalidation(e,cycle_id="OLD"))[0])
    def test_revalidation_requires_safety_law(self):
        _,e=self.env();self.assertFalse(validate_revalidation_receipt(e,revalidation(e,system_safety_law_checked=False))[0])
    def test_revalidation_requires_tool_capability(self):
        _,e=self.env();self.assertFalse(validate_revalidation_receipt(e,revalidation(e,tool_capability_checked=False))[0])
    def test_host_execution_requires_revalidation(self):
        _,e=self.env();self.assertFalse(validate_execution_receipt(e,receipt(e),revalidation_receipt=None)[0])
    def test_valid_host_execution_receipt(self):
        _,e=self.env();self.assertTrue(validate_execution_receipt(e,receipt(e),revalidation_receipt=revalidation(e))[0])
    def test_human_receipt_must_be_human(self):
        _,e=self.env(plan_status="PLAN_HUMAN_EXECUTION_REQUIRED",action_status="HUMAN_EXECUTION_REQUIRED");self.assertFalse(validate_execution_receipt(e,receipt(e,actor="host"))[0])
    def test_dependent_step_cannot_report_execution(self):
        rt,c,p=fixture(dependent=True);e=build_execution_ledger(rt,c,p)["handoffs"][1]
        self.assertFalse(validate_execution_receipt(e,receipt(e),revalidation_receipt=revalidation(e))[0])
    def test_execution_reference_required(self):
        _,e=self.env();self.assertFalse(validate_execution_receipt(e,receipt(e,execution_ref=""),revalidation_receipt=revalidation(e))[0])
    def test_invalid_observed_predicate_rejected(self):
        _,e=self.env();self.assertFalse(validate_execution_receipt(e,receipt(e,observed=["*"]),revalidation_receipt=revalidation(e))[0])
    def test_authority_escalation_rejected(self):
        _,e=self.env();self.assertFalse(validate_execution_receipt(e,receipt(e,grants_runtime_execution_authority=True),revalidation_receipt=revalidation(e))[0])
    def test_idempotent_replay(self):
        rt,e=self.env();r=receipt(e);rv=revalidation(e);self.assertEqual(record_execution_receipt(rt,e,r,revalidation_receipt=rv)["status"],"RECORDED");self.assertEqual(record_execution_receipt(rt,e,r,revalidation_receipt=rv)["status"],"IDEMPOTENT_REPLAY")
    def test_conflicting_replay_fails_closed(self):
        rt,e=self.env();rv=revalidation(e);r1=receipt(e,execution_ref="tool:1");r2=receipt(e,execution_ref="tool:2");record_execution_receipt(rt,e,r1,revalidation_receipt=rv);self.assertEqual(record_execution_receipt(rt,e,r2,revalidation_receipt=rv)["status"],"RECEIPT_CONFLICT")
    def test_durable_receipt_registry(self):
        with tempfile.TemporaryDirectory() as td:
            rt,e=self.env();rt.durable=True;rt.state_dir=Path(td);record_execution_receipt(rt,e,receipt(e),revalidation_receipt=revalidation(e));self.assertTrue((Path(td)/"execution-receipts.json").exists())


class ReconciliationTests(unittest.TestCase):
    def env(self):
        rt,c,p=fixture();return build_execution_ledger(rt,c,p)["handoffs"][0]
    def test_reported_postconditions(self):
        e=self.env();x=reconcile_execution_outcome(e,receipt(e));self.assertEqual(x["status"],"POSTCONDITIONS_REPORTED")
    def test_conflict_is_explicit(self):
        e=self.env();x=reconcile_execution_outcome(e,receipt(e,observed=["!service.healthy"]));self.assertEqual(x["status"],"POSTCONDITION_CONFLICT")
    def test_partial_is_not_confirmation(self):
        e=self.env();e=copy.deepcopy(e);e["declared_postconditions"]=["service.healthy","traffic.restored"];x=reconcile_execution_outcome(e,receipt(e,observed=["service.healthy"]));self.assertEqual(x["status"],"POSTCONDITIONS_PARTIAL")
    def test_no_observation_requires_observation(self):
        e=self.env();self.assertEqual(reconcile_execution_outcome(e,receipt(e,observed=[]))["status"],"OBSERVATION_REQUIRED")
    def test_failed_not_success(self):
        e=self.env();self.assertEqual(reconcile_execution_outcome(e,receipt(e,outcome="FAILED"))["status"],"EXECUTION_FAILED")
    def test_declined_not_success(self):
        e=self.env();self.assertEqual(reconcile_execution_outcome(e,receipt(e,outcome="DECLINED"))["status"],"EXECUTION_DECLINED")
    def test_semantic_opposite_not_inferred(self):
        e=self.env();x=reconcile_execution_outcome(e,receipt(e,observed=["service.failed"]));self.assertEqual(x["status"],"OBSERVATION_REQUIRED");self.assertEqual(x["reported_conflicts"],[])
    def test_no_auto_advance_and_zero_authority(self):
        e=self.env();x=reconcile_execution_outcome(e,receipt(e));self.assertFalse(x["next_step_auto_advance"]);self.assertEqual(x["epistemic_authority"],0.0);self.assertFalse(x["observed_world_verified"])


class ProtocolTests(unittest.TestCase):
    def test_finalize_never_executes(self):
        rt,c,p=fixture();x=finalize_execution_protocol(rt,c,p);self.assertFalse(x["runtime_execution_performed"]);self.assertEqual(x["execution_authority"],0.0)
    def test_receipt_digest_is_not_actor_authentication(self):
        rt,c,p=fixture();x=finalize_execution_protocol(rt,c,p);self.assertTrue(x["boundaries"]["receipt_digest_is_integrity_not_actor_authentication"]);self.assertTrue(x["boundaries"]["host_transport_authentication_is_external"])
    def test_accept_and_reconcile(self):
        rt,c,p=fixture();e=build_execution_ledger(rt,c,p)["handoffs"][0];x=accept_and_reconcile(rt,e,receipt(e),revalidation_receipt=revalidation(e));self.assertEqual(x["recording"]["status"],"RECORDED");self.assertEqual(x["reconciliation"]["status"],"POSTCONDITIONS_REPORTED");self.assertFalse(x["runtime_execution_performed"])


if __name__ == "__main__":
    unittest.main()
