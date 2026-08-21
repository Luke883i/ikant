from __future__ import annotations
import time,unittest
from pathlib import Path
from ikant.product_experience import ProductBootstrapCoordinator,ProductExperienceService,PRODUCT_EXPERIENCE_SCHEMA,PRODUCT_VOICE_SCHEMA
ROOT=Path(__file__).resolve().parents[1]

class FakeModel:
 managed_runtime=True;runtime_binding_digest='a'*64;model='local-test'
 def health(self):return True
 def status(self):return {'configured':True}

class FakeRuntime:
 def __init__(self,fail=False):self.fail=fail;self.stops=0
 def start(self,*,progress,readiness_timeout):
  progress({'phase':'PLAN','target':'model','bytes':100});progress({'phase':'DOWNLOADING','target':'model','bytes':50})
  if self.fail:raise RuntimeError('blocked')
  progress({'phase':'VERIFIED','target':'model','bytes':100});return FakeModel()
 def stop(self,*,persist=True):self.stops+=1

class FakeVoice:
 def status(self):return {'configured':True,'endpoint_scope':'LOOPBACK_ONLY','voice_is_input_only':True,'voice_can_approve_authority':False}
 def transcribe(self,audio,content_type):return {'text':'candidate vocale'}

class ProductExperienceV27Tests(unittest.TestCase):
 def wait(self,c):
  for _ in range(200):
   s=c.product_status()
   if s['stage'] in {'READY','BLOCKED'}:return s
   time.sleep(.005)
  self.fail('bootstrap did not settle')
 def test_bootstrap_exposes_zero_authority_progress_then_ready(self):
  c=ProductBootstrapCoordinator(ROOT,runtime=FakeRuntime(),voice_endpoint=None,readiness_timeout=.1);c.start_async();s=self.wait(c)
  self.assertEqual(s['schema'],PRODUCT_EXPERIENCE_SCHEMA);self.assertEqual(s['stage'],'READY');self.assertTrue(s['runtime_ready']);self.assertFalse(s['diagnostics']['browser_may_mark_ready']);self.assertFalse(s['diagnostics']['runtime_readiness_is_authority']);self.assertEqual(s['epistemic_authority'],0.0);self.assertEqual(s['execution_authority'],0.0);c.stop()
 def test_blocked_setup_remains_visible_and_retry_is_explicit(self):
  rt=FakeRuntime(fail=True);c=ProductBootstrapCoordinator(ROOT,runtime=rt,voice_endpoint=None,readiness_timeout=.1);c.start_async();s=self.wait(c);self.assertEqual(s['stage'],'BLOCKED');self.assertTrue(s['diagnostics']['retry_available']);rt.fail=False;c.retry_setup();self.assertEqual(self.wait(c)['stage'],'READY');c.stop()
 def test_voice_candidate_is_writer_bound_and_never_auto_submits_or_approves(self):
  svc=ProductExperienceService(ROOT,model=FakeModel(),voice=FakeVoice());svc.require_web_conformance=lambda: {};svc._active_session_id=lambda:'SES-S9';opened=svc.web_shell.open('SES-S9','client-1234567890123456');out=svc.shell_voice_candidate(opened['shell_id'],opened['client_id'],b'audio','audio/webm');self.assertEqual(out['schema'],PRODUCT_VOICE_SCHEMA);self.assertEqual(out['text'],'candidate vocale');self.assertTrue(out['writer_bound']);self.assertFalse(out['auto_submit']);self.assertFalse(out['may_approve_capability_or_action']);self.assertEqual(out['execution_authority'],0.0)
 def test_ui_is_chat_first_progressive_and_single_semantic_viewport(self):
  html=(ROOT/'ikant/web/index.html').read_text(encoding='utf-8');js=(ROOT/'ikant/web/app.js').read_text(encoding='utf-8');css=(ROOT/'ikant/web/styles.css').read_text(encoding='utf-8')
  self.assertEqual(html.count('id="dashboard"'),1);self.assertIn('command-palette',html);self.assertIn('inspector',html);self.assertIn('setup-panel',html);self.assertIn('orbit-rail',html);self.assertNotIn('https://',html);self.assertNotIn('https://',css);self.assertIn('prefers-reduced-motion',css)
  self.assertIn("frame?.receipt?.kind!=='TURN'",js);self.assertIn('localService===true',js);self.assertIn('processLocally:true',js);self.assertIn('auto_submit!==false',js);self.assertLess(js.index('confirmed=await apiRetry'),js.rindex('maybeSpeak(frame)'))
 def test_product_status_declares_progressive_disclosure_and_post_ack_voice(self):
  c=ProductBootstrapCoordinator(ROOT,runtime=FakeRuntime(),voice_endpoint=None,readiness_timeout=.1);c.start_async();s=self.wait(c);x=s['experience'];self.assertTrue(x['progressive_disclosure']);self.assertTrue(x['traditional_controls_on_demand']);self.assertFalse(x['epistemic_inspector_default_open']);self.assertEqual(x['voice_output_source'],'POST_ACK_SEALED_SURFACE_A_ONLY');c.stop()
if __name__=='__main__':unittest.main()
