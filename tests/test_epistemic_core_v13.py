import tempfile
import unittest
from pathlib import Path

from ikant.calibration import apply_calibration_to_cycle, derive_calibration
from ikant.causal_crc import diagnose_crc_causality
from ikant.cognitive_runtime import compile_cognitive_turn
from ikant.hybrid_retrieval import apply_hybrid_retrieval
from ikant.model import Layer, NodeKind, RelationKind
from ikant.provenance import bind_node_source, materialize_provenance, provenance_quality, validate_provenance_graph
from tests.helpers import active_runtime


class EpistemicCoreV13Tests(unittest.TestCase):
    def test_provenance_tracks_independent_sources_without_authority_escalation(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            try:
                n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='The release gate passed',confidence=.8,evidence=.7,source_mode='repository',metadata={'path':'ci/receipt.json','provenance_key':'repo:ci'})
                bind_node_source(rt,n.id,source_mode='document',provenance_key='doc:independent',locator='audit/report.txt')
                out=materialize_provenance(rt);ok,errs=validate_provenance_graph(out['graph'])
                self.assertTrue(ok,errs);self.assertGreaterEqual(len(out['graph']['claims'][n.id]['source_ids']),2)
                self.assertGreater(provenance_quality(rt,n.id),.6);self.assertEqual(out['summary']['epistemic_authority'],0.0)
                self.assertTrue((Path(rt.state_dir)/'provenance.json').exists())
            finally: rt.close()

    def test_calibration_is_feedback_bound_and_monotone_caution(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            try:
                first=compile_cognitive_turn(rt,'Assess whether this result is reliable')
                rt.record_feedback(first['cycle']['cycle_id'],outcome='failure',prediction_error=.9)
                second=compile_cognitive_turn(rt,'Reassess the result after the failed prediction')
                profile=second['epistemic_core']['calibration']; policy=second['cycle']['output_policy']
                self.assertGreaterEqual(profile['sample_count'],1);self.assertGreater(profile['risk_adjustment'],0)
                self.assertTrue(policy['calibration']['monotone_caution_only']);self.assertFalse(policy['calibration']['evidence_modified'])
                self.assertGreaterEqual(policy['epistemic_caution'],policy['calibration']['base_caution'])
                self.assertGreaterEqual(policy['claim_threshold'],policy['calibration']['base_claim_threshold'])
            finally: rt.close()

    def test_hybrid_retrieval_modifies_availability_only(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            try:
                a=rt.ingest(kind=NodeKind.CONSTRAINT,layer=Layer.MEMORY,text='Rollback before deployment if validation fails',confidence=.9,evidence=.8,source_mode='repository',metadata={'provenance_key':'repo:rollback'})
                b=rt.ingest(kind=NodeKind.HYPOTHESIS,layer=Layer.ARCHETYPAL_HYPOTHESIS,text='A symbolic bridge pattern',confidence=.3,evidence=.1,source_mode='runtime_derived')
                before={x.id:x.evidence for x in (a,b)}; trace=apply_hybrid_retrieval(rt,'deployment rollback validation',limit=2)
                self.assertEqual(before,{x.id:x.evidence for x in (a,b)});self.assertFalse(trace['evidence_modified'])
                self.assertEqual(trace['authority'],'AVAILABILITY_ONLY');self.assertNotIn('intent',trace);self.assertIn('intent_sha256',trace)
            finally: rt.close()

    def test_crc_causal_diagnostics_are_executable_and_bounded(self):
        baseline={'roa_alignment':{'crc_basic':True,'representational_path_complete':True},'diagnostics':{'mean_coefficient_of_collapse':.2,'epistemic_debt_open_count':0,'functional_coherence':.9}}
        sem={'nodes':[{'id':'critical','kind':'claim','source_mode':'document','epistemic_score':.9},{'id':'other','kind':'claim','source_mode':'repository','epistemic_score':.7}]}
        def evaluator(slice_,**kwargs):
            ids={x['id'] for x in slice_['nodes']}; ok='critical' in ids
            return {'roa_alignment':{'crc_basic':ok,'representational_path_complete':ok},'diagnostics':{'mean_coefficient_of_collapse':.2 if ok else .8,'epistemic_debt_open_count':0 if ok else 2,'functional_coherence':.9 if ok else .3}}
        out=diagnose_crc_causality(sem,baseline,evaluator=evaluator,max_node_ablations=2,max_source_ablations=2)
        self.assertTrue(out['single_point_dependency']);self.assertGreater(out['max_counterfactual_dependency'],.4)
        self.assertEqual(out['epistemic_authority'],0.0);self.assertIn('not proof',out['claim_boundary'])

    def test_canonical_turn_materializes_all_epistemic_slices(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            try:
                source=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='Main currently contains the target implementation',confidence=.8,evidence=.7,source_mode='repository',metadata={'path':'ikant/runtime.py','provenance_key':'repo:runtime'})
                before=source.evidence
                out=compile_cognitive_turn(rt,'Audit the implementation and preserve source boundaries',atoms=[{'kind':'constraint','layer':'predictive_control','text':'Do not promote derived telemetry to evidence','confidence':.9,'evidence':.8,'source_mode':'user','metadata':{'provenance_key':'user:current-session'}}])
                core=out['epistemic_core'];self.assertEqual(core['schema'],'ikant-epistemic-core/v0.13-test')
                self.assertIn('provenance',core);self.assertIn('calibration',core);self.assertIn('hybrid_retrieval',core);self.assertIn('causal_crc',core)
                self.assertIn('causal_diagnostics',out['crc']);self.assertEqual(rt.nodes[source.id].evidence,before)
                self.assertEqual(out['surface_b_snapshot']['dynamic_state']['epistemic_core']['schema'],'ikant-epistemic-core/v0.13-test')
            finally: rt.close()

if __name__=='__main__': unittest.main()
