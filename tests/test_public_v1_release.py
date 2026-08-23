from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from ikant.public_v1 import PUBLIC_EXPERIENCE_SCHEMA,PUBLIC_RELEASE,conversation_projection,runtime_system_projection

ROOT=Path(__file__).resolve().parents[1]

class PublicV1ReleaseTests(unittest.TestCase):
 def test_release_identity_is_public_test_without_rewriting_protocol_versions(self):
  self.assertEqual(PUBLIC_RELEASE,'v1.0-public-test');self.assertEqual(PUBLIC_EXPERIENCE_SCHEMA,'ikant-public-experience/v1-test')
 def test_hidden_state_is_absolute_and_viewport_is_not_page_scrolled(self):
  css=(ROOT/'ikant/web/public-v1.css').read_text();self.assertIn('[hidden]{display:none!important}',css);self.assertIn('html,body{height:100%;overflow:hidden}',css);self.assertIn('.gate-stage',css);self.assertIn('.semantic-window',css)
 def test_acceptance_input_is_repaired_to_writable_and_ctas_are_state_reconciled(self):
  js=(ROOT/'ikant/web/public-v1.js').read_text();self.assertIn('keepAcceptanceWritable',js);self.assertIn('input.disabled=false',js);self.assertIn("removeAttribute('disabled')",js);self.assertIn('syncAdmission',js);self.assertNotIn("turn-form').addEventListener('submit'",js)
 def test_consumed_pair_code_has_actionable_recovery(self):
  js=(ROOT/'ikant/web/public-v1.js').read_text();self.assertIn('already consumed',js);self.assertIn('history.replaceState',js);self.assertIn('codice monouso',js.lower())
 def test_public_shell_has_transitions_and_reduced_motion_parity(self):
  css=(ROOT/'ikant/web/public-v1.css').read_text();self.assertIn('@keyframes viewIn',css);self.assertIn('@keyframes bubbleIn',css);self.assertIn('prefers-reduced-motion:reduce',css);self.assertIn('position:fixed',css)
 def test_ui_exposes_runtime_backed_conversation_epistemic_and_system_regions(self):
  html=(ROOT/'ikant/web/index.html').read_text();self.assertEqual(html.count('id="dashboard"'),1);self.assertIn('id="conversation-log"',html);self.assertIn('id="insight-strip"',html);self.assertIn('id="foundation-services"',html);self.assertIn('id="foundation-systems"',html);self.assertIn('id="foundation-meta"',html);self.assertNotIn('orbit-rail',html);self.assertNotIn('disabled',html)
 def test_public_endpoint_and_assets_are_authenticated_and_composed(self):
  http=(ROOT/'ikant/bootstrap_http.py').read_text();self.assertIn("path=='/api/v8/public'",http);self.assertIn('public_projection(service)',http);self.assertIn("'public-v1.js'",http);self.assertIn("'public-v1.css'",http);self.assertIn('if not self._guard():return',http)
 def test_conversation_projection_is_visible_chat_only_bounded_and_integrity_checked(self):
  src=(ROOT/'ikant/public_v1.py').read_text();self.assertIn('ChatLog',src);self.assertIn('VISIBLE_CHAT_LIMIT = 32',src);self.assertIn('VISIBLE_TEXT_BYTES = 6144',src);self.assertIn('integrity_verified',src);self.assertNotIn('chain_of_thought',src.lower())
 def test_runtime_system_cards_are_inspection_only_and_presence_bound(self):
  src=(ROOT/'ikant/public_v1.py').read_text();self.assertIn('ONLY_PERSISTED_RECOGNIZED_RUNTIME_PROJECTIONS',src);self.assertIn('"actionable": False',src);self.assertIn('"mode": "INSPECT"',src)
 def test_projection_helpers_fail_empty_in_absence_of_runtime(self):
  with tempfile.TemporaryDirectory() as td:
   c=conversation_projection(td);r=runtime_system_projection(td);self.assertEqual(c['records'],[]);self.assertFalse(c['integrity_verified']);self.assertEqual(r['systems'],[]);self.assertEqual(c['execution_authority'],0.0);self.assertEqual(r['epistemic_authority'],0.0)
 def test_service_navigation_is_derived_from_rendered_catalog_rows(self):
  foundation=(ROOT/'ikant/web/foundation.js').read_text();public=(ROOT/'ikant/web/public-v1.js').read_text();self.assertIn('row.dataset.service',foundation);self.assertIn("closest('[data-service]')",public);self.assertNotIn("shellCommand('TURN'",public)
 def test_service_worker_invalidates_pre_public_test_shell(self):
  sw=(ROOT/'ikant/web/sw.js').read_text();self.assertIn('foundation-v1-s12-public-v1-s13',sw);self.assertIn('/public-v1.js',sw);self.assertIn('/public-v1.css',sw);self.assertIn('caches.delete',sw)
 def test_s13_contract_is_preserved_under_corrective_s13bis(self):
  product=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text());self.assertEqual(product['constitutional_convergence'],'S13bis');s=next(x for x in product['slices'] if x['id']=='S13');self.assertEqual(s['schema'],PUBLIC_EXPERIENCE_SCHEMA);self.assertEqual(s['saturation'],{'cases':10000000,'mutations':10000000,'edges':100000,'tail':100000,'seed':20260823});ev=s['evidence'];self.assertEqual(ev['ux_e2e_trials'],10000000);self.assertEqual(ev['onto_epistemic_trials'],10000000);self.assertEqual(ev['surface_census_trials'],3000000);self.assertEqual(ev['edge_trials'],100000);self.assertEqual(ev['no_novelty_tail'],100000);self.assertEqual(ev['no_better_compression_tail'],100000);self.assertEqual(len(ev['seeds']),4);self.assertLess(product['slices'].index(s),len(product['slices'])-1)

if __name__=='__main__':unittest.main()
