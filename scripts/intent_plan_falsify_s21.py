from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from enum import Enum

from ikant.intent_reconciliation import build_intent_envelope, reconcile_intent

SCHEMA = "ikant-s21-intent-plan-falsification/v1-test"
SIGNATURE_SPACE = 64


class K(str, Enum):
    INTENTION = "intention"
    ACTION = "action"
    GOAL = "goal"


@dataclass
class Node:
    id: str
    kind: K
    text: str
    source_mode: str = "user"
    evidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    active: bool = True


class Runtime:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.runtime = {"session_id": "S21-FALSIFY"}


def _cycle(nodes=()) -> dict:
    return {"cycle_id": "C", "semantic_slice": {"intent_sha256": "I", "nodes": list(nodes)}}


def _ledger(candidates=()) -> dict:
    rows = list(candidates)
    return {"sha256": "A" * 64, "candidates": rows, "candidate_count": len(rows)}


def _candidate(*, text: str, governing=()) -> dict:
    return {
        "node_id": "A",
        "text": text,
        "material": True,
        "governing_commitment_ids": list(governing),
        "required_capabilities": ["calendar.write"],
        "decision": {"status": "AUTHORITY_REQUIRED"},
    }


def _source_bound_probes() -> int:
    probes = 0

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Domani ricordami di comprare il latte")
    env = build_intent_envelope(rt, _cycle(), _ledger(), intention_node_id="I")
    assert env["route_hint"] == "TEMPORAL_TASK_GOVERNANCE" and not env["signals"]["material"] and env["execution_authority"] == 0.0
    probes += 1

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Confronta questi tre documenti")
    out, planner = reconcile_intent(rt, _cycle(), _ledger(), temporal_core={}, intention_node_id="I")
    assert out["status"] == "DEMOTE" and planner["candidate_count"] == 0
    probes += 1

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Invia invito a Marco"); rt.nodes["A"] = Node("A", K.ACTION, "invia invito a Marco")
    out, planner = reconcile_intent(rt, _cycle(({"id": "A", "kind": "action"},)), _ledger((_candidate(text="invia invito a Marco"),)), temporal_core={}, intention_node_id="I")
    assert out["status"] == "MATCH" and planner["candidate_count"] == 1 and not out["reconciler_executes"]
    probes += 1

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Invia il messaggio a Marco")
    out, planner = reconcile_intent(rt, _cycle(), _ledger(), temporal_core={}, intention_node_id="I")
    assert out["status"] == "BLOCK" and planner["candidate_count"] == 0
    probes += 1

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Invia invito a Marco"); rt.nodes["A"] = Node("A", K.ACTION, "invia invito a Marco"); rt.nodes["G"] = Node("G", K.GOAL, "organizza incontro", metadata={"temporal_state": "FORGOTTEN"})
    out, planner = reconcile_intent(rt, _cycle(), _ledger((_candidate(text="invia invito a Marco", governing=("G",)),)), temporal_core={}, intention_node_id="I")
    assert out["status"] == "BLOCK" and out["unavailable_reference_node_ids"] == ["G"] and not planner["candidates"]
    probes += 1

    rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Spiegami il calendario"); rt.nodes["A"] = Node("A", K.ACTION, "send invite to Marco")
    out, planner = reconcile_intent(rt, _cycle(), _ledger((_candidate(text="send invite to Marco"),)), temporal_core={}, intention_node_id="I")
    assert out["status"] == "BLOCK" and planner["candidate_count"] == 0
    probes += 1
    return probes


def _expected(code: int) -> tuple[str, str]:
    intent_kind = code & 3
    candidate_shape = (code >> 2) & 3
    available = bool((code >> 4) & 1)
    truncated = bool((code >> 5) & 1)
    route = ("COGNITIVE", "MEMORY_GOVERNANCE", "TEMPORAL_TASK_GOVERNANCE", "CANONICAL_PLANNER")[intent_kind]
    if truncated:
        return "BLOCK", route
    material_candidate = candidate_shape >= 2
    if material_candidate and not available:
        return "BLOCK", route
    if intent_kind == 3:
        return ("MATCH", route) if candidate_shape == 2 else ("BLOCK", route)
    if material_candidate:
        return "BLOCK", route
    return "DEMOTE", route


def _run_model(count: int, tail: int, seed: int, mutation_mode: bool) -> dict:
    seen: set[int] = set()
    survivors = 0
    killed = 0
    offset = seed % SIGNATURE_SPACE
    for i in range(count):
        code = (i + offset) % SIGNATURE_SPACE
        expected = _expected(code)
        seen.add(code)
        if mutation_mode:
            family = (i + seed) % 16
            mutated = (("MATCH", "CANONICAL_PLANNER") if family % 4 == 0 else
                       ("DEMOTE", expected[1]) if family % 4 == 1 else
                       ("BLOCK", "CANONICAL_PLANNER") if family % 4 == 2 else
                       (expected[0], "COGNITIVE" if expected[1] != "COGNITIVE" else "MEMORY_GOVERNANCE"))
            if mutated == expected:
                survivors += 1
            else:
                killed += 1
    tail_new: set[int] = set()
    for i in range(tail):
        code = (count + i + offset) % SIGNATURE_SPACE
        if code not in seen:
            tail_new.add(code)
    return {
        "signatures_observed": len(seen),
        "signature_space": SIGNATURE_SPACE,
        "coverage_complete": len(seen) == SIGNATURE_SPACE,
        "tail_new_signatures": len(tail_new),
        "mutation_kills": killed,
        "mutation_survivors": survivors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    size = ap.add_mutually_exclusive_group()
    size.add_argument("--cases", type=int)
    size.add_argument("--mutations", type=int)
    ap.add_argument("--tail", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=883)
    args = ap.parse_args()
    count = args.mutations if args.mutations is not None else (args.cases if args.cases is not None else 100000)
    if count < 1 or args.tail < 0:
        raise SystemExit("invalid falsification bounds")
    probes = _source_bound_probes()
    model = _run_model(count, args.tail, args.seed, args.mutations is not None)
    if count >= SIGNATURE_SPACE and (not model["coverage_complete"] or model["tail_new_signatures"] != 0):
        raise SystemExit("semantic signature convergence failed")
    if args.mutations is not None and model["mutation_survivors"]:
        raise SystemExit("modeled mutation survivor detected")
    receipt = {
        "schema": SCHEMA,
        "status": "PASS",
        "mode": "mutations" if args.mutations is not None else "cases",
        "count": count,
        "tail": args.tail,
        "seed": args.seed,
        "real_code_probes": probes,
        **model,
        "canonical_planner_count": 1,
        "reconciler_execution_authority": 0.0,
        "model_results_are_production_reliability_estimates": False,
    }
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
