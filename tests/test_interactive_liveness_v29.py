from __future__ import annotations

from pathlib import Path
import unittest

from ikant.bootstrap_http import TRANSPORT_DIAGNOSTIC_SCHEMA, transport_diagnostic

ROOT = Path(__file__).resolve().parents[1]


class InteractiveLivenessSourceTests(unittest.TestCase):
    def setUp(self):
        self.js = (ROOT / "ikant" / "web" / "conversation.js").read_text(encoding="utf-8")
        self.sw = (ROOT / "ikant" / "web" / "sw.js").read_text(encoding="utf-8")
        self.bootstrap = (ROOT / "ikant" / "bootstrap_http.py").read_text(encoding="utf-8")

    def test_http_decoder_accepts_empty_errors_and_does_not_retry_semantic_409(self):
        self.assertIn("const rawText=await response.text()", self.js)
        self.assertIn("if(rawText)", self.js)
        self.assertIn("JSON.parse(rawText)", self.js)
        self.assertIn("HTTP_ERROR", self.js)
        self.assertIn("HTTP_INVALID_JSON", self.js)
        self.assertIn("retryableHttp", self.js)
        self.assertIn("status===408", self.js)
        self.assertIn("status===425", self.js)
        self.assertIn("status===429", self.js)
        self.assertNotIn("status===409", self.js)

    def test_on_device_voice_is_attested_and_never_falls_back_to_remote_recognition(self):
        self.assertIn("const SR=window.SpeechRecognition", self.js)
        self.assertNotIn("window.webkitSpeechRecognition", self.js)
        self.assertIn("'processLocally' in probe", self.js)
        self.assertIn("SR.available({langs:[lang],processLocally:true})", self.js)
        self.assertIn("SR.install({langs:[lang],processLocally:true})", self.js)
        self.assertIn("VOICE_NATIVE_POST_INSTALL_AVAILABILITY", self.js)
        self.assertIn("rec.processLocally=true", self.js)
        self.assertNotIn("processLocally=false", self.js)

    def test_native_failure_is_observable_and_capability_failure_can_fallback(self):
        self.assertIn("VOICE_NATIVE_ERROR", self.js)
        for code in ("language-not-supported", "service-not-allowed", "network", "audio-capture"):
            self.assertIn(code, self.js)
        self.assertIn("fallbackVoiceAfterNativeError", self.js)
        self.assertIn("Nessuna voce rilevata", self.js)
        self.assertIn("Dettatura interrotta", self.js)

    def test_loopback_recording_never_prompts_when_stt_is_unconfigured(self):
        check = "if(state.product?.voice?.configured!==true)throw new Error('STT loopback non configurato')"
        self.assertIn(check, self.js)
        self.assertLess(self.js.index(check), self.js.index("navigator.mediaDevices.getUserMedia({audio:true})"))
        self.assertIn("VOICE_FALLBACK_UNAVAILABLE", self.js)

    def test_media_recorder_negotiates_only_broker_accepted_audio_containers(self):
        for media in ("audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"):
            self.assertIn(media, self.js)
        self.assertIn("MediaRecorder.isTypeSupported", self.js)
        self.assertIn("IKANT_VOICE_MEDIA_BASES", self.js)
        self.assertIn("VOICE_RECORDER_MIME_REJECTED", self.js)
        self.assertIn("NotAllowedError", self.js)
        self.assertIn("NotFoundError", self.js)

    def test_voice_candidate_remains_input_only_and_never_overwrites_concurrent_user_edit(self):
        self.assertIn("out.auto_submit!==false", self.js)
        self.assertIn("Testo riconosciuto. Premi ↑ per inviare a iKant.", self.js)
        self.assertIn("VOICE_RESULT_DISCARDED_USER_EDIT", self.js)
        self.assertIn("state.intentRevision", self.js)
        self.assertNotIn("requestSubmit()", self.js)

    def test_turn_submit_has_immediate_pending_slow_liveness_and_terminal_diagnostics(self):
        self.assertIn("$('turn-form').addEventListener('submit',async e=>", self.js)
        self.assertIn("e.stopImmediatePropagation()", self.js)
        self.assertIn("renderPrimaryValue(IKANT_PENDING_PRIMARY)", self.js)
        self.assertIn("TURN_SUBMIT", self.js)
        self.assertIn("TURN_WAITING", self.js)
        self.assertIn("TURN_SLOW", self.js)
        self.assertIn("TURN_FAIL", self.js)
        self.assertIn("await recoverShell(error)", self.js)
        self.assertIn("SHELL_RECOVERY_FAIL", self.js)
        self.assertIn("clearTurnWatchdogs", self.js)

    def test_runtime_live_log_is_bounded_redacted_zero_authority_and_progressive(self):
        self.assertIn("IKANT_RUNTIME_EVENT_LIMIT=48", self.js)
        self.assertIn("ikant-browser-runtime-liveness/v0.29-test", self.js)
        self.assertIn("[REDACTED]", self.js)
        self.assertIn("epistemic_authority:0.0,execution_authority:0.0", self.js)
        self.assertIn("text('system-diagnostics'", self.js)
        self.assertIn("text('voice-diagnostics'", self.js)

    def test_tts_requires_local_service_and_recovers_from_initial_empty_voice_list(self):
        self.assertIn("localVoices()", self.js)
        self.assertIn("voiceOutputAwaiting", self.js)
        self.assertIn("onvoiceschanged", self.js)
        self.assertIn("VOICE_TTS_VOICES_CHANGED", self.js)
        self.assertIn("frame?.receipt?.kind!=='TURN'", self.js)
        self.assertIn("if(!spoken)return", self.js)

    def test_server_returns_bounded_structured_shell_and_voice_diagnostics(self):
        self.assertIn("TRANSPORT_DIAGNOSTIC_SCHEMA", self.bootstrap)
        self.assertIn("path.startswith('/api/v2/shell/')", self.bootstrap)
        self.assertIn("path=='/api/v3/voice/transcribe'", self.bootstrap)
        self.assertIn("transport_diagnostic(path,exc)", self.bootstrap)
        out = transport_diagnostic('/api/v2/shell/command', RuntimeError('token=abc Bearer xyz secret:zzz ' + 'x'*500))
        self.assertEqual(out['schema'], TRANSPORT_DIAGNOSTIC_SCHEMA)
        self.assertEqual(out['epistemic_authority'], 0.0)
        self.assertEqual(out['execution_authority'], 0.0)
        self.assertLessEqual(len(out['message']), 240)
        self.assertNotIn('abc', out['message'])
        self.assertNotIn('xyz', out['message'])
        self.assertNotIn('zzz', out['message'])
        self.assertIn('[REDACTED]', out['message'])

    def test_hotfix_asset_is_revalidated_and_served_by_bootstrap_handler(self):
        self.assertIn("interactive-liveness-hotfix5", self.sw)
        self.assertIn("'/conversation.js'", self.sw)
        self.assertIn("'conversation.js'", self.bootstrap)
        self.assertIn("'/conversation.js'", self.bootstrap)


if __name__ == "__main__":
    unittest.main()
