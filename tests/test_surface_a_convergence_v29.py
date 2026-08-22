from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from ikant.engine_supervisor import build_server_command
from ikant.interaction import build_interaction_contract, validate_interaction_surface
from ikant.local_service import operational_fallback
from ikant.model_broker import LocalModelBroker
from ikant.surfaces import validate_surface_a
from ikant.web_frame import PENDING_PRIMARY_TEXT, project_primary_text, wrap_prepared_frame

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.raw = json.dumps(payload).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit=-1): return self.raw if limit < 0 else self.raw[:limit]


def _frame(text: str, *, kind: str = "TURN") -> dict:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "text": text,
        "receipt": {
            "runtime_session_id": "s1",
            "epoch": 1,
            "frame_seq": 1,
            "kind": kind,
            "cycle_id": "c1",
            "frame_sha256": digest,
            "release_after_frame": False,
        },
        "delivery_state": "FRAME_PENDING",
    }


class GenerationBoundaryTests(unittest.TestCase):
    def test_server_disables_reasoning_for_surface_a_runtime(self):
        cmd = build_server_command("/engine/llama-server", "/model/q.gguf", 31337, "/state/key")
        self.assertEqual(cmd[cmd.index("--reasoning") + 1], "off")
        self.assertIn("--no-webui", cmd)
        self.assertNotIn("--agent", cmd)

    def test_identity_contract_is_inside_generation_and_repair_loop(self):
        responses = iter([
            {"choices": [{"message": {"content": "Sono un assistente locale pronto a rispondere alla tua domanda."}}]},
            {"choices": [{"message": {"content": "Sono iKant; il motore Qwen3.5-0.8B genera il testo locale, senza autorità propria."}}]},
        ])
        payloads = []
        def opener(req, timeout=None):
            payloads.append(json.loads(req.data.decode("utf-8")))
            return FakeResponse(next(responses))
        broker = LocalModelBroker("http://127.0.0.1:31337/v1/chat/completions", model="Qwen3.5-0.8B", opener=opener)
        text = broker.complete_surface_a({}, "ciao, chi sei?", validator=validate_surface_a)
        self.assertTrue(text.startswith("Sono iKant"))
        self.assertEqual(len(payloads), 2)
        self.assertIn("interaction_contract", payloads[0]["messages"][0]["content"])
        self.assertEqual(payloads[0]["tools"], [])
        self.assertLessEqual(payloads[0]["max_tokens"], 165)

    def test_reasoning_only_or_empty_content_never_counts_as_surface_a(self):
        def opener(req, timeout=None):
            return FakeResponse({"choices": [{"message": {"content": "", "reasoning_content": "private reasoning"}}]})
        broker = LocalModelBroker("http://127.0.0.1:31337/v1/chat/completions", opener=opener)
        with self.assertRaises(Exception):
            broker.complete_surface_a({}, "ciao", validator=validate_surface_a)

    def test_italian_fallback_and_identity_are_interaction_valid(self):
        simple = operational_fallback("ciao", engine_label="Qwen3.5-0.8B")
        self.assertTrue(simple.startswith("Il motore linguistico locale"))
        identity = operational_fallback("ciao, chi sei?", engine_label="Qwen3.5-0.8B")
        self.assertTrue(identity.startswith("Sono iKant"))
        contract = build_interaction_contract("ciao, chi sei?", engine_label="Qwen3.5-0.8B")
        ok, errors = validate_interaction_surface(identity, contract)
        self.assertTrue(ok, errors)
        self.assertIn("nessuna azione materiale", identity)


class PrimaryProjectionTests(unittest.TestCase):
    def test_pending_dashboard_projects_only_exact_pending_line(self):
        dashboard = "\n".join([
            "+----------------+",
            "| SUPERFICIE A      [PENDING] ciclo c1 |",
            "| > iKant: [PENDING - la risposta validata non e ancora stata emessa] |",
            "| SUPERFICIE B      [BOUND] x.docx |",
        ])
        self.assertEqual(project_primary_text(dashboard, "TURN"), PENDING_PRIMARY_TEXT)
        wrapped = wrap_prepared_frame(_frame(dashboard))
        self.assertEqual(wrapped["primary_text"], PENDING_PRIMARY_TEXT)
        self.assertEqual(wrapped["render_contract"]["mode"], "VERBATIM_TEXT")
        self.assertEqual(wrapped["render_contract"]["primary_mode"], "PRIMARY_WITH_PROGRESSIVE_DISCLOSURE")
        self.assertTrue(wrapped["render_contract"]["canonical_frame_ack_remains_exact"])

    def test_validated_surface_projects_reply_without_dashboard(self):
        dashboard = "\n".join([
            "+----------------+",
            "| SUPERFICIE A      [VALIDATED] ciclo c1 |",
            "| > iKant: Sono iKant e questa e la risposta validata |",
            "|          per il turno corrente. |",
            "| SUPERFICIE B      [BOUND] x.docx |",
        ])
        primary = project_primary_text(dashboard, "TURN")
        self.assertEqual(primary, "iKant: Sono iKant e questa e la risposta validata per il turno corrente.")
        self.assertNotIn("SUPERFICIE", primary)
        self.assertNotIn("Backlog runtime", primary)

    def test_control_message_preempts_stale_surface(self):
        dashboard = "\n".join([
            "| Uscita Uscita da iKant confermata. |",
            "| SUPERFICIE A      [VALIDATED] ciclo c0 |",
            "| > iKant: risposta precedente che non deve vincere |",
            "| SUPERFICIE B      [BOUND] x.docx |",
        ])
        self.assertEqual(project_primary_text(dashboard, "EXIT"), "iKant: Uscita da iKant confermata.")

    def test_web_client_keeps_canonical_frame_in_inspector(self):
        js = (ROOT / "ikant" / "web" / "conversation.js").read_text(encoding="utf-8")
        html = (ROOT / "ikant" / "web" / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "ikant" / "web" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("function renderPrimaryValue(value)", js)
        self.assertIn("const primary=primaryText(frame);renderPrimaryValue(primary)", js)
        self.assertIn("renderPrimaryValue(IKANT_PENDING_PRIMARY)", js)
        self.assertIn("text('dashboard',out)", js)
        self.assertIn("text('frame-inspect',detail", js)
        self.assertIn("IKANT_PENDING_PRIMARY", js)
        self.assertIn("visible_text:canonical", js)
        self.assertLess(html.index('/app.js'), html.index('/conversation.js'))
        self.assertIn("HSPv2 · dettagli on demand", html)
        self.assertIn("/conversation.js", sw)
        self.assertIn("ikant-s10bis-bootstrap-v1", sw)


if __name__ == "__main__":
    unittest.main()
