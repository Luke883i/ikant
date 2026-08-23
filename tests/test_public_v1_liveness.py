from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PublicV1LivenessTests(unittest.TestCase):
 def test_admission_observer_never_observes_its_own_presentation_writes(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  self.assertNotIn("observer.observe(root,{subtree:true,attributes:true,attributeFilter:['disabled','class','hidden']})",ui)
  self.assertIn("const steps=[$('step-accept'),$('step-probe')].filter(Boolean)",ui)
  self.assertIn("observer.observe(step,{attributes:true,attributeFilter:['class']})",ui)
  self.assertIn('function setHidden(el,on){const next=Boolean(on);if(el&&el.hidden!==next)el.hidden=next;}',ui)
 def test_partial_primary_controller_is_not_mistaken_for_completed_bootstrap(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  for marker in ("const fragment=pairFragment();","if(fragment)return $('pair-code')?.value===fragment;","if(state.token)return true;","return String($('status-label')?.textContent||'')!=='Avvio';"):
   self.assertIn(marker,ui)
 def test_pairing_input_remains_native_and_fallback_is_single_consuming(self):
  ui=(ROOT/'ikant/web/public-v1.js').read_text(encoding='utf-8')
  for marker in ('ensurePairInputInteractive()',"input.disabled=false","input.readOnly=false","input.tabIndex=0","input.style.pointerEvents='auto'",'if(fallbackPairing)return false','event.stopImmediatePropagation()'):
   self.assertIn(marker,ui)
 def test_liveness_fix_invalidates_stale_public_shell_cache(self):
  sw=(ROOT/'ikant/web/sw.js').read_text(encoding='utf-8')
  self.assertIn('browser-liveness-hotfix',sw)
 def test_launcher_still_binds_one_shot_pair_fragment(self):
  local=(ROOT/'ikant/local_app.py').read_text(encoding='utf-8')
  self.assertIn("launch_url=url+'#pair='+pairing.code",local)
  self.assertIn('webbrowser.open(launch_url,new=2)',local)

if __name__=='__main__':unittest.main()