from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from ikant.cognitive_v05 import compile_cognitive_turn
from ikant.v05_cli import _psyche_integrity
from ikant.model import Layer,NodeKind
from ikant.psyche import PSYCHE_SCHEMA,validate_functional_psyche
from ikant.runtime import Runtime
from tests.helpers import active_runtime
RANK={'REFLECTIVE_SYNTHESIS':0,'PRACTICAL_REVIEW':1,'SYNTHESIS_REPAIR':2,'CRITIQUE':3,'PRACTICAL_BLOCK':4,'HORIZON_BLOCK':5}
class RuntimePsycheV05Tests(unittest.TestCase):
 def test_durable_turn_materializes_psyche_without_changing_external_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=True);sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='sentinel external evidence',confidence=.8,evidence=.37,source_mode='document');before=sentinel.evidence;out=compile_cognitive_turn(rt,'Valuta il prossimo passo con prudenza e conserva i limiti.',export_docx=True);psyche=out['functional_psyche'];self.assertEqual(psyche['schema'],PSYCHE_SCHEMA);self.assertTrue(validate_functional_psyche(psyche)[0]);self.assertEqual(rt.nodes[sentinel.id].evidence,before);self.assertFalse(out['workspace']['evidence_modified']);self.assertTrue(Path(out['psyche_json']).exists());self.assertTrue(Path(out['surface_b_json']).exists());self.assertTrue(Path(out['surface_b_docx']).exists());snap=json.loads(Path(out['surface_b_json']).read_text());self.assertEqual(snap['dynamic_state']['functional_psyche']['schema'],PSYCHE_SCHEMA);reg=out['central_oracle']['functional_psyche_regulation'];self.assertGreaterEqual(RANK[reg['result_mode']],RANK[reg['base_mode']]);self.assertFalse(reg['evidence_modified']);rt.close();reopened=Runtime(Path(td)/'repo'/'.ikant');self.assertTrue(reopened.integrity()['ok']);self.assertTrue(_psyche_integrity(reopened)['ok']);reopened.close()
 def test_maturation_is_persistent_revisable_and_non_evidential(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=False);sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='persistent evidence boundary',confidence=.7,evidence=.41,source_mode='repository');before=sentinel.evidence
   for i in range(36):out=compile_cognitive_turn(rt,f'Continua la valutazione coerente {i}')
   self.assertEqual(rt.nodes[sentinel.id].evidence,before);self.assertEqual(out['functional_psyche']['epistemic_accumulation']['turns'],36);self.assertFalse(out['functional_psyche']['epistemic_accumulation']['may_change_evidence']);rt.close()
 def test_psyche_file_tamper_is_detected_by_host_integrity(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td),durable=True);out=compile_cognitive_turn(rt,'Materializza un auto-modello operativo verificabile.');path=Path(out['psyche_json']);payload=json.loads(path.read_text());payload['boundaries']['phenomenal_consciousness_claim']=True;path.write_text(json.dumps(payload));check=_psyche_integrity(rt);self.assertFalse(check['ok']);self.assertIn('psyche persistence/runtime mismatch',check['errors']);rt.close()
 def test_operational_self_is_explicitly_not_sentience(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));out=compile_cognitive_turn(rt,'Chi sei e quali sono i tuoi limiti?');sk=out['functional_psyche']['self_knowledge'];self.assertEqual(sk['identity'],'iKant');self.assertTrue(sk['operational_self_awareness']);self.assertFalse(sk['phenomenal_consciousness_claim']);self.assertFalse(sk['felt_emotion_claim']);self.assertFalse(sk['brain_one_to_one_claim']);rt.close()
if __name__=='__main__':unittest.main()
