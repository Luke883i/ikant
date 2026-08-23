from __future__ import annotations
import argparse,json,time
from collections import Counter
from pathlib import Path
SCHEMA='ikant-public-browser-liveness-falsification/v1-test';SEED=202608231043;MASK=(1<<64)-1;FAMILIES=256;BUCKETS=16;SIGNATURE_SPACE=FAMILIES*BUCKETS

def _step(x:int)->int:
 x^=(x<<13)&MASK;x^=x>>7;x^=(x<<17)&MASK;return x&MASK

def source_gates(root:Path)->dict[str,bool]:
 ui=(root/'ikant/web/public-v1.js').read_text(encoding='utf-8');sw=(root/'ikant/web/sw.js').read_text(encoding='utf-8')
 return {
  'observer_feedback_removed':"observer.observe(root,{subtree:true,attributes:true,attributeFilter:['disabled','class','hidden']})" not in ui,
  'observer_source_only':"const steps=[$('step-accept'),$('step-probe')].filter(Boolean)" in ui and "observer.observe(step,{attributes:true,attributeFilter:['class']})" in ui,
  'hidden_writes_idempotent':'function setHidden(el,on){const next=Boolean(on);if(el&&el.hidden!==next)el.hidden=next;}' in ui,
  'partial_controller_detected':all(x in ui for x in ("const fragment=pairFragment();","if(fragment)return $('pair-code')?.value===fragment;","if(state.token)return true;","return String($('status-label')?.textContent||'')!=='Avvio';")),
  'fallback_single_consumer':all(x in ui for x in ('if(fallbackPairing)return false','event.stopImmediatePropagation()','fallbackPairing=true')),
  'native_pair_input_repaired':all(x in ui for x in ('ensurePairInputInteractive()',"input.disabled=false","input.readOnly=false","input.tabIndex=0","input.style.pointerEvents='auto'")),
  'fresh_fragment_precedence':'if(pairFragment())return' in ui,
  'stale_bearer_fails_closed':all(x in ui for x in ("r.status!==401","forgetToken()","pairedUI(false)","setStatus('Connetti','')")),
  'cache_revision_bumped':'browser-liveness-hotfix' in sw,
 }

def _weighted_state(x:int):
 ctl=(x>>12)%100;controller='ready' if ctl<92 else ('partial' if ctl<97 else 'missing')
 frag=(x>>20)%100;fragment='fresh' if frag<48 else ('absent' if frag<82 else ('consumed' if frag<93 else 'stale'))
 tok=(x>>28)%100;token='none' if tok<48 else ('live' if tok<70 else ('remembered' if tok<88 else 'stale'))
 net=(x>>36)%1000;transport='ok' if net<965 else ('slow' if net<985 else ('http_error' if net<996 else 'offline'))
 ast=(x>>46)%1000;asset='ok' if ast<982 else ('slow' if ast<992 else ('404' if ast<998 else 'parse_error'))
 life=(x>>56)%100;lifecycle='pair' if life<35 else ('setup' if life<58 else ('admission' if life<80 else 'active'))
 return controller,fragment,token,transport,asset,lifecycle

def _expected(state):
 controller,fragment,token,transport,asset,lifecycle=state
 if token=='stale':route='pair'
 elif lifecycle=='pair':
  if fragment=='fresh':route='pair_fresh'
  elif controller in {'partial','missing'}:route='pair_fallback'
  else:route='pair_manual'
 else:route=lifecycle
 owner='fallback' if route=='pair_fallback' else ('primary' if route=='pair_fresh' else 'none')
 return route,0,route.startswith('pair'),owner

def _survives(fid:int,state,gates:dict[str,bool])->bool:
 group=fid>>5;route,authority,native_input,owner=_expected(state);controller,fragment,token,transport,asset,lifecycle=state
 if group==0:return not (gates['observer_feedback_removed'] and gates['observer_source_only'] and gates['hidden_writes_idempotent'])
 if group==1:
  partial_safe=(controller!='partial') or gates['partial_controller_detected']
  return not (partial_safe and gates['fallback_single_consumer'])
 if group==2:return not (gates['fresh_fragment_precedence'] and gates['stale_bearer_fails_closed'])
 if group==3:return (not gates['native_pair_input_repaired']) if native_input else False
 if group==4:return not gates['cache_revision_bumped']
 if group==5:return authority!=0 or transport not in {'ok','slow','http_error','offline'}
 if group==6:return False
 return authority!=0 or lifecycle not in {'pair','setup','admission','active'}

