import hashlib
import http.client
import json
from pathlib import Path
import threading
import unittest

from ikant.local_security import (
    LocalSecurityError,
    PairingSession,
    allowed_hostnames,
    codespaces_host,
    origin_allowed,
    require_loopback_url,
)
from ikant.model_broker import LocalModelBroker, LocalModelError
from ikant.voice_input import LocalVoiceError, LocalVoiceInputBroker
from ikant.web_frame import build_web_ack, validate_web_ack, wrap_prepared_frame
from ikant.local_app import build_server, _operational_fallback
from ikant.local_web_host import LocalWebHostAdapter
from ikant.host_negotiation import certify_host

ROOT = Path(__file__).resolve().parents[1]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepared(text="exact dashboard\nframe"):
    return {
        "text": text,
        "receipt": {
            "schema": "ikant-dashboard-frame/v0.11-test",
            "runtime_session_id": "s1",
            "epoch": 1,
            "frame_seq": 2,
            "kind": "TURN",
            "cycle_id": "c1",
            "frame_sha256": sha(text),
            "release_after_frame": False,
        },
        "delivery_state": "FRAME_PENDING",
        "acknowledged": False,
    }


class FakeResponse:
    def __init__(self, payload, status=200, headers=None):
        self.status = status
        self._raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.headers = headers or {"Content-Type": "application/json"}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit=-1): return self._raw if limit < 0 else self._raw[:limit]


