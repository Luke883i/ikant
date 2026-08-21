from __future__ import annotations
import json,unittest
from pathlib import Path
from ikant import __version__
from ikant.advanced_web_shell import ADVANCED_WEB_SHELL_SCHEMA,SHELL_COMMAND_SCHEMA,SHELL_ACK_SCHEMA,MAX_SHELL_OPERATIONS
from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids,registry_manifest
ROOT=Path(__file__).parents[1]

class ProductConvergenceV26Tests(unittest.TestCase):
 def test_v26_identity_converges(self):
  self.assertEqual(PRODUCT_VERSION,'0.26.0a1');self.assertEqual(__version__,PRODUCT_VERSION);self.assertEqual(registry_manifest()['product_version'],PRODUCT_VERSION);self.assertEqual(INVARIANT_REGISTRY_SCHEMA,'ikant-invariant-registry/v0.26-test')
 def test_s8_is_current_registered_slice(self):
  c=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual(c['schema'],'ikant-product-contract/v0.26-test');self.assertEqual([x['id'] for x in c['slices']],['S1','S2','S3','S4','S5','S6','S7','S8']);self.assertEqual(c['constitutional_convergence'],'S8');s=c['slices'][-1];self.assertEqual(s['schema'],ADVANCED_WEB_SHELL_SCHEMA);self.assertEqual(set(s['invariants']),{'AWS-001','AWS-002','AWS-003'});self.assertEqual(s['saturation'],{'cases':1000000,'mutations':10000000,'edges':1000000,'tail':100000,'seed':883})
 def test_shell_protocol_and_invariants_are_constitutional(self):
  self.assertEqual(ADVANCED_WEB_SHELL_SCHEMA,'ikant-advanced-web-shell/v0.26-test');self.assertEqual(SHELL_COMMAND_SCHEMA,'ikant-advanced-web-shell-command/v0.26-test');self.assertEqual(SHELL_ACK_SCHEMA,'ikant-advanced-web-shell-ack/v0.26-test');self.assertEqual(MAX_SHELL_OPERATIONS,4096);self.assertTrue({'AWS-001','AWS-002','AWS-003'}<=set(critical_ids()))
 def test_manifests_expose_shell_noncollapse(self):
  for name in ('ADMISSION.json','BOOTSTRAP.json'):
   m=json.loads((ROOT/name).read_text(encoding='utf-8'));s=m['advanced_web_shell'];self.assertEqual(s['schema'],ADVANCED_WEB_SHELL_SCHEMA);self.assertTrue(s['single_writer']);self.assertTrue(s['runtime_session_bound']);self.assertTrue(s['monotonic_sequence']);self.assertTrue(s['whole_session_idempotency_keys']);self.assertTrue(s['exact_previous_frame_binding']);self.assertTrue(s['legacy_active_mutations_blocked_after_claim']);self.assertEqual(s['semantic_output_channel'],'HSPV2_SEALED_DASHBOARD_ONLY');self.assertFalse(s['browser_is_authority']);self.assertFalse(s['shell_state_is_authority']);self.assertEqual(s['epistemic_authority'],0.0);self.assertEqual(s['execution_authority'],0.0)
 def test_canonical_pwa_and_docs_bind_s8(self):
  js=(ROOT/'ikant'/'web'/'app.js').read_text(encoding='utf-8');app=(ROOT/'ikant'/'local_app.py').read_text(encoding='utf-8');self.assertIn('/api/v2/shell/open',js);self.assertIn('/api/v2/shell/command',js);self.assertIn('/api/v2/shell/ack',js);self.assertNotIn("'/api/v1/turn'",js);self.assertIn('AdvancedWebShellService',app);self.assertTrue((ROOT/'docs'/'S8_ADVANCED_WEB_SHELL.md').is_file())
if __name__=='__main__':unittest.main()