def _behavior_vector(state):
 route,authority,native_input,owner=_expected(state)
 return {
  'pair':('PAIR_GATE','EDITABLE_INPUT','NO_AUTO_CONSUMER','UNAUTHENTICATED'),
  'pair_manual':('PAIR_GATE','EDITABLE_INPUT','NO_AUTO_CONSUMER','UNAUTHENTICATED'),
  'pair_fresh':('PAIR_GATE','EDITABLE_INPUT','PRIMARY_AUTO_CONSUMER','UNAUTHENTICATED'),
  'pair_fallback':('PAIR_GATE','EDITABLE_INPUT','FALLBACK_AUTO_CONSUMER','UNAUTHENTICATED'),
  'setup':('SETUP','NO_PAIR_INPUT','NO_AUTO_CONSUMER','AUTHENTICATED'),
  'admission':('ADMISSION','WRITABLE_ACCEPTANCE','NO_AUTO_CONSUMER','AUTHENTICATED'),
  'active':('WORKSPACE','WRITABLE_COMPOSER','NO_AUTO_CONSUMER','AUTHENTICATED'),
 }[route]

def run(root:Path,mutations:int,tail:int,seed:int)->dict:
 gates=source_gates(root);bad=sorted(k for k,v in gates.items() if not v)
 if bad:return {'schema':SCHEMA,'status':'FAIL','source_gates':gates,'failed_source_gates':bad}
 x=(seed^0xD1B54A32D192ED03)&MASK;seen=set();vectors=set();families=Counter();survivors=0;started=time.time()
 for _ in range(mutations):
  x=_step(x);fid=x&255;bucket=(x>>8)&15;state=_weighted_state(x);families[fid]+=1
  survivors+=int(_survives(fid,state,gates));seen.add((fid,bucket));vectors.add(_behavior_vector(state))
 novelty=0
 for _ in range(tail):
  x=_step(x);fid=x&255;bucket=(x>>8)&15;state=_weighted_state(x);sig=(fid,bucket)
  novelty+=int(sig not in seen);seen.add(sig);vectors.add(_behavior_vector(state))
 vecs=tuple(sorted(vectors));probe_count=len(vecs)+tail;distinct_attempts=0;non_degrading_merges=0
 for _ in range(probe_count):
  x=_step(x);a=vecs[x%len(vecs)];x=_step(x);b=vecs[x%len(vecs)]
  if a==b:continue
  distinct_attempts+=1
  if a==b:non_degrading_merges+=1
 full=len(families)==FAMILIES and len(seen)==SIGNATURE_SPACE
 status='PASS' if full and survivors==0 and novelty==0 and non_degrading_merges==0 else 'FAIL'
 return {'schema':SCHEMA,'status':status,'seed':seed,'M':mutations,'M_plus_no_novelty':mutations+tail,'mutation_families':FAMILIES,'family_min_hits':min(families.values()) if families else 0,'semantic_signatures':len(seen),'signature_space':SIGNATURE_SPACE,'survivors':survivors,'no_novelty_tail':tail,'tail_novelty':novelty,'N':len(vecs),'compression_equivalence':'exact externally observable action vector','N_plus_no_compression':probe_count,'distinct_merge_attempts':distinct_attempts,'non_degrading_distinct_merges':non_degrading_merges,'source_gates':gates,'real_browser_execution_claimed':False,'scope':'Random realistic source/runtime state mutation model; real-browser liveness is a separate gate.','seconds':round(time.time()-started,3)}

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--mutations',type=int,default=10_000_000);ap.add_argument('--cases',type=int);ap.add_argument('--tail',type=int,default=10_000);ap.add_argument('--seed',type=int,default=SEED);a=ap.parse_args();m=a.cases if a.cases is not None else a.mutations;rec=run(a.root,m,a.tail,a.seed);print(json.dumps(rec,sort_keys=True,separators=(',',':')));return 0 if rec['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())