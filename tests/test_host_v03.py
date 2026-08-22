import json,tempfile,unittest
from pathlib import Path
from ikant.host import conforming_turn,emit_conforming_surface_a
from ikant.runtime import Runtime
from tests.helpers import active_runtime

class HostV03Tests(unittest.TestCase):
    def test_identity_turn_requires_ikant_first_then_engine(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            out=conforming_turn(rt,'ciao, chi sei?',engine_label='GPT-5.6 Sol')
            bad='Sono GPT-5.6 Sol e uso iKant come struttura locale per governare questa sessione.'
            with self.assertRaisesRegex(ValueError,'identity_order_violation'):
                emit_conforming_surface_a(rt,out['cycle']['cycle_id'],bad,intention_node_id=out['intention_node_id'])
            good='Sono iKant, eseguito con motore GPT-5.6 Sol. Il motore fornisce capacità linguistiche e di ragionamento, mentre iKant governa questa interazione locale.'
            rec=emit_conforming_surface_a(rt,out['cycle']['cycle_id'],good,intention_node_id=out['intention_node_id'])
            self.assertTrue(rec['interaction_validated']);self.assertEqual(rec['evidence'],0);rt.close()

    def test_engine_binding_is_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            out=conforming_turn(rt,'dimmi il prossimo passo',engine_label='GPT-5.6 Sol')
            text='Procederei con cautela, mantenendo separati i fatti verificati dalle inferenze e controllando i vincoli locali prima di qualsiasi passo materiale.'
            emit_conforming_surface_a(rt,out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'])
            with self.assertRaisesRegex(PermissionError,'host engine binding mismatch'):
                conforming_turn(rt,'continua',engine_label='different-engine')
            rt.close()

    def test_tampered_host_binding_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);state=rt.runtime_path;sd=rt.state_dir
            out=conforming_turn(rt,'dimmi il prossimo passo',engine_label='GPT-5.6 Sol')
            emit_conforming_surface_a(rt,out['cycle']['cycle_id'],'Procederei con prudenza, mantenendo verificabili i limiti e senza trasformare inferenze interne in nuove prove.',intention_node_id=out['intention_node_id']);rt.close()
            data=json.loads(state.read_text());data['host']['engine_label']='tampered-engine';state.write_text(json.dumps(data))
            reopened=Runtime(sd)
            with self.assertRaisesRegex(RuntimeError,'host engine binding receipt mismatch'):
                conforming_turn(reopened,'continua',engine_label='tampered-engine')
            reopened.close()

    def test_pending_turn_must_close_before_next_turn(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            out=conforming_turn(rt,'prima intenzione',engine_label='GPT-5.6 Sol')
            with self.assertRaisesRegex(RuntimeError,'pending Surface A emission'):
                conforming_turn(rt,'seconda intenzione',engine_label='GPT-5.6 Sol')
            emit_conforming_surface_a(rt,out['cycle']['cycle_id'],'Procederei con ordine, chiudendo prima la risposta corrente e mantenendo separati fatti, inferenze e vincoli locali.',intention_node_id=out['intention_node_id']);rt.close()

    def test_one_cycle_one_emission(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            out=conforming_turn(rt,'rispondi brevemente',engine_label='GPT-5.6 Sol');text='Rispondo in modo breve e verificabile, mantenendo separati i fatti dalle inferenze e rispettando il contratto locale della sessione.'
            emit_conforming_surface_a(rt,out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'])
            with self.assertRaisesRegex(PermissionError,'single pending'):
                emit_conforming_surface_a(rt,out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'])
            rt.close()

    def test_surface_b_json_is_mandatory_and_docx_is_not_preprimary(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            out=conforming_turn(rt,'valuta questo punto',engine_label='GPT-5.6 Sol')
            self.assertTrue(Path(out['surface_b_json']).exists());self.assertNotIn('surface_b_docx',out)
            cycle=out['cycle']['cycle_id'];self.assertFalse((rt.state_dir/'artifacts'/f'CRC_SNAPSHOT_{cycle}.docx').exists())
            snap=json.loads(Path(out['surface_b_json']).read_text());self.assertIn('interaction_contract',snap['dynamic_state']);self.assertEqual(snap['dynamic_state']['host_binding']['interface_identity'],'iKant');rt.close()

if __name__=='__main__':unittest.main()
