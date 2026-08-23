from pathlib import Path
import unittest
from ikant.reactive_hybrid import WorkStore,build_graph,compile_command,hybrid_membrane

class ReactiveHybridS15Tests(unittest.TestCase):
 def test_known_open_command_compiles_without_inference_or_execution_authority(self):
  p=compile_command('Apri Firefox e Word');self.assertEqual(p['targets'],['firefox','word']);self.assertFalse(p['inference_required']);self.assertEqual(p['execution_authority'],0.0);self.assertEqual(build_graph('Apri Firefox e Word')['units'][0]['route'],'DETERMINISTIC_COMMAND_MAP')
 def test_unknown_or_shellish_commands_fail_closed(self):
  for text in ('Apri UnknownApp','Apri Firefox --private-window','Apri /usr/bin/firefox','Apri https://example.com'):self.assertIsNone(compile_command(text))
 def test_private_or_material_turn_quarantines_whole_turn(self):
  for text in ('Confronta A. Verifica /home/user/private.txt.','Analizza le mie preferenze politiche.','Confronta A. Poi compra B.'):self.assertEqual(hybrid_membrane(build_graph(text),enabled=True,opt_in=True,provider='openai')['route'],'LOCAL_ONLY')
 def test_abstract_exportable_turn_can_cross_only_as_zero_authority(self):
  out=hybrid_membrane(build_graph('Confronta architettura A e B.'),enabled=True,opt_in=True,provider='anthropic');self.assertEqual(out['route'],'HYBRID_ABSTRACT');self.assertFalse(out['raw_prompt_exportable']);self.assertFalse(out['tool_calls_allowed']);self.assertEqual(out['execution_authority'],0.0)
 def test_work_projection_is_identifier_free_and_terminal_only_after_delivery(self):
  s=WorkStore();wid,_=s.begin('secret-session','Confronta A e B.');p=s.projection('secret-session');self.assertTrue(p['active']);self.assertFalse(p['identifiers_exposed']);self.assertNotIn('session',p);s.bind_cycle(wid,'c1');s.advance(wid,'SEALED');self.assertTrue(s.projection('secret-session')['active']);s.deliver_current('secret-session');self.assertFalse(s.projection('secret-session')['active'])
 def test_phase_skip_fails_closed(self):
  s=WorkStore();wid,_=s.begin('s','Confronta A e B.')
  with self.assertRaises(RuntimeError):s.advance(wid,'DELIVERED')
 def test_capacity_never_evicts_active_work(self):
  s=WorkStore(max_works=4);ids=[s.begin(f's{i}','Confronta A e B.')[0] for i in range(4)]
  with self.assertRaises(RuntimeError):s.begin('overflow','Confronta A e B.')
  s.fail(ids[0]);s.begin('replacement','Confronta A e B.')
 def test_web_progress_is_single_flight_stale_safe_and_progressive(self):
  src=Path('ikant/web/reactive-hybrid.js').read_text();self.assertIn('polling||local!==epoch',src);self.assertIn("s.textContent='Dettagli'",src);self.assertNotIn('innerHTML',src);self.assertNotIn('progress_fraction',src)
 def test_http_wrapper_preserves_canonical_shell_command_and_ack(self):
  src=Path('ikant/reactive_http.py').read_text();self.assertIn('service.shell_command(body)',src);self.assertIn('service.shell_ack(body)',src);self.assertIn("'/api/v9/work/current'",src);self.assertNotIn('service.turn(',src)

if __name__=='__main__':unittest.main()
