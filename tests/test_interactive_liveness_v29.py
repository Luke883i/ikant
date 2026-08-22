from __future__ import annotations
from pathlib import Path
import unittest
from ikant.bootstrap_http import TRANSPORT_DIAGNOSTIC_SCHEMA,transport_diagnostic
ROOT=Path(__file__).resolve().parents[1]

class InteractiveLivenessSourceTests(unittest.TestCase):
 def setUp(self):
  self.js=(ROOT/'ikant/web/app.js').read_text(encoding='utf-8')
  self.compat=(ROOT/'ikant/web/conversation.js').read_text(encoding='utf-8')
  self.sw=(ROOT/'ikant/web/sw.js').read_text(encoding='utf-8')
  self.bootstrap=(ROOT/'ikant/bootstrap_http.py').read_text(encoding='utf-8')
 def test_single_controller_owns_transport_and_compat_is_noop(self):
  self.assertEqual(self.js.count("turn-form').addEventListener('submit'"),1)
  self.assertEqual(self.js.count("voice-button').addEventListener('click'"),1)
  self.assertNotIn('addEventListener',self.compat)
  self.assertIn('ECF1.3',self.compat)
 def test_http_decoder_preserves_errors_and_does_not_retry_semantic_409(self):
  api=self.js.split('async function api(',1)[1].split('function retryable',1)[0]
  self.assertRegex(api,r'const\s+rawText\s*=\s*await\s+\w+\.text\(\)');self.assertIn('JSON.parse(rawText)',api)
  self.assertIn('HTTP_ERROR',api);self.assertIn('HTTP_RETRY',self.js)
  for code in ('s===408','s===425','s===429'):self.assertIn(code,self.js)
  self.assertNotIn('s===409',self.js);self.assertNotIn('status===409',self.js)
 def test_on_device_voice_is_local_only_and_has_loopback_fallback_boundary(self):
  self.assertIn('const SR=window.SpeechRecognition',self.js);self.assertNotIn('webkitSpeechRecognition',self.js)
  self.assertIn('SR.available({langs:[lang],processLocally:true})',self.js);self.assertIn('SR.install({langs:[lang],processLocally:true})',self.js)
  self.assertIn('r.processLocally=true',self.js);self.assertIn("state.product?.voice?.configured===true",self.js)
  self.assertNotIn('processLocally=false',self.js)
 def test_loopback_checks_configuration_before_microphone_and_negotiates_mime(self):
  check="if(state.product?.voice?.configured!==true)throw new Error('STT locale non configurato')"
  self.assertIn(check,self.js);self.assertLess(self.js.index(check),self.js.index('navigator.mediaDevices.getUserMedia({audio:true})'))
  for media in ('audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'):self.assertIn(media,self.js)
  self.assertIn('MediaRecorder.isTypeSupported',self.js);self.assertIn('IKANT_VOICE_MEDIA_BASES',self.js)
 def test_voice_candidate_is_input_only(self):
  self.assertIn('out.auto_submit!==false',self.js)
  voice=self.js.split('async function loopbackVoiceInput',1)[1].split('function resizeComposer',1)[0]
  self.assertNotIn('requestSubmit()',voice)
 def test_turn_submit_has_immediate_pending_slow_liveness_and_recovery(self):
  submit=self.js.split("$('turn-form').addEventListener('submit'",1)[1].split("$('intent').addEventListener('input'",1)[0]
  self.assertIn('IKANT_PENDING_PRIMARY',submit);self.assertIn('startWatchdogs()',submit);self.assertIn('recoverShell',submit)
  self.assertIn('TURN_WAITING',self.js);self.assertIn('TURN_SLOW',self.js);self.assertIn('SHELL_RECOVERY_FAIL',self.js)
 def test_runtime_log_is_bounded_redacted_and_zero_authority(self):
  self.assertIn('IKANT_RUNTIME_EVENT_LIMIT=48',self.js);self.assertIn('[REDACTED]',self.js)
  self.assertIn('epistemic_authority:0.0,execution_authority:0.0',self.js)
  self.assertIn("text('system-diagnostics'",self.js);self.assertIn("text('voice-diagnostics'",self.js)
 def test_tts_requires_local_service_and_post_ack_turn(self):
  self.assertIn('localService===true',self.js);self.assertIn("frame?.receipt?.kind!=='TURN'",self.js)
  self.assertIn('maybeSpeak(f)',self.js);self.assertLess(self.js.index('acknowledged!==true'),self.js.index('maybeSpeak(f)'))
 def test_server_returns_bounded_structured_shell_and_voice_diagnostics(self):
  self.assertIn('TRANSPORT_DIAGNOSTIC_SCHEMA',self.bootstrap);self.assertIn("path.startswith('/api/v2/shell/')",self.bootstrap);self.assertIn("path=='/api/v3/voice/transcribe'",self.bootstrap)
  out=transport_diagnostic('/api/v2/shell/command',RuntimeError('token=abc Bearer xyz secret:zzz '+'x'*500))
  self.assertEqual(out['schema'],TRANSPORT_DIAGNOSTIC_SCHEMA);self.assertEqual(out['epistemic_authority'],0.0);self.assertEqual(out['execution_authority'],0.0);self.assertLessEqual(len(out['message']),240)
  for secret in ('abc','xyz','zzz'):self.assertNotIn(secret,out['message'])
  self.assertIn('[REDACTED]',out['message'])
 def test_hotfix_lineage_asset_is_revalidated_and_served(self):
  self.assertIn('interactive-liveness-hotfix5',self.sw);self.assertIn("'/conversation.js'",self.sw);self.assertIn("'conversation.js'",self.bootstrap);self.assertIn("'/conversation.js'",self.bootstrap)

if __name__=='__main__':unittest.main()
