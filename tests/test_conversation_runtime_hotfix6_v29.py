from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from ikant.engine_supervisor import build_server_command
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


def frame(text: str, *, cycle: str = "CYC-screen", kind: str = "TURN") -> dict:
    return {"text": text,"receipt": {"runtime_session_id": "SES-hotfix6","epoch": 1,"frame_seq": 7,"kind": kind,"cycle_id": cycle,"frame_sha256": hashlib.sha256(text.encode()).hexdigest(),"release_after_frame": False},"delivery_state": "FRAME_PENDING"}


class StructuredPrimaryProjectionTests(unittest.TestCase):
    def test_real_screenshot_shape_no_longer_collapses_validated_reply_to_pending(self):
        dashboard = "\n".join(["+----------------------------------------------------------------------------------------------+","| SUPERFICIE A      [VALIDATED] ciclo CYC-screen                                      |","| [prompt-like text] > iKant: Ciao! Come posso aiutarti oggi?                          |","| SUPERFICIE B      [BOUND] CRC_SNAPSHOT_CYC-screen.docx                              |","+----------------------------------------------------------------------------------------------+"])
        self.assertEqual(project_primary_text(dashboard, "TURN"), "iKant: Ciao! Come posso aiutarti oggi?")
        wrapped = wrap_prepared_frame(frame(dashboard));self.assertEqual(wrapped["primary_text"], "iKant: Ciao! Come posso aiutarti oggi?");self.assertNotEqual(wrapped["primary_text"], PENDING_PRIMARY_TEXT)

    def test_live_turn_prefers_structured_surface_over_ascii_dashboard(self):
        dashboard = "\n".join(["| SUPERFICIE A      [VALIDATED] ciclo CYC-screen |","| [presentation deliberately unparsable] |","| SUPERFICIE B      [BOUND] x.docx |"])
        wrapped = wrap_prepared_frame(frame(dashboard), primary_text="iKant: Ciao, questa risposta arriva dal dato strutturato.")
        self.assertEqual(wrapped["primary_text"], "iKant: Ciao, questa risposta arriva dal dato strutturato.");self.assertEqual(wrapped["primary_projection_source"], "STRUCTURED_SURFACE_A");self.assertTrue(wrapped["render_contract"]["structured_primary_preferred"]);self.assertTrue(wrapped["render_contract"]["dashboard_parsing_is_compatibility_only"])

    def test_explicit_primary_is_bounded_and_identity_prefixed(self):
        dashboard = "| SUPERFICIE A      [PENDING] ciclo CYC-screen |"
        with self.assertRaises(ValueError):wrap_prepared_frame(frame(dashboard), primary_text="risposta senza identita")
        with self.assertRaises(ValueError):wrap_prepared_frame(frame(dashboard), primary_text="iKant: x\x00y")


class FastInferenceBoundaryTests(unittest.TestCase):
    def test_server_is_single_user_bounded_and_prompt_cached(self):
        cmd = build_server_command("/engine/llama-server", "/model/q.gguf", 31337, "/state/key")
        for flag, value in (("--reasoning", "off"), ("--ctx-size", "4096"), ("--parallel", "1")):
            self.assertIn(flag, cmd);self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--cache-prompt", cmd);self.assertIn("--no-webui", cmd)

    def test_compact_generation_preserves_language_identity_and_one_repair(self):
        responses = iter([{"choices": [{"message": {"content": "Hello, I can help with your question."}}], "usage": {"prompt_tokens": 100, "completion_tokens": 9}},{"choices": [{"message": {"content": "Sono iKant; il motore Qwen3.5-0.8B genera la risposta locale senza autorita propria."}}], "usage": {"prompt_tokens": 120, "completion_tokens": 18}}])
        payloads = []
        def opener(req, timeout=None):payloads.append(json.loads(req.data.decode()));return FakeResponse(next(responses))
        broker = LocalModelBroker("http://127.0.0.1:31337/v1/chat/completions", model="Qwen3.5-0.8B", opener=opener);text = broker.complete_surface_a({}, "ciao, chi sei?", validator=validate_surface_a)
        self.assertTrue(text.startswith("Sono iKant"));self.assertEqual(len(payloads), 2);system = payloads[0]["messages"][0]["content"];self.assertIn('"language":"Italian"', system);self.assertIn('"identity_first":true', system);self.assertLess(len(system), 2500);self.assertLessEqual(payloads[0]["max_tokens"], 110);self.assertEqual(payloads[0]["tools"], []);self.assertEqual(broker.last_completion_metrics["attempts"], 2);self.assertEqual(broker.last_completion_metrics["epistemic_authority"], 0.0);self.assertEqual(broker.last_completion_metrics["execution_authority"], 0.0)

    def test_simple_italian_turn_repairs_mixed_language_reply(self):
        responses=iter([{"choices":[{"message":{"content":"Ciao! How can I help you today?"}}]},{"choices":[{"message":{"content":"Ciao, sono qui e posso aiutarti con quello che ti serve."}}]}]);payloads=[]
        def opener(req,timeout=None):payloads.append(json.loads(req.data.decode()));return FakeResponse(next(responses))
        broker=LocalModelBroker("http://127.0.0.1:31337/v1/chat/completions",model="Qwen3.5-0.8B",opener=opener);text=broker.complete_surface_a({},"ciao",validator=validate_surface_a)
        self.assertTrue(text.startswith("Ciao,"));self.assertEqual(len(payloads),2);self.assertIn("reply language differs",payloads[1]["messages"][-1]["content"])

    def test_local_service_turn_has_no_redundant_health_round_trip_and_supplies_structured_primary(self):
        source = (ROOT / "ikant" / "local_service.py").read_text(encoding="utf-8");turn = source.split("    def turn(self,user_text):", 1)[1].split("    def notice", 1)[0]
        self.assertNotIn("self.model.health()", turn);self.assertIn("wrap_prepared_frame(prepared,primary_text='iKant: '+surface)", turn);self.assertIn("_structured_primary_from_chat", source);self.assertIn("model_metrics", turn)


class VoiceRoundTripBindingTests(unittest.TestCase):
    def test_voice_path_remains_local_candidate_then_same_explicit_turn(self):
        app = (ROOT / "ikant" / "web" / "app.js").read_text(encoding="utf-8");js = (ROOT / "ikant" / "web" / "conversation.js").read_text(encoding="utf-8")
        self.assertIn("const SR=window.SpeechRecognition", js);self.assertNotIn("window.webkitSpeechRecognition", js);self.assertIn("rec.processLocally=true", js);self.assertIn("out.auto_submit!==false", js);self.assertIn("Premi ↑ per inviare a iKant", js);self.assertIn("shellCommand('TURN',{text:value})", js);self.assertIn("localService===true", app);self.assertIn("localVoices()", js);self.assertIn("maybeSpeak(frame)", js);self.assertIn("FRAME_ACKED", js)


if __name__ == "__main__":unittest.main()
