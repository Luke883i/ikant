from pathlib import Path
import unittest
from unittest.mock import patch
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
 def test_begin_failure_cannot_orphan_active_session(self):
  s=WorkStore()
  with patch('ikant.reactive_hybrid.build_graph',side_effect=RuntimeError('synthetic compile failure')):
   with self.assertRaises(RuntimeError):s.begin('session-x','Confronta A e B.')
  self.assertFalse(s.active('session-x'));self.assertEqual(s.projection('session-x')['phase'],'IDLE')
 def test_canonical_frame_seal_is_monotonic_and_projection_drift_is_non_authoritative(self):
  s=WorkStore();wid,_=s.begin('s','Confronta A e B.');s.seal_from_canonical(wid,'cycle-a');p=s.projection('s');self.assertEqual(p['phase'],'SEALED');self.assertTrue(p['active']);self.assertTrue(p['cycle_bound'])
  s.seal_from_canonical(wid,'cycle-b');p=s.projection('s');self.assertEqual(p['phase'],'SEALED');self.assertEqual(p['facts']['projection_degraded'],'cycle_binding_drift');self.assertEqual(p['execution_authority'],0.0)
  s.deliver_current('s');self.assertEqual(s.projection('s')['phase'],'DELIVERED')
 def test_web_progress_is_single_flight_stale_safe_and_progressive(self):
  src=Path('ikant/web/reactive-hybrid.js').read_text();self.assertIn('polling||local!==epoch',src);self.assertIn("s.textContent='Dettagli'",src);self.assertNotIn('innerHTML',src);self.assertNotIn('progress_fraction',src)
 def test_http_wrapper_preserves_canonical_shell_command_ack_and_post_frame_monotonicity(self):
  src=Path('ikant/reactive_http.py').read_text();self.assertIn('service.shell_command(body)',src);self.assertIn('service.shell_ack(body)',src);self.assertIn("'/api/v9/work/current'",src);self.assertNotIn('service.turn(',src);self.assertIn('seal_from_canonical',src);self.assertIn('not canonical_frame',src)
 def test_real_browser_gate_executes_reactive_http_slow_turn_fixture(self):
  wrapper=Path('scripts/public_v1_browser_liveness.mjs').read_text();probe=Path('scripts/reactive_hybrid_browser_liveness.mjs').read_text();fixture=Path('scripts/reactive_hybrid_browser_fixture.py').read_text()
  self.assertIn('runReactiveHybridBrowserLiveness',wrapper);self.assertIn('/api/v9/work/current',probe);self.assertIn('/api/v2/shell/command',probe);self.assertIn('/api/v2/shell/ack',probe);self.assertIn('from ikant.reactive_http import build_server',fixture)

if __name__=='__main__':unittest.main()
