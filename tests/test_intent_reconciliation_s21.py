from __future__ import annotations

import subprocess
import sys
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ikant.intent_reconciliation import build_intent_envelope, reconcile_intent


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
    def __init__(self):
        self.nodes = {}
        self.runtime = {"session_id": "S"}


def cycle(nodes=None):
    return {"cycle_id": "C", "semantic_slice": {"intent_sha256": "I", "nodes": list(nodes or [])}}


def ledger(candidates):
    return {"sha256": "A" * 64, "candidates": list(candidates), "candidate_count": len(candidates)}


def candidate(node_id="A", text="send invite to Marco", material=True, governing=()):
    return {
        "node_id": node_id,
        "text": text,
        "material": material,
        "governing_commitment_ids": list(governing),
        "required_capabilities": ["calendar.write"] if material else [],
        "decision": {"status": "AUTHORITY_REQUIRED" if material else "PROPOSABLE"},
    }


class IntentEnvelopeTests(unittest.TestCase):
    def test_reminder_with_nested_buy_is_temporal_not_material_authority(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Domani ricordami di comprare il latte")
        env = build_intent_envelope(rt, cycle(), ledger([]), intention_node_id="I")
        self.assertTrue(env["signals"]["temporal"])
        self.assertTrue(env["signals"]["reminder"])
        self.assertFalse(env["signals"]["material"])
        self.assertEqual(env["route_hint"], "TEMPORAL_TASK_GOVERNANCE")
        self.assertFalse(env["reactive_graph_is_planner"])
        self.assertEqual(env["execution_authority"], 0.0)

    def test_memory_statement_demotes_out_of_planner(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Ricorda che Marco preferisce il pomeriggio")
        out, planner = reconcile_intent(rt, cycle(), ledger([]), temporal_core={"replay": {"sha256": "T"}}, intention_node_id="I")
        self.assertEqual(out["status"], "DEMOTE")
        self.assertEqual(out["route"], "MEMORY_GOVERNANCE")
        self.assertEqual(planner["candidate_count"], 0)

    def test_cognitive_compare_demotes_out_of_planner(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Confronta questi tre documenti")
        out, planner = reconcile_intent(rt, cycle(), ledger([]), temporal_core={}, intention_node_id="I")
        self.assertEqual(out["status"], "DEMOTE")
        self.assertEqual(out["route"], "COGNITIVE")
        self.assertEqual(planner["candidates"], [])

    def test_material_intent_matches_only_canonical_action_candidate(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Prepara e invia l'invito a Marco")
        rt.nodes["A"] = Node("A", K.ACTION, "invia invito a Marco")
        c = candidate(text="invia invito a Marco")
        out, planner = reconcile_intent(rt, cycle([{"id": "A", "kind": "action"}]), ledger([c]), temporal_core={}, intention_node_id="I")
        self.assertEqual(out["status"], "MATCH")
        self.assertEqual(out["route"], "CANONICAL_PLANNER")
        self.assertEqual(planner["candidate_count"], 1)
        self.assertEqual(planner["candidates"][0]["node_id"], "A")
        self.assertFalse(out["reconciler_executes"])

    def test_material_language_without_canonical_action_blocks(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Invia il messaggio a Marco")
        out, planner = reconcile_intent(rt, cycle(), ledger([]), temporal_core={}, intention_node_id="I")
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(planner["candidate_count"], 0)

    def test_injected_material_candidate_without_material_intent_blocks(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Spiegami il calendario")
        rt.nodes["A"] = Node("A", K.ACTION, "send invite to Marco")
        out, planner = reconcile_intent(rt, cycle(), ledger([candidate()]), temporal_core={}, intention_node_id="I")
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(planner["candidate_count"], 0)

    def test_forgotten_governing_reference_blocks(self):
        rt = Runtime(); rt.nodes["I"] = Node("I", K.INTENTION, "Invia invito a Marco")
        rt.nodes["A"] = Node("A", K.ACTION, "invia invito a Marco")
        rt.nodes["G"] = Node("G", K.GOAL, "organizza incontro", metadata={"temporal_state": "FORGOTTEN"})
        out, planner = reconcile_intent(rt, cycle(), ledger([candidate(text="invia invito a Marco", governing=("G",))]), temporal_core={}, intention_node_id="I")
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(out["unavailable_reference_node_ids"], ["G"])
        self.assertEqual(planner["candidates"], [])

    def test_independent_census_proves_one_planner_and_no_reactive_execution_bypass(self):
        proc = subprocess.run([sys.executable, "scripts/intent_plan_census_s21.py"], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"planner_count": 1', proc.stdout)
        self.assertIn('"reactive_execution_refs": []', proc.stdout)


if __name__ == "__main__":
    unittest.main()
