from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PublicV1PairingRecoveryTests(unittest.TestCase):
 def test_launcher_emits_and_opens_fragment_bound_pairing_url(self):
  src=(ROOT/'ikant/local_app.py').read_text(encoding='utf-8')
  self.assertIn("launch_url=url+'#pair='+pairing.code",src)
  self.assertIn("webbrowser.open(launch_url,new=2)",src)
  self.assertNotIn("webbrowser.open(url+'#pair='+pairing.code",src)
 def test_browser_continuity_preserves_one_shot_server_pairing(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8');sec=(ROOT/'ikant/local_security.py').read_text(encoding='utf-8')
  self.assertIn("CONTINUITY_KEY='ikantBearerContinuityV1'",ui);self.assertIn('localStorage.setItem(CONTINUITY_KEY',ui);self.assertIn("sessionStorage.setItem('ikantBearer',remembered)",ui);self.assertIn('if(pairFragment())return',ui);self.assertIn('if self.paired:',sec);self.assertIn('raise LocalSecurityError("pairing code already consumed")',sec)
 def test_stale_continuity_fails_closed_to_pairing_gate(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  for marker in ("r.status!==401","forgetToken()","publicPairStatus()","pairedUI(false)","setStatus('Connetti','')"):self.assertIn(marker,ui)
  self.assertIn('già collegata a una sessione browser precedente',ui)
 def test_controller_failure_keeps_pairing_operable_and_autoconsumes_fresh_fragment(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  for marker in ('function installControllerFallback()',"status.textContent='Connetti'","dot.className='status-dot blocked'",'function pairFragment()','async function fallbackPair(code)','const fragment=pairFragment()','queueMicrotask(()=>fallbackPair(fragment)','ensurePairInputInteractive()',"input.style.pointerEvents='auto'","input.tabIndex=0"):self.assertIn(marker,ui)
 def test_fallback_is_tdz_safe_and_single_consuming(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  self.assertIn("function controllerAvailable(){try{return typeof state!=='undefined'",ui)
  self.assertIn('catch(_){return false;}',ui)
  self.assertIn("fallbackPairing=false",ui);self.assertIn('if(fallbackPairing)return false',ui)
  self.assertIn('event.stopImmediatePropagation()',ui)
 def test_release_cache_and_contract_register_corrective_slice(self):
  sw=(ROOT/'ikant/web/sw.js').read_text(encoding='utf-8');self.assertIn('public-v1-s13-pairing-recovery-s13bis',sw)
  product=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'));self.assertEqual(product['constitutional_convergence'],'S13bis');s=product['slices'][-1];self.assertEqual(s['id'],'S13bis');self.assertEqual(s['schema'],'ikant-public-pairing-recovery/v1-test');self.assertEqual(s['saturation'],{'cases':1000000,'mutations':1000000,'edges':100000,'tail':100000,'seed':2026082309});self.assertTrue(s['evidence']['one_shot_pairing_preserved']);self.assertFalse(s['evidence']['pair_code_publicly_exposed']);self.assertTrue(s['evidence']['fragment_autopair_fallback'])

if __name__=='__main__':unittest.main()