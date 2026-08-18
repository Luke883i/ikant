import math, tempfile, unittest
from pathlib import Path

from ikant.central import converge_kant_oracle
from ikant.cognitive import compile_cognitive_turn, record_surface_a
from ikant.crc import EpistemicHorizon, evaluate_reticulum
from ikant.model import Layer, NodeKind, RelationKind
from ikant.surfaces import validate_surface_a
from tests.helpers import active_runtime


def base_row(**kw):
    row={
        'id':'N1','layer':'signal','kind':'observation','epistemic_score':.72,
        'activation':.2,'stability':.2,'novelty':.7,'prediction_error':.1,
        'source_mode':'document','text':'grounded boundary observation','modulators':{},
    }
    row.update(kw);return row


class EdgeV02Tests(unittest.TestCase):
    def test_unknown_ring_fails_closed_without_crash(self):
        out=evaluate_reticulum({'nodes':[base_row(layer='unknown')],'directives':[]})
        self.assertFalse(out['roa_alignment']['ioa'])
        self.assertFalse(out['roa_alignment']['crc_basic'])
        self.assertIn('unregistered ring:unknown',out['ioa_errors'])

    def test_source_outside_declared_horizon_fails_closed(self):
        h=EpistemicHorizon(allowed_source_modes=('document',))
        out=evaluate_reticulum({'nodes':[base_row(source_mode='user')],'directives':[]},horizon=h)
        self.assertTrue(out['horizon_exceeded'])
        self.assertFalse(out['roa_alignment']['epistemic_closure'])
        self.assertIn('source outside horizon:user',out['ioa_errors'])

    def test_malformed_numeric_is_not_allowed_into_crc(self):
        for bad in (float('nan'),float('inf'),-0.1,1.1,'not-a-number'):
            out=evaluate_reticulum({'nodes':[base_row(activation=bad)],'directives':[]})
            self.assertFalse(out['roa_alignment']['crc_basic'])
            self.assertTrue(any(x.startswith('invalid numeric:activation') for x in out['ioa_errors']))

    def test_divergent_duplicate_id_is_detected(self):
        rows=[base_row(id='X',text='first'),base_row(id='X',text='different')]
        out=evaluate_reticulum({'nodes':rows,'directives':[]})
        self.assertFalse(out['roa_alignment']['crc_basic'])
        self.assertIn('divergent duplicate id:X',out['ioa_errors'])

    def test_surface_a_rejects_unicode_and_html_lists_and_setext(self):
        bad=(
            '• primo elemento\n• secondo elemento\nQuesta forma non deve passare.',
            '<ul><li>primo elemento</li></ul> Questa forma non deve passare.',
            'Titolo\n=====\nQuesta intestazione non deve passare come prosa.',
            '    print(1)\nQuesta forma di codice indentato non deve passare.',
            '<table><tr><td>x</td></tr></table> Questa tabella non deve passare.',
        )
        for text in bad:self.assertFalse(validate_surface_a(text)[0],text)

    def test_horizon_block_changes_surface_contract(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            out=compile_cognitive_turn(rt,'Rispondi oltre il perimetro dichiarato',horizon=EpistemicHorizon(max_ring='signal'))
            self.assertEqual(out['central_oracle']['regulative_mode'],'HORIZON_BLOCK')
            self.assertTrue(out['surface_a_contract']['regulation']['must_abstain_or_review'])
            self.assertEqual(out['central_projection']['material_action'],'BLOCK')
            rt.close()

    def test_practical_block_changes_surface_contract(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            action=rt.ingest(kind=NodeKind.ACTION,layer=Layer.PREDICTIVE_CONTROL,text='apply a material change affecting another person',confidence=.9,evidence=.8,source_mode='user')
            rt.modulate_node(action.id,source_mode='user',social_relevance=.95,agency_relevance=.95)
            out=compile_cognitive_turn(rt,'Procedi con questa azione materiale')
            self.assertEqual(out['central_oracle']['regulative_mode'],'PRACTICAL_BLOCK')
            self.assertEqual(out['central_projection']['material_action'],'BLOCK')
            self.assertFalse(out['central_projection']['authorized_directives'])
            rt.close()

    def test_practical_review_is_distinct_from_material_block(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            out=compile_cognitive_turn(rt,'Completa il lavoro richiesto',atoms=[{'kind':'goal','layer':'predictive_control','text':'complete explicitly requested operation','confidence':.9,'evidence':.9,'source_mode':'user'}])
            self.assertEqual(out['central_oracle']['regulative_mode'],'PRACTICAL_REVIEW')
            self.assertNotEqual(out['central_projection']['material_action'],'BLOCK')
            self.assertTrue(out['surface_a_contract']['regulation']['must_abstain_or_review'])
            rt.close()

    def test_stressed_uncertainty_forces_repair_or_critique(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td));rt.runtime['calibration']={'n':10,'brier_sum':10.0,'brier_mean':1.0}
            nodes=[]
            for i in range(10):
                n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text=f'weak uncertain state {i}',confidence=.25,evidence=.08,source_mode='inference')
                n.prediction_error=.95;n.activation=.5;rt._save(n);nodes.append(n)
            for i in range(1,len(nodes),2):rt.relate(nodes[i].id,nodes[i-1].id,RelationKind.CONTRADICTS,1)
            out=compile_cognitive_turn(rt,'Valuta uno stato conflittuale e altamente incerto')
            self.assertIn(out['cycle']['kant_oracle']['self_state']['regulative_mode'],{'CRITIQUE','SYNTHESIS_REPAIR'})
            self.assertIn(out['central_oracle']['regulative_mode'],{'CRITIQUE','SYNTHESIS_REPAIR'})
            self.assertGreater(out['surface_a_contract']['regulation']['epistemic_caution'],.55)
            rt.close()

    def test_durable_tamper_of_response_evidence_fails_closed(self):
        import json
        from ikant.runtime import Runtime
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            out=compile_cognitive_turn(rt,'Rispondi con prudenza')
            rec=record_surface_a(rt,out['cycle']['cycle_id'],'Procederei con prudenza, verificando prima i punti incerti e mantenendo separate le ipotesi dalle prove disponibili.',intention_node_id=out['intention_node_id'])
            graph_path=rt.graph_path;state_dir=rt.state_dir;rid=rec['response_id'];rt.close()
            graph=json.loads(graph_path.read_text());graph['nodes'][rid]['evidence']=.8;graph_path.write_text(json.dumps(graph))
            with self.assertRaisesRegex(RuntimeError,'response evidence must be zero'):Runtime(state_dir)
            # Failed reopen must release the writer lock so the state can be repaired explicitly.
            from ikant.store import acquire_writer_lock
            lock=acquire_writer_lock(Path(td)/'repo'/'.ikant.writer.lock');lock.release()

    def test_durable_tamper_of_proto_self_boundary_fails_closed(self):
        import json
        from ikant.runtime import Runtime
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);compile_cognitive_turn(rt,'Mantieni continuità senza fare affermazioni di coscienza');state_path=rt.runtime_path;state_dir=rt.state_dir;rt.close()
            state=json.loads(state_path.read_text());state['cognitive']['proto_self']['is_consciousness_claim']=True;state_path.write_text(json.dumps(state))
            with self.assertRaisesRegex(RuntimeError,'proto-self consciousness boundary'):Runtime(state_dir)

    def test_response_recurrence_remains_zero_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            out=compile_cognitive_turn(rt,'Dimmi cosa faresti con cautela')
            text='Procederei con cautela, mantenendo espliciti i limiti e verificando i punti ancora incerti prima di qualsiasi azione materiale.'
            first=record_surface_a(rt,out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'])
            for _ in range(20):
                nxt=compile_cognitive_turn(rt,'Continua con lo stesso criterio')
                rec=record_surface_a(rt,nxt['cycle']['cycle_id'],text,intention_node_id=nxt['intention_node_id'])
                self.assertEqual(rec['response_id'],first['response_id'])
            self.assertEqual(rt.nodes[first['response_id']].evidence,0.0)
            self.assertLessEqual(len(rt.nodes[first['response_id']].metadata['response_cycles']),32)
            rt.close()


if __name__=='__main__': unittest.main()
