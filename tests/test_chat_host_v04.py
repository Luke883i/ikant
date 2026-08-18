import json,tempfile,unittest
from pathlib import Path
from ikant.chat_session import ChatController,ChatIntegrityError,ChatLog
from ikant.dashboard import project_dashboard
from ikant.model import Layer,NodeKind
from ikant.runtime import Runtime
from tests.helpers import active_runtime

class ChatHostV04Tests(unittest.TestCase):
    def test_real_durable_roundtrip_reopen_and_dashboard(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);controller=ChatController(rt)
            out=controller.begin('ciao, chi sei?',engine_label='GPT-5.6 Sol')
            text='Sono iKant, con motore GPT-5.6 Sol. Mantengo questa sessione locale con telemetria verificabile e senza inventare nuove prove.'
            rec=controller.close(out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'],user_seq=out['chat']['user_seq'])
            self.assertTrue(rec['interaction_validated']);self.assertEqual(rec['chat_record']['role'],'ikant');self.assertEqual(rec['chat_record']['reply_to_seq'],out['chat']['user_seq'])
            self.assertTrue(controller.log.verify()['ok']);self.assertTrue((rt.state_dir/'dashboard.json').exists());self.assertTrue((rt.state_dir/'dashboard.txt').exists());self.assertEqual(rt.nodes[rec['response_id']].evidence,0)
            state_dir=rt.state_dir;session=rt.runtime['session_id'];rt.close()
            reopened=Runtime(state_dir);log=ChatLog(state_dir/'chat'/'transcript.jsonl',runtime_session_id=session);self.assertTrue(log.verify()['ok']);dash=project_dashboard(reopened);self.assertTrue(dash['surface_b']['available']);self.assertFalse(dash['contract']['may_modify_runtime_evidence']);reopened.close()

    def test_pending_turn_blocks_new_visible_input_before_append(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);controller=ChatController(rt);out=controller.begin('valuta il prossimo passo',engine_label='GPT')
            before=controller.log.rows();self.assertEqual(len(before),1)
            with self.assertRaises(RuntimeError):controller.begin('secondo input non ammesso',engine_label='GPT')
            self.assertEqual(controller.log.rows(),before);controller.close(out['cycle']['cycle_id'],'Procederei con cautela, mantenendo verificabili i presupposti e chiudendo prima questo turno locale.',intention_node_id=out['intention_node_id']);rt.close()

    def test_duplicate_surface_close_does_not_duplicate_chat_reply(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);controller=ChatController(rt);out=controller.begin('continua con prudenza',engine_label='GPT')
            text='Continuerei con prudenza, verificando i limiti attuali prima di qualsiasi passo materiale nella sessione locale.'
            controller.close(out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id']);rows=controller.log.rows()
            with self.assertRaises(PermissionError):controller.close(out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'])
            self.assertEqual(controller.log.rows(),rows);rt.close()

    def test_chat_tamper_is_detected_by_chat_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);controller=ChatController(rt);out=controller.begin('ciao',engine_label='GPT');controller.close(out['cycle']['cycle_id'],'Ciao, sono iKant e mantengo il turno locale in forma verificabile e sintetica.',intention_node_id=out['intention_node_id']);p=controller.log.path;session=rt.runtime['session_id'];rt.close()
            lines=p.read_text().splitlines();row=json.loads(lines[0]);row['text']='tampered';lines[0]=json.dumps(row);p.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(ChatIntegrityError):ChatLog(p,runtime_session_id=session).verify()

    def test_dashboard_projection_never_changes_node_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='sentinel evidence',confidence=.8,evidence=.37,source_mode='document');before=n.evidence;controller=ChatController(rt);out=controller.begin('valuta il sentinel',engine_label='GPT');after_begin=rt.nodes[n.id].evidence;project_dashboard(rt);self.assertEqual(rt.nodes[n.id].evidence,after_begin);self.assertEqual(before,after_begin);controller.close(out['cycle']['cycle_id'],'Il sentinel resta invariato come evidenza; la dashboard lo osserva senza modificarne il peso epistemico.',intention_node_id=out['intention_node_id']);self.assertEqual(rt.nodes[n.id].evidence,before);rt.close()

if __name__=='__main__':unittest.main()