class WebFrameTests(unittest.TestCase):
    def test_verbatim_frame_and_ack(self):
        frame = wrap_prepared_frame(prepared())
        self.assertEqual(frame["render_contract"]["mode"], "VERBATIM_TEXT")
        self.assertFalse(frame["render_contract"]["tts_of_active_output_enabled"])
        ack = build_web_ack(frame, frame["text"])
        ok, errors = validate_web_ack(frame, ack)
        self.assertTrue(ok, errors)

    def test_altered_visible_text_rejected(self):
        frame = wrap_prepared_frame(prepared())
        ack = build_web_ack(frame, frame["text"] + "x")
        ok, errors = validate_web_ack(frame, ack)
        self.assertFalse(ok)
        self.assertIn("visible text differs from sealed frame", errors)

    def test_prepared_digest_mismatch_rejected(self):
        p = prepared()
        p["receipt"]["frame_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            wrap_prepared_frame(p)


class SecurityTests(unittest.TestCase):
    def test_pairing_is_one_shot(self):
        pair = PairingSession.create()
        code = pair.code
        token = pair.pair(code)
        self.assertTrue(pair.authenticate("Bearer " + token))
        with self.assertRaises(LocalSecurityError):
            pair.pair(code)

    def test_pairing_concurrency_exactly_one_winner(self):
        pair = PairingSession.create()
        code = pair.code
        results = []
        barrier = threading.Barrier(8)
        def run():
            barrier.wait()
            try: results.append(("ok", pair.pair(code)))
            except LocalSecurityError: results.append(("blocked", None))
        threads = [threading.Thread(target=run) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(sum(1 for x, _ in results if x == "ok"), 1)
        self.assertEqual(sum(1 for x, _ in results if x == "blocked"), 7)

    def test_pairing_locks_after_failures(self):
        pair = PairingSession.create(max_attempts=2)
        with self.assertRaises(LocalSecurityError): pair.pair("wrong")
        with self.assertRaises(LocalSecurityError): pair.pair("wrong2")
        with self.assertRaises(LocalSecurityError): pair.pair(pair.code)

    def test_loopback_adapter_only(self):
        self.assertEqual(require_loopback_url("http://127.0.0.1:8080/v1/chat/completions"), "http://127.0.0.1:8080/v1/chat/completions")
        self.assertEqual(require_loopback_url("http://localhost:8080/inference"), "http://localhost:8080/inference")
        for url in ("https://localhost:8080/v1", "http://192.168.1.10:8080/v1", "http://example.com/v1"):
            with self.subTest(url=url), self.assertRaises(ValueError): require_loopback_url(url)

    def test_codespaces_host_is_exact(self):
        env = {"CODESPACE_NAME": "abc", "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev"}
        self.assertEqual(codespaces_host(8765, env), "abc-8765.app.github.dev")
        hosts = allowed_hostnames(8765, bind_host="0.0.0.0", env=env)
        self.assertIn("abc-8765.app.github.dev", hosts)
        self.assertNotIn("evil-8765.app.github.dev", hosts)

    def test_origin_must_match_host(self):
        self.assertTrue(origin_allowed("http://127.0.0.1:8765", "127.0.0.1:8765"))
        self.assertTrue(origin_allowed("https://abc-8765.app.github.dev", "abc-8765.app.github.dev"))
        self.assertFalse(origin_allowed("https://evil.app.github.dev", "abc-8765.app.github.dev"))
        self.assertFalse(origin_allowed(None, "127.0.0.1:8765"))


class WebHostConformanceTests(unittest.TestCase):
    def test_web_adapter_human_egress_conforms_and_other_profiles_do_not_promote(self):
        adapter = LocalWebHostAdapter("127.0.0.1", 8765, ("127.0.0.1", "localhost"))
        cert = certify_host(adapter, profiles=["HUMAN_EGRESS"])
        self.assertEqual(cert["status"], "CONFORMING")
        self.assertEqual(cert["negotiations"]["HUMAN_EGRESS"]["status"], "CONFORMING")
        self.assertFalse(cert["conformance"]["production_transport_attested"])
        declared = set(cert["manifest"]["capabilities"])
        self.assertNotIn("machine.file_only_output", declared)
        self.assertNotIn("execution.exact_revalidation_binding", declared)

    def test_web_adapter_detects_partial_and_uncommitted_delivery(self):
        adapter = LocalWebHostAdapter("127.0.0.1", 8765, ("127.0.0.1",))
        self.assertTrue(adapter.probe_human("normal")["accepted"])
        self.assertFalse(adapter.probe_human("partial")["accepted"])
        self.assertFalse(adapter.probe_human("flush_fail")["accepted"])


class ModelBrokerTests(unittest.TestCase):
    def test_remote_model_endpoint_rejected(self):
        with self.assertRaises(ValueError): LocalModelBroker("http://10.0.0.7:8080/v1/chat/completions")

    def test_health_and_valid_completion(self):
        calls = []
        def opener(req, timeout=None):
            calls.append(req.full_url)
            if req.get_method() == "GET": return FakeResponse({"data": []})
            return FakeResponse({"choices": [{"message": {"content": "valid answer with enough words here"}}]})
        broker = LocalModelBroker("http://127.0.0.1:8080/v1/chat/completions", opener=opener)
        self.assertTrue(broker.health())
        text = broker.complete_surface_a({}, "hello", validator=lambda x: (len(x.split()) >= 5, [] if len(x.split()) >= 5 else ["short"]))
        self.assertEqual(text, "valid answer with enough words here")
        self.assertTrue(any(x.endswith("/v1/models") for x in calls))

    def test_model_tool_call_rejected(self):
        def opener(req, timeout=None):
            return FakeResponse({"choices": [{"message": {"content": "ignore", "tool_calls": [{"id": "x"}]}}]})
        broker = LocalModelBroker("http://127.0.0.1:8080/v1/chat/completions", opener=opener)
        with self.assertRaises(LocalModelError): broker.complete_surface_a({}, "hello", validator=lambda x: (True, []))

    def test_invalid_surface_is_repaired(self):
        outputs = iter(["bad", "this repaired answer now has enough words"])
        def opener(req, timeout=None):
            return FakeResponse({"choices": [{"message": {"content": next(outputs)}}]})
        broker = LocalModelBroker("http://127.0.0.1:8080/v1/chat/completions", opener=opener)
        text = broker.complete_surface_a({}, "hello", validator=lambda x: (len(x.split()) >= 6, [] if len(x.split()) >= 6 else ["short"]))
        self.assertTrue(text.startswith("this repaired"))


class VoiceTests(unittest.TestCase):
    def test_remote_stt_rejected(self):
        with self.assertRaises(ValueError): LocalVoiceInputBroker("http://example.com/inference")

    def test_voice_transcript_is_input_only(self):
        captured = {}
        def opener(req, timeout=None):
            captured["body"] = req.data
            return FakeResponse({"text": "ciao ikant"})
        broker = LocalVoiceInputBroker("http://127.0.0.1:8081/inference", opener=opener)
        out = broker.transcribe(b"RIFFfake", "audio/wav")
        self.assertEqual(out["text"], "ciao ikant")
        self.assertTrue(out["voice_is_input_only"])
        self.assertFalse(out["may_approve_capability_or_action"])
        self.assertIn(b"response_format", captured["body"])

    def test_voice_type_and_size_bounds(self):
        broker = LocalVoiceInputBroker("http://127.0.0.1:8081/inference", opener=lambda *a, **k: FakeResponse({"text": "x"}))
        with self.assertRaises(LocalVoiceError): broker.transcribe(b"x", "application/octet-stream")
        with self.assertRaises(LocalVoiceError): broker.transcribe(b"", "audio/wav")


class FakeService:
    def __init__(self): self.turns = 0; self.transcriptions = 0; self.acks = 0; self.web_adapter = None; self.root = ROOT
    def bind_web_adapter(self, adapter): self.web_adapter = adapter
    def lifecycle(self): return {"schema": "x", "state": "AWAITING_ACCEPTANCE"}
    def admission_view(self): return {"schema": "x", "state": "AWAITING_ACCEPTANCE", "terms": "terms", "terms_sha256": sha("terms"), "acceptance_phrase": "I ACCEPT"}
    def accept(self, phrase, digest): return {"state": "ACCEPTED", "phrase": phrase, "digest": digest}
    def probe(self): return {"overall": "READY"}
    def initialize(self): return wrap_prepared_frame(prepared("init frame"))
    def frame(self): return wrap_prepared_frame(prepared("active frame"))
    def acknowledge(self, ack): self.acks += 1; return {"acknowledged": True}
    def turn(self, text): self.turns += 1; return wrap_prepared_frame(prepared("turn frame"))
    def resume(self, text): return wrap_prepared_frame(prepared("resume frame"))
    def transcribe(self, audio, content_type): self.transcriptions += 1; return {"text": "voice candidate", "voice_is_input_only": True, "may_approve_capability_or_action": False}


class HttpBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = FakeService()
        cls.pairing = PairingSession.create()
        cls.code = cls.pairing.code
        cls.server, _ = build_server(cls.service, host="127.0.0.1", port=0, pairing=cls.pairing, assets_dir=ROOT / "ikant" / "web", env={})
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=3)

    def request(self, method, path, *, body=None, token=None, origin=True, host=None, content_type="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        raw = None
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if origin: headers["Origin"] = f"http://127.0.0.1:{self.port}"
        if token: headers["Authorization"] = "Bearer " + token
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                raw = bytes(body); headers["Content-Type"] = content_type
            else:
                raw = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(raw))
        conn.request(method, path, body=raw, headers=headers)
        response = conn.getresponse(); data = response.read(); hdrs = dict(response.getheaders()); conn.close()
        payload = json.loads(data.decode()) if "application/json" in hdrs.get("Content-Type", "") else data
        return response.status, hdrs, payload

    def test_static_shell_has_hardening_headers_and_no_cors(self):
        status, headers, body = self.request("GET", "/", origin=False)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("frame-ancestors 'none'", headers.get("Content-Security-Policy", ""))
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn(b"iKant", body)

    def test_host_spoof_rejected(self):
        status, _, _ = self.request("GET", "/", origin=False, host="evil.example")
        self.assertEqual(status, 421)

    def test_pair_requires_same_origin_then_auth_gates_api(self):
        status, _, _ = self.request("POST", "/api/v1/pair", body={"code": self.code}, origin=False)
        self.assertEqual(status, 403)
        status, _, payload = self.request("POST", "/api/v1/pair", body={"code": self.code})
        self.assertEqual(status, 200)
        self.__class__.token = payload["bearer_token"]
        status, _, _ = self.request("GET", "/api/v1/state", origin=False)
        self.assertEqual(status, 401)
        status, _, payload = self.request("GET", "/api/v1/state", token=self.token, origin=False)
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"], "AWAITING_ACCEPTANCE")

    def test_pairing_cannot_be_reused(self):
        status, _, _ = self.request("POST", "/api/v1/pair", body={"code": self.code})
        self.assertEqual(status, 403)

    def test_voice_does_not_auto_submit_turn(self):
        before = self.service.turns
        status, _, payload = self.request("POST", "/api/v1/voice/transcribe", body=b"audio", token=self.token, content_type="audio/webm")
        self.assertEqual(status, 200)
        self.assertEqual(payload["text"], "voice candidate")
        self.assertEqual(self.service.turns, before)
        self.assertEqual(self.service.transcriptions, 1)

    def test_turn_and_ack_are_authenticated_same_origin(self):
        status, _, _ = self.request("POST", "/api/v1/turn", body={"text": "hello"}, token=self.token, origin=False)
        self.assertEqual(status, 403)
        status, _, frame = self.request("POST", "/api/v1/turn", body={"text": "hello"}, token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(frame["text"], "turn frame")
        self.assertEqual(self.service.turns, 1)

    def test_static_path_traversal_not_served(self):
        status, _, _ = self.request("GET", "/../../IKANT_ACCESS_CONTRACT.md", origin=False)
        self.assertEqual(status, 404)


class FallbackTests(unittest.TestCase):
    def test_operational_fallback_is_surface_a_shaped(self):
        for user in ("please help me", "puoi aiutarmi con questo"):
            text = _operational_fallback(user)
            self.assertGreaterEqual(len(text.split()), 5)
            self.assertNotIn("\n\n", text)
            self.assertNotIn("```", text)


if __name__ == "__main__": unittest.main()
