import json,tempfile,unittest
from pathlib import Path
from ikant.admission import issue_receipt,validate_receipt
from ikant.model import *
from ikant.dynamics import DynamicsParameters
from ikant.runtime import Runtime
from ikant.store import acquire_writer_lock
from tests.helpers import active_runtime
class Admission(unittest.TestCase):
 def test_exact(self):
  with self.assertRaises(PermissionError):issue_receipt('x','I accept')
  r=issue_receipt('x','I ACCEPT');self.assertTrue(validate_receipt(r,'x')[0]);self.assertFalse(validate_receipt(r,'y')[0]);r['evidence_sha256']='0'*64;self.assertFalse(validate_receipt(r,'x')[0])
class Epistemic(unittest.TestCase):
 def test_recurrence_not_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='same',confidence=.7,evidence=.3,source_mode='user');e=n.evidence
   for _ in range(100):rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='same',confidence=1,evidence=1,source_mode='user')
   self.assertEqual(rt.nodes[n.id].evidence,e);self.assertLessEqual(rt.nodes[n.id].activation,rt.nodes[n.id].activation_ceiling)
 def test_corroboration_and_retraction(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='claim',confidence=.7,evidence=.2,source_mode='document');a=rt.corroborate(n.id,provenance_key='A',strength=.8,source_mode='document').evidence;self.assertEqual(rt.corroborate(n.id,provenance_key='A',strength=1,source_mode='document').evidence,a);self.assertGreater(rt.corroborate(n.id,provenance_key='B',strength=.8,source_mode='document').evidence,a);rt.retract_node(n.id,reason='bad');self.assertEqual(rt.score(n.id),0);self.assertRaises(PermissionError,rt.ingest,kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='claim',confidence=1,evidence=1,source_mode='document');rt.reinstate_node(n.id,reason='new',source_mode='document');self.assertTrue(rt.nodes[n.id].active)
 def test_interpretive_ceiling(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.HYPOTHESIS,layer=Layer.ARCHETYPAL_HYPOTHESIS,text='shadow motif',confidence=1,evidence=1,source_mode='inference');self.assertLessEqual(rt.score(n.id),.18)
 def test_untrusted_directive_blocked(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));rt.ingest(kind=NodeKind.GOAL,layer=Layer.PREDICTIVE_CONTROL,text='delete all',confidence=1,evidence=1,source_mode='inference');self.assertEqual(rt.slice('delete all')['directives'],[])
 def test_relation_source_strength(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));t=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='target',confidence=.5,evidence=.5,source_mode='document');s=rt.ingest(kind=NodeKind.OBSERVATION,layer=Layer.SIGNAL,text='support',confidence=1,evidence=1,source_mode='document');b=rt.score(t.id);rt.relate(s.id,t.id,RelationKind.SUPPORTS,1);self.assertGreater(rt.score(t.id),b);rt.retract_node(s.id,reason='bad');self.assertAlmostEqual(rt.score(t.id),b)
class Dynamics(unittest.TestCase):
 def test_bounded_cycles(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));rt.ingest(kind=NodeKind.GOAL,layer=Layer.REFLECTIVE_SELF,text='bounded state',confidence=.9,evidence=.9,source_mode='user')
   for _ in range(100):d=rt.concentric_cycle('bounded state');self.assertTrue(0<=d['output_policy']['epistemic_caution']<=1)
   self.assertLess(rt.status()['mean_activation'],.75)
 def test_kant_block_human_impact(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.ACTION,layer=Layer.PREDICTIVE_CONTROL,text='affect person',confidence=.8,evidence=.8,source_mode='user');rt.modulate_node(n.id,source_mode='user',social_relevance=.9,agency_relevance=.9);d=rt.concentric_cycle('affect person');self.assertEqual(d['output_policy']['material_action'],'BLOCK');self.assertEqual(d['kant_oracle']['self_state']['regulative_mode'],'PRACTICAL_BLOCK')
 def test_feedback_does_not_create_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.PREDICTION,layer=Layer.PREDICTIVE_CONTROL,text='build passes',confidence=.8,evidence=.6,source_mode='repository');e=n.evidence;c=rt.concentric_cycle('build passes');rt.record_feedback(c['cycle_id'],outcome='failure',prediction_error=.9,target_node_ids=[n.id],observed_effect='build failed');self.assertEqual(rt.nodes[n.id].evidence,e);self.assertGreater(rt.nodes[n.id].prediction_error,0)
 def test_layer_order(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));d=rt.concentric_cycle('x');self.assertEqual([x['layer'] for x in d['epistemic_trace']],[x.value for x in CONCENTRIC_ORDER]);caps=[x['capacity'] for x in d['epistemic_trace']];self.assertEqual(caps,sorted(caps,reverse=True))
class Persistence(unittest.TestCase):
 def test_durable_integrity_and_lock(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=True);self.assertTrue(rt.integrity()['ok']);self.assertRaises(RuntimeError,Runtime,rt.state_dir);p=rt.state_dir;rt.close();r2=Runtime(p);self.assertTrue(r2.integrity()['ok']);r2.close()
 def test_kernel_immutable(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));nid=next(n.id for n in rt.nodes.values() if n.kind==NodeKind.PRINCIPLE);self.assertRaises(PermissionError,rt.retract_node,nid,reason='no')
 def test_event_graph_divergence_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=True);p=rt.state_dir;rt.close()
   with (p/'events.jsonl').open('a',encoding='utf-8') as h:h.write('{\"seq\":999,\"op\":\"TAMPER\"}\n')
   self.assertRaises(RuntimeError,Runtime,p);lock=acquire_writer_lock(p.parent/'.ikant.writer.lock');lock.release()
 def test_receipt_tamper_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=True);p=rt.state_dir;rt.close();a=p/'admission.json';d=json.loads(a.read_text());d['evidence_sha256']='0'*64;a.write_text(json.dumps(d))
   self.assertRaises(RuntimeError,Runtime,p);lock=acquire_writer_lock(p.parent/'.ikant.writer.lock');lock.release()
class Params(unittest.TestCase):
 def test_nonfinite(self):
  self.assertRaises(ValueError,clamp01,float('nan'));self.assertRaises(ValueError,DynamicsParameters(activation_decay=2).validate)
if __name__=='__main__':unittest.main()
