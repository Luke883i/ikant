from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InteractiveLivenessSourceTests(unittest.TestCase):
    def setUp(self):
        self.js = (ROOT / "ikant" / "web" / "conversation.js").read_text(encoding="utf-8")
        self.sw = (ROOT / "ikant" / "web" / "sw.js").read_text(encoding="utf-8")
        self.bootstrap = (ROOT / "ikant" / "bootstrap_http.py").read_text(encoding="utf-8")

    def test_http_decoder_accepts_empty_error_bodies_without_json_parse_crash(self):
        self.assertIn("const rawText=await response.text()", self.js)
        self.assertIn("if(rawText)", self.js)
        self.assertIn("JSON.parse(rawText)", self.js)
        self.assertIn("HTTP_ERROR", self.js)
        self.assertIn("HTTP_INVALID_JSON", self.js)

    def test_on_device_voice_never_uses_prefixed_potentially_remote_recognition(self):
        self.assertIn("const SR=window.SpeechRecognition", self.js)
        self.assertNotIn("window.webkitSpeechRecognition", self.js)
        self.assertIn("'processLocally' in probe", self.js)
        self.assertIn("SR.available({langs:[lang],processLocally:true})", self.js)
        self.assertIn("SR.install({langs:[lang],processLocally:true})", self.js)
        self.assertIn("rec.processLocally=true", self.js)

    def test_native_failure_is_observable_and_capability_failure_can_fallback(self):
        self.assertIn("VOICE_NATIVE_ERROR", self.js)
        self.assertIn("language-not-supported", self.js)
        self.assertIn("service-not-allowed", self.js)
        self.assertIn("fallbackVoiceAfterNativeError", self.js)
        self.assertIn("Nessuna voce rilevata", self.js)

    def test_loopback_recording_never_starts_when_stt_is_unconfigured(self):
        check = "if(state.product?.voice?.configured!==true)throw new Error('STT loopback non configurato')"
        self.assertIn(check, self.js)
        self.assertLess(self.js.index(check), self.js.index("navigator.mediaDevices.getUserMedia({audio:true})"))
        self.assertIn("VOICE_FALLBACK_UNAVAILABLE", self.js)

    def test_voice_candidate_remains_input_only_and_requires_explicit_send(self):
        self.assertIn("out.auto_submit!==false", self.js)
        self.assertIn("Testo riconosciuto. Premi ↑ per inviare a iKant.", self.js)
        self.assertNotIn("requestSubmit()", self.js)

    def test_turn_submit_is_single_owned_by_capture_adapter_and_always_reports_failure(self):
        self.assertIn("$('turn-form').addEventListener('submit',async e=>", self.js)
        self.assertIn("e.stopImmediatePropagation()", self.js)
        self.assertIn("renderPrimaryValue(IKANT_PENDING_PRIMARY)", self.js)
        self.assertIn("TURN_SUBMIT", self.js)
        self.assertIn("TURN_FAIL", self.js)
        self.assertIn("await recoverShell(error)", self.js)
        self.assertIn("SHELL_RECOVERY_FAIL", self.js)

    def test_runtime_live_log_is_bounded_zero_authority_and_progressive(self):
        self.assertIn("IKANT_RUNTIME_EVENT_LIMIT=48", self.js)
        self.assertIn("ikant-browser-runtime-liveness/v0.29-test", self.js)
        self.assertIn("epistemic_authority:0.0,execution_authority:0.0", self.js)
        self.assertIn("text('system-diagnostics'", self.js)
        self.assertIn("text('voice-diagnostics'", self.js)

    def test_tts_requires_local_service_voice_and_never_speaks_pending(self):
        self.assertIn("localVoices()", self.js)
        self.assertIn("no localService voice", self.js)
        self.assertIn("frame?.receipt?.kind!=='TURN'", self.js)
        self.assertIn("if(!spoken)return", self.js)

    def test_hotfix_asset_is_revalidated_and_served_by_bootstrap_handler(self):
        self.assertIn("interactive-liveness-hotfix5", self.sw)
        self.assertIn("'/conversation.js'", self.sw)
        self.assertIn("'conversation.js'", self.bootstrap)
        self.assertIn("'/conversation.js'", self.bootstrap)


if __name__ == "__main__":
    unittest.main()
