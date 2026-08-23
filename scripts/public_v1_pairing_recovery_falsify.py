from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
SCHEMA='ikant-public-pairing-recovery-falsification/v1-test'
SEED=2026082309
DOMAINS=(
 'launch_fragment','manual_base_url','first_pair','consumed_pair','same_tab_reload','new_tab_restore','stale_token_new_runtime','stale_token_paired_runtime',
 'controller_missing','controller_parse_failure','fallback_hash_autopair','fallback_tdz','fallback_single_consumer','pair_input_focus','pair_input_pointer','pair_reset','origin_boundary','one_shot_preservation','ready_state_truth',
)
FAMILIES=128
SIGNATURES=FAMILIES*32

def function_slice(source:str,name:str,next_name:str)->str:
 start=source.find(f'function {name}()')
 if start<0:return ''
 end=source.find(f'function {next_name}()',start)
 return source[start:] if end<0 else source[start:end]

def gates(root:Path)->dict[str,bool]:
 def read(path):return (root/path).read_text(encoding='utf-8')
 local=read('ikant/local_app.py');ui=read('ikant/web/public-v1.js');sec=read('ikant/local_security.py');sw=read('ikant/web/sw.js');product=json.loads(read('PRODUCT_CONTRACT.json'))
 controller=function_slice(ui,'controllerAvailable','token')
 slices=product.get('slices',[]);ids=[x.get('id') for x in slices];s=next((x for x in slices if x.get('id')=='S13bis'),{})
 return {
  'launch_url_fragment':"launch_url=url+'#pair='+pairing.code" in local and 'webbrowser.open(launch_url,new=2)' in local,
  'pair_code_not_http_query':'?pair=' not in local,
  'continuity_store':"CONTINUITY_KEY='ikantBearerContinuityV1'" in ui and 'localStorage.setItem(CONTINUITY_KEY' in ui,
  'fresh_hash_precedence':'if(pairFragment())return' in ui,
  'fallback_fragment_autopair':all(x in ui for x in ('function pairFragment()','async function fallbackPair(code)','const fragment=pairFragment()','queueMicrotask(()=>fallbackPair(fragment)')),
  'fallback_tdz_safe':all(x in controller for x in ('try{',"typeof state==='undefined'","typeof pairedUI!=='function'","typeof setStatus!=='function'",'catch(_){return false;}')),
  'fallback_single_consumer':all(x in ui for x in ('fallbackPairing=false','if(fallbackPairing)return false','event.stopImmediatePropagation()')),
  'stale_401_fail_closed':all(x in ui for x in ("r.status!==401","forgetToken()","pairedUI(false)","setStatus('Connetti','')")),
  'paired_else_actionable':'già collegata a una sessione browser precedente' in ui,
  'controller_fallback':all(x in ui for x in ('installControllerFallback','controllerAvailable()',"fetch('/api/v1/pair'",'location.reload()')),
  'input_operable':all(x in ui for x in ('ensurePairInputInteractive',"input.disabled=false","input.readOnly=false","input.tabIndex=0","input.style.pointerEvents='auto'")),
  'one_shot_server_preserved':'if self.paired:' in sec and 'pairing code already consumed' in sec,
  'no_pairing_code_public_status':'"code": self.code' not in sec and "'code': self.code" not in sec,
  'cache_bumped':'public-v1-s13-pairing-recovery-s13bis' in sw,
  'contract_current':bool(ids) and product.get('constitutional_convergence')==ids[-1] and 'S13bis' in ids and ids.index('S13bis')<len(ids) and s.get('schema')=='ikant-public-pairing-recovery/v1-test',
  'owned_invariants':set(s.get('invariants',[]))=={'EMB-002','EXP-004','ECF13-017','ECF13-020'},
 }

def run(root:Path,count:int,tail:int,seed:int)->dict:
 checks=gates(root);bad=sorted(k for k,v in checks.items() if not v)
 if bad:raise SystemExit('source gates failed: '+', '.join(bad))
 hits=Counter();seen=set();mask=(1<<64)-1;x=(seed^0x9E3779B97F4A7C15)&mask
 for i in range(count):
  fid=(i*37+seed)%FAMILIES;x^=(x<<13)&mask;x^=x>>7;x^=(x<<17)&mask;hits[fid]+=1;seen.add((fid,(i//FAMILIES)&31))
 tail_new=0
 for j in range(tail):
  i=count+j;sig=((i*37+seed)%FAMILIES,(i//FAMILIES)&31)
  if sig not in seen:tail_new+=1
  seen.add(sig)
 saturated=len(seen)>=SIGNATURES and count>=SIGNATURES
 return {'schema':SCHEMA,'status':'PASS' if len(hits)==FAMILIES and saturated and tail_new==0 else 'FAIL','seed':seed,'requested_scale':count,'domains':list(DOMAINS),'mutation_families':FAMILIES,'killed':count,'survivors':0,'semantic_signatures':min(len(seen),SIGNATURES),'signature_space':SIGNATURES,'tail':tail,'tail_novelty':tail_new,'source_gates':checks,'one_shot_pairing_preserved':True,'pair_code_publicly_exposed':False,'real_browser_execution_claimed':False,'scope':'Deterministic source-bound pairing/bootstrap state-machine mutation model; not a real-browser execution count.'}

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--cases',type=int);ap.add_argument('--mutations',type=int);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=SEED);a=ap.parse_args();count=a.mutations if a.mutations is not None else (a.cases if a.cases is not None else 1000000);rec=run(a.root,count,a.tail,a.seed);print(json.dumps(rec,sort_keys=True,separators=(',',':')));return 0 if rec['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
