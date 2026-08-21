from __future__ import annotations
import copy,hashlib,json,unittest
from pathlib import Path
from ikant.human_frame import build_human_frame
from ikant.human_surface_protocol import HSP_SCHEMA,project_human_surface,validate_human_surface
ROOT=Path(__file__).parents[1]
class FakeRuntime:
 def __init__(self,session='SES-S7'):self.runtime={'session_id':session}
def base_dashboard():return {'session_egress':{'state':'DASHBOARD_LOCKED','epoch':3},'incarnate':{'state':'IDLE','cycle_id':None,'surface_a':{'status':'EMPTY','cycle_id':None,'text':None},'surface_b':{'bound':False,'cycle_id':None,'json':{},'docx':{}}}}
def turn_dashboard():
 d=base_dashboard();d['incarnate']={'state':'READY','cycle_id':'CYC-7','surface_a':{'status':'VALIDATED','cycle_id':'CYC-7','text':'Risposta validata'},'surface_b':{'bound':True,'cycle_id':'CYC-7','json':{'sha256':'a'*64},'docx':{'sha256':'b'*64}}};return d
def rehash(env):
 material=dict(env);material.pop('sha256',None);env['sha256']=hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
class HumanSurfaceProtocolV25Tests(unittest.TestCase):
 def test_notice_is_single_zero_authority_payload(self):
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='NOTICE',notice='Stato aggiornato');ok,e=validate_human_surface(d);self.assertTrue(ok,e);h=d['human_surface_protocol'];self.assertEqual(h['schema'],HSP_SCHEMA);self.assertEqual(h['kind'],'NOTICE');self.assertEqual([k for k,v in h['payload'].items() if v is not None],['notice']);self.assertFalse(h['raw_model_tokens_visible']);self.assertFalse(h['parallel_human_message_allowed']);self.assertEqual(h['execution_authority'],0.0)
 def test_hsp_requires_locked_positive_egress_epoch(self):
  for egress in ({'state':'RELEASED','epoch':3},{'state':'DASHBOARD_LOCKED','epoch':0},{'state':'DASHBOARD_LOCKED','epoch':None}):
   d=base_dashboard();d['session_egress']=egress
   with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),d,kind='NOTICE',notice='x')
 def test_turn_requires_validated_a_and_bound_b_same_cycle(self):
  d=project_human_surface(FakeRuntime(),turn_dashboard(),kind='TURN',cycle_id='CYC-7');self.assertTrue(validate_human_surface(d)[0]);t=d['human_surface_protocol']['payload']['surface_turn'];self.assertTrue(t['surface_a_inside_dashboard']);self.assertTrue(t['surface_b_bound'])
  bad=turn_dashboard();bad['incarnate']['surface_b']['cycle_id']='CYC-X'
  with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),bad,kind='TURN',cycle_id='CYC-7')
 def test_approval_request_projects_valid_human_frame_without_decision(self):
  frame=build_human_frame(session_id='SES-S7',actor_binding_id='ab-s7',frame_seq=1,purpose='ACTION_CONFIRMATION',title='Conferma',body='Conferma azione',action_fingerprint='act-1')
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='APPROVAL_REQUEST',approval_frame=frame);self.assertTrue(validate_human_surface(d)[0]);a=d['human_surface_protocol']['payload']['approval_request'];self.assertEqual(a['session_id'],'SES-S7');self.assertEqual(a['actor_binding_id'],'ab-s7');self.assertTrue(a['requires_explicit_decision']);self.assertTrue(a['presentation_is_not_authorization']);self.assertFalse(a['decision_recorded']);self.assertFalse(a['grant_issued']);self.assertEqual(a['execution_authority'],0.0)
 def test_approval_request_is_session_bound(self):
  frame=build_human_frame(session_id='OTHER',actor_binding_id='ab-s7',frame_seq=1,purpose='ACTION_CONFIRMATION',title='Conferma',body='Conferma')
  with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),base_dashboard(),kind='APPROVAL_REQUEST',approval_frame=frame)
 def test_progress_and_degraded_are_bounded_control_state(self):
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='PROGRESS',progress={'phase':'FETCH','label':'Verifica','fraction':0.5});self.assertTrue(validate_human_surface(d)[0]);self.assertEqual(d['human_surface_protocol']['state'],'WORKING')
  for bad in (-0.01,1.01,float('nan'),float('inf')):
   with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),base_dashboard(),kind='PROGRESS',progress={'label':'x','fraction':bad})
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='DEGRADED',degraded={'code':'VOICE_OFF','message':'Voce non disponibile','capability_loss':['voice_input']});self.assertTrue(validate_human_surface(d)[0]);self.assertEqual(d['human_surface_protocol']['state'],'DEGRADED')
 def test_exit_is_release_bound_and_resume_is_not(self):
  with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),base_dashboard(),kind='EXIT',notice='Uscita')
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='EXIT',notice='Uscita',release_after_frame=True);self.assertTrue(validate_human_surface(d)[0]);self.assertEqual(d['human_surface_protocol']['payload']['release']['command'],'EXIT IKANT')
  with self.assertRaises(ValueError):project_human_surface(FakeRuntime(),base_dashboard(),kind='RESUME',notice='Rientro',release_after_frame=True)
 def test_digest_and_payload_tamper_fail_closed(self):
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='ERROR',error={'code':'E','message':'errore'});bad=copy.deepcopy(d);bad['human_surface_protocol']['payload']['error']['retryable']=True;self.assertFalse(validate_human_surface(bad)[0]);bad=copy.deepcopy(d);bad['human_surface_protocol']['payload']['notice']={'message':'parallel'};self.assertFalse(validate_human_surface(bad)[0])
 def test_rehashed_typed_tamper_still_fails_semantic_validation(self):
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='ERROR',error={'code':'E','message':'errore'});bad=copy.deepcopy(d);bad['human_surface_protocol']['payload']['error']['authority_effect']='EXECUTE';rehash(bad['human_surface_protocol']);ok,e=validate_human_surface(bad);self.assertFalse(ok);self.assertIn('error_authority',e)
  x=project_human_surface(FakeRuntime(),base_dashboard(),kind='EXIT',notice='Uscita',release_after_frame=True);bad=copy.deepcopy(x);bad['human_surface_protocol']['payload']['release']['command']='QUIT';rehash(bad['human_surface_protocol']);ok,e=validate_human_surface(bad);self.assertFalse(ok);self.assertIn('exit_release',e)
  frame=build_human_frame(session_id='SES-S7',actor_binding_id='ab-s7',frame_seq=1,purpose='ACTION_CONFIRMATION',title='Conferma',body='Conferma');a=project_human_surface(FakeRuntime(),base_dashboard(),kind='APPROVAL_REQUEST',approval_frame=frame);bad=copy.deepcopy(a);bad['human_surface_protocol']['payload']['approval_request']['session_id']='OTHER';rehash(bad['human_surface_protocol']);ok,e=validate_human_surface(bad);self.assertFalse(ok);self.assertIn('approval_session_binding',e)
 def test_malformed_degraded_projection_returns_fail_not_validator_exception(self):
  d=project_human_surface(FakeRuntime(),base_dashboard(),kind='DEGRADED',degraded={'code':'D','message':'degraded','capability_loss':['voice']});bad=copy.deepcopy(d);bad['human_surface_protocol']['payload']['degraded']['capability_loss']=[{}];rehash(bad['human_surface_protocol']);ok,e=validate_human_surface(bad);self.assertFalse(ok);self.assertIn('degraded_capability_loss',e)
 def test_active_browser_has_no_parallel_error_text_channel(self):
  js=(ROOT/'ikant'/'web'/'app.js').read_text(encoding='utf-8');html=(ROOT/'ikant'/'web'/'index.html').read_text(encoding='utf-8');self.assertIn('recoverShell',js);self.assertNotIn("setError('active-error',error.message)",js);self.assertNotIn("setError('active-error',_error.message)",js);self.assertNotIn('id="active-error"',html)
 def test_session_host_projects_protocol_before_seal(self):
  text=(ROOT/'ikant'/'session_host.py').read_text(encoding='utf-8');self.assertLess(text.index('project_human_surface'),text.index('prepare_text_frame(runtime,render_dashboard_ascii'))
if __name__=='__main__':unittest.main()
