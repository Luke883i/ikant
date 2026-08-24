import subprocess,tempfile,unittest,sys
from pathlib import Path

from ikant.causal_ledger import begin_turn,causal_projection,reconcile_restart
from ikant.runtime import Runtime
from ikant.session_egress import activate_runtime_egress
from ikant.session_host import DashboardOnlySession,prepare_text_frame
from ikant.runtime_recovery import materialize_recovery_frame
from tests.helpers import active_runtime

GOOD='Procederei con prudenza, mantenendo separati fatti, inferenze e vincoli locali e senza attribuire autorità materiale alla risposta.'

class CausalLedgerS18Tests(unittest.TestCase):
    def test_preprepare_rollback_restores_durable_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);sd=rt.state_dir
            before=rt.runtime_path.read_bytes();begin_turn(rt);rt.runtime['s18_uncommitted_probe']='must_disappear';rt._write_runtime()
            result=reconcile_restart(rt);self.assertEqual(result['state'],'ROLLED_BACK_PREPARE');rt.close()
            self.assertEqual((sd/'runtime.json').read_bytes(),before)
            reopened=Runtime(sd);self.assertNotIn('s18_uncommitted_probe',reopened.runtime);self.assertEqual(causal_projection(reopened)['last_terminal']['event'],'TURN_ABORTED');reopened.close()

    def test_canonical_exact_ack_is_only_commit_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);activate_runtime_egress(rt,initialization=True);session=DashboardOnlySession(rt)
            begin=session.begin_user('valuta questo punto',engine_label='GPT-5.6 Sol');out=begin['machine'];cycle=out['cycle']['cycle_id']
            self.assertIsNotNone(causal_projection(rt)['active'])
            session.controller.close(cycle,GOOD,intention_node_id=out['intention_node_id'])
            prepared=prepare_text_frame(rt,'S18 canonical exact-ACK frame',kind='TURN',cycle_id=cycle)
            self.assertEqual(causal_projection(rt)['active']['stage'],'FRAME_SEALED')
            session.acknowledge(prepared,prepared['text']);p=causal_projection(rt);self.assertIsNone(p['active']);self.assertEqual(p['last_terminal']['event'],'TURN_COMMITTED');rt.close()

    def test_s17bis_interruption_recovery_aborts_not_commits(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True);activate_runtime_egress(rt,initialization=True);session=DashboardOnlySession(rt)
            begin=session.begin_user('turno che verra interrotto',engine_label='GPT-5.6 Sol');cycle=begin['machine']['cycle']['cycle_id']
            recovery=materialize_recovery_frame(rt);self.assertIsNotNone(recovery);self.assertEqual(recovery['receipt']['kind'],'RECOVERY');self.assertEqual(recovery['receipt']['cycle_id'],cycle)
            session.acknowledge(recovery,recovery['text']);p=causal_projection(rt);self.assertIsNone(p['active']);self.assertEqual(p['last_terminal']['event'],'TURN_ABORTED');rt.close()

    def test_real_subprocess_preprepare_crash_oracle(self):
        root=Path(__file__).resolve().parents[1]
        proc=subprocess.run([sys.executable,'scripts/s18_process_crash_oracle.py'],cwd=root,capture_output=True,text=True,check=True)
        self.assertIn('"status": "PASS"',proc.stdout)

if __name__=='__main__':unittest.main()
