from __future__ import annotations
import json,re,unittest
from pathlib import Path
from ikant.experience_projection import EXPERIENCE_PROJECTION_SCHEMA,COGNITIVE_TRACE_SCHEMA,TURN_TIMING_SCHEMA,PUBLIC_STAGES,cognitive_trace,experience_projection,timing_start,timing_mark,timing_public
from ikant.future_supply import future_supply_manifest
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=('Surface A','Surface B','HSPv2','S8','S9','S10','S10bis','Authority UI','PROGRESSIVE DISCLOSURE','ADMISSION','PROBE','INITIALIZE','CRC','proto_self','psychodynamic_hypothesis','archetypal_hypothesis','kant_oracle')

class ECF13RuntimeV30Tests(unittest.TestCase):
 def test_projection_is_zero_authority_and_public_stages_are_stable(self):
  t=timing_start(10.0);timing_mark(t,'TURN_ACCEPTED',10.0);timing_mark(t,'COGNITIVE_START',10.01)
  trace=cognitive_trace({'cycle':{'cycle_id':'CYC-X','semantic_slice':{'nodes':[{}],'directives':[]}},'crc':{'roa_alignment':{'crc_basic':True}},'central_projection':{},'practical_reason':{},'intention_node_id':'N1','mined_atoms':[]},{'source':'MODEL','model_metrics':{'total_ms':12.5}},{'response_id':'R1'})
  out=experience_projection(runtime_session_id='SES-X',cycle_id='CYC-X',primary_text='iKant: risposta',state='Pronto',trace=trace,timing=t,generation={'source':'MODEL'})
  self.assertEqual(out['schema'],EXPERIENCE_PROJECTION_SCHEMA);self.assertEqual(trace['schema'],COGNITIVE_TRACE_SCHEMA);self.assertEqual(out['epistemic_authority'],0.0);self.assertEqual(out['execution_authority'],0.0);self.assertFalse(trace['private_chain_of_thought']);self.assertFalse(trace['raw_model_rationale']);self.assertEqual([x[1] for x in PUBLIC_STAGES],['Capisco','Collego','Verifico','Valuto','Formulo','Integro']);self.assertEqual(trace['stages'][-1]['facts']['evidence'],0.0);self.assertEqual(timing_public(t)['schema'],TURN_TIMING_SCHEMA)
 def test_turn_timing_and_artifact_boundary_are_source_bound(self):
  cog=(ROOT/'ikant/cognitive_runtime.py').read_text();host=(ROOT/'ikant/runtime_host.py').read_text();local=(ROOT/'ikant/local_service.py').read_text()
  for phase in ('TURN_ACCEPTED','COGNITIVE_START','SEMANTIC_SLICE_DONE','CRC_DONE','GOVERNANCE_DONE','SNAPSHOT_JSON_DONE'):self.assertIn(phase,cog)
  for phase in ('MODEL_START','MODEL_DONE','VALIDATION_DONE','FRAME_SEALED','PRIMARY_DELIVERED','ACK_DONE'):self.assertIn(phase,local)
  self.assertIn('export_docx=False',host);self.assertNotIn('export_surface_b_docx',host);self.assertIn('_schedule_cycle_artifact',local);turn=local.split('    def turn(self,user_text):',1)[1].split('    def notice(',1)[0];self.assertNotIn('export_surface_b_docx',turn);self.assertIn("timing_mark(timing,'PRIMARY_DELIVERED'",turn)
 def test_web_shell_is_compact_single_owner_and_hides_internal_taxonomy(self):
  html=(ROOT/'ikant/web/index.html').read_text();app=(ROOT/'ikant/web/app.js').read_text();compat=(ROOT/'ikant/web/conversation.js').read_text();epi=(ROOT/'ikant/web/epistemic.js').read_text();sw=(ROOT/'ikant/web/sw.js').read_text()
  self.assertEqual(html.count('id="dashboard"'),1);self.assertNotIn('orbit-rail',html);self.assertNotIn('disabled',html)
  for label in FORBIDDEN:self.assertNotIn(label,html)
  self.assertEqual(app.count("turn-form').addEventListener('submit'"),1);self.assertEqual(app.count("voice-button').addEventListener('click'"),1);self.assertNotIn('webkitSpeechRecognition',app);self.assertIn('processLocally:true',app);self.assertIn('auto_submit!==false',app);self.assertIn('MediaRecorder.isTypeSupported',app);self.assertIn('PRIMARY_DELIVERED',app);self.assertIn('ACK_DONE',app);self.assertIn('runtimeEvents',app)
  self.assertNotIn('addEventListener',compat);self.assertNotRegex(compat,r'\b(?:api|renderProduct|renderShellResponse|toggleVoice)\s*=')
  self.assertIn("LEGACY_LAYOUT_LABELS=['Graph','List']",epi);self.assertIn('Rete',epi);self.assertIn('Elenco',epi);self.assertIn("event.code==='Space'",epi);self.assertIn("show('epi-docx',!!c.artifacts?.docx?.available)",epi)
  self.assertIn('ikant-s10bis-bootstrap-v1-interactive-liveness-hotfix5-ecf1-3-runtime-v30',sw);self.assertIn('caches.delete',sw)
 def test_http_exposes_read_only_experience_projection(self):
  http=(ROOT/'ikant/bootstrap_http.py').read_text();self.assertIn("'/api/v6/experience'",http);self.assertIn('runtime_projection(service.root)',http);self.assertIn("if not self._guard():return",http)
 def test_response_memory_boundary_remains_zero_evidence(self):
  cognitive=(ROOT/'ikant/cognitive.py').read_text();self.assertIn('kind=NodeKind.RESPONSE',cognitive);self.assertIn('layer=Layer.MEMORY',cognitive);self.assertIn("source_mode='runtime_derived'",cognitive);self.assertRegex(cognitive,r'evidence=0\.0');self.assertIn('speech_act_not_evidence',cognitive)
 def test_future_supply_is_defined_but_not_activated(self):
  out=future_supply_manifest();self.assertFalse(out['activated']);self.assertEqual(out['epistemic_authority'],0.0);self.assertEqual(out['execution_authority'],0.0);self.assertEqual(len(out['components']),5);blob=json.dumps(out);self.assertIn('exact_allowed_origins_no_wildcards',blob);self.assertIn('owns_no_cognition',blob);self.assertIn('platform_permission_surface_first',blob);self.assertIn('pinned_version',blob)
 def test_ecf13_contract_remains_registered_as_historical_slice(self):
  c=json.loads((ROOT/'docs/ECF1_3_ENGINEERING_CONTRACT.json').read_text());ids=[x['id'] for x in c['invariants']];self.assertEqual(ids,[f'ECF13-{i:03d}' for i in range(1,31)]);product=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());s11=next(s for s in product['slices'] if s['id']=='S11');self.assertEqual(s11['schema'],'ikant-experience-projection/v1.3');self.assertEqual(s11['invariants'],ids);self.assertLess([s['id'] for s in product['slices']].index('S11'),len(product['slices'])-1)
if __name__=='__main__':unittest.main()
