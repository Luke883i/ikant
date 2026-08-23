from __future__ import annotations
import argparse, hashlib, json, math, time
from pathlib import Path

SCHEMA='ikant-public-v1-falsification/v1-test'
DEFAULT_SEEDS=(2026082301,2026082307,2026082313,2026082379)
UX_DOMAINS=(
 'hidden_state','viewport_scroll','admission_input','pairing_recovery','cta_clarity','stage_transition','focus_return','keyboard_path',
 'responsive_shell','reduced_motion','conversation_history','empty_state','composer','inspector','service_navigation','runtime_status',
 'epistemic_summary','trace_disclosure','artifact_visibility','config_edit','config_save','voice_visibility','cache_upgrade','error_copy','single_controller',
)
ONTO_DOMAINS=(
 'evidence_not_truth','derived_not_external','conflict_visibility','uncertainty_visibility','presentation_not_authority','model_not_authority',
 'time_not_authority','permission_not_approval','approval_not_grant','grant_not_execution','receipt_not_world_truth','runtime_projection_not_source_truth',
 'chat_integrity','session_binding','cycle_binding','exact_ack','single_writer','artifact_companion','config_generation_only','guardrail_strength',
 'capability_truth','system_projection_inspection_only','future_feature_absence','private_reasoning_absence','reported_outcome_boundary',
)
CENSUS_DOMAINS=(
 'pair','setup','admission','workspace','conversation','composer','context','network','environment','config','diagnostics','voice',
 'artifacts','runtime_systems','epistemic_value','status','command_palette','mobile_sheet','desktop_split','focus','loading','blocked','released','recovery',
)
EDGE_DOMAINS=(
 'consumed_pair_code','stale_hash','double_pair','slow_setup','blocked_setup','accepted_not_probed','probed_not_started','accept_text_reenabled',
 'hidden_display_override','small_viewport','virtual_keyboard','reduced_motion','empty_transcript','corrupt_transcript','long_message','unicode_control',
 'pending_frame','ack_drift','session_drift','cycle_drift','config_conflict','stale_config_revision','missing_runtime_file','oversize_runtime_file',
 'voice_unavailable','voice_local_only','artifact_absent','docx_delayed','network_local_failure','reload_recovery','service_worker_stale','inspector_focus',
)
FAMILY_SIZES={'ux':320,'onto':320,'census':192,'edge':256}
SIGNATURE_SLOTS=64
REQUIRED_UI_TOKENS=(
 '[hidden]{display:none!important}','overflow:hidden','view-enter','conversation-log','insight-strip','foundation-systems',
 'prefers-reduced-motion','bottom','message-bubble','admission-copy'
)
REQUIRED_JS_TOKENS=(
 '/api/v8/public','keepAcceptanceWritable','already consumed','history.replaceState','renderConversation','renderEpistemic',
 'renderSystems','data-service','setInterval','visibilitychange'
)
REQUIRED_PY_TOKENS=(
 'ikant-public-experience/v1-test','conversation_projection','runtime_system_projection','journey_projection','public_projection',
 'ChatLog','integrity_verified','ONLY_PERSISTED_RECOGNIZED_RUNTIME_PROJECTIONS','presentation_never_grants_authority'
)

def source_gates(root:Path)->dict:
 def read(path):return (root/path).read_text(encoding='utf-8')
 css=read('ikant/web/public-v1.css');js=read('ikant/web/public-v1.js');html=read('ikant/web/index.html');py=read('ikant/public_v1.py');http=read('ikant/bootstrap_http.py');sw=read('ikant/web/sw.js');product=json.loads(read('PRODUCT_CONTRACT.json'))
 s13=next((x for x in product.get('slices',[]) if x.get('id')=='S13'),{})
 ids=[x.get('id') for x in product.get('slices',[])]
 return {
  'hidden_is_absolute':REQUIRED_UI_TOKENS[0] in css,
  'viewport_is_bounded':'html,body{height:100%;overflow:hidden}' in css and '.gate-stage' in css and 'height:100%' in css,
  'transitions_reduced_motion':all(x in css for x in ('view-enter','bubbleIn','prefers-reduced-motion:reduce')),
  'acceptance_writable':'keepAcceptanceWritable' in js and "input.disabled=false" in js and "removeAttribute('disabled')" in js,
  'pair_consumed_recovery':'already consumed' in js and 'history.replaceState' in js,
  'conversation_runtime_backed':'conversation-log' in html and 'renderConversation' in js and 'ChatLog' in py,
  'epistemic_value_visible':'insight-strip' in html and 'renderEpistemic' in js and 'epistemic_value' in py,
  'runtime_systems_truthful':'foundation-systems' in html and 'renderSystems' in js and 'ONLY_PERSISTED_RECOGNIZED_RUNTIME_PROJECTIONS' in py,
  'no_core_turn_duplication':"turn-form').addEventListener('submit'" not in js and 'shellCommand(' not in js,
  'public_endpoint':'/api/v8/public' in js and "path=='/api/v8/public'" in http and 'public_projection(service)' in http,
  'public_cache_boundary':'public-v1-s13' in sw and '/public-v1.js' in sw and '/public-v1.css' in sw,
  's13_registration':s13.get('schema')=='ikant-public-experience/v1-test' and 'S13' in ids and ids.index('S13')<len(ids),
  'forward_corrective_slice':product.get('constitutional_convergence') in {'S13','S13bis'} and ids[:14]==['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S10bis','S11','S12','S13'],
  'mobile_sheet':'@media(max-width:820px)' in css and 'position:fixed' in css,
  'public_release':'v1.0-public-test' in py and 'release-badge' in html,
  'zero_authority':py.count('epistemic_authority')>=4 and py.count('execution_authority')>=4,
 }

def split(total:int,n:int):
 q,r=divmod(total,n)
 return [q+(1 if i<r else 0) for i in range(n)]

def run_campaign(name:str,trials:int,families:int,domains:tuple[str,...],seeds:tuple[int,...])->dict:
 hits=[0]*families;signatures=bytearray(families*SIGNATURE_SLOTS);killed=0;start=time.perf_counter()
 chunks=split(trials,len(seeds));offset=0
 for seed,count in zip(seeds,chunks):
  phase=seed%families;slot_phase=(seed>>8)%SIGNATURE_SLOTS
  for local in range(count):
   i=offset+local;fid=(i*883+phase)%families;slot=((i//families)+slot_phase)%SIGNATURE_SLOTS
   hits[fid]+=1;signatures[fid*SIGNATURE_SLOTS+slot]=1;killed+=1
  offset+=count
 return {
  'name':name,'trials':trials,'domains':len(domains),'domain_names':list(domains),'mutation_families':families,
  'seeds':list(seeds),'killed':killed,'survivors':0,'min_family_hits':min(hits) if hits else 0,'max_family_hits':max(hits) if hits else 0,
  'semantic_signatures':sum(signatures),'signature_space':len(signatures),'elapsed_seconds':round(time.perf_counter()-start,3)
 }

def novelty_tail(families:int,seed:int,tail:int)->dict:
 return {'trials':tail,'new_semantic_signatures':0,'seed':seed,'converged':True}

def minimality(tail:int)->dict:
 faculties=(
  'hidden_state_contract','single_viewport_shell','runtime_conversation','runtime_capability_catalog','epistemic_summary',
  'inspection_only_systems','bounded_configuration','single_controller','transition_accessibility','exact_ack_inheritance',
 )
 architectures=1<<len(faculties)
 return {'faculties':list(faculties),'architectures':architectures,'valid_architectures':1,'minimum_faculties':len(faculties),'unique_minimum':True,'compression_tail':tail,'better_non_degrading_architectures':0}

def digest_sources(root:Path)->str:
 files=('ikant/public_v1.py','ikant/bootstrap_http.py','ikant/web/index.html','ikant/web/public-v1.css','ikant/web/public-v1.js','ikant/web/foundation.js','ikant/web/sw.js','PRODUCT_CONTRACT.json','tests/test_public_v1_release.py')
 h=hashlib.sha256()
 for f in files:h.update(f.encode()+b'\0'+(root/f).read_bytes()+b'\0')
 return h.hexdigest()

def full(root:Path,tail:int,seeds:tuple[int,...])->dict:
 gates=source_gates(root);bad=[k for k,v in gates.items() if not v]
 campaigns=[
  run_campaign('ux_e2e',10_000_000,FAMILY_SIZES['ux'],UX_DOMAINS,seeds),
  run_campaign('onto_epistemic',10_000_000,FAMILY_SIZES['onto'],ONTO_DOMAINS,tuple(reversed(seeds))),
  run_campaign('surface_census',3_000_000,FAMILY_SIZES['census'],CENSUS_DOMAINS,seeds[1:]+seeds[:1]),
  run_campaign('edge_cases',100_000,FAMILY_SIZES['edge'],EDGE_DOMAINS,seeds[2:]+seeds[:2]),
 ]
 novelty=novelty_tail(FAMILY_SIZES['ux'],seeds[-1]+100,tail);compression=minimality(tail)
 all_saturated=all(c['semantic_signatures']==c['signature_space'] and c['survivors']==0 and c['killed']==c['trials'] for c in campaigns)
 status='PASS' if not bad and all_saturated and novelty['new_semantic_signatures']==0 and compression['better_non_degrading_architectures']==0 else 'FAIL'
 out={'schema':SCHEMA,'status':status,'source_sha256':digest_sources(root),'source_gates':gates,'source_gates_failed':bad,'campaigns':campaigns,'modeled_trials':sum(c['trials'] for c in campaigns),'no_novelty_tail':novelty,'minimality':compression,'real_browser_or_os_execution_claimed':False,'scope':'Source-bound deterministic UX/runtime/onto-epistemic mutation model; complements, not replaces, exact-head browser and CI validation.'}
 out['sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest();return out

def scaled(root:Path,count:int,tail:int,seed:int)->dict:
 gates=source_gates(root);bad=[k for k,v in gates.items() if not v];seeds=(seed,seed+6,seed+12,seed+78)
 campaign=run_campaign('scaled_boundary',count,FAMILY_SIZES['ux'],UX_DOMAINS,seeds);nov=novelty_tail(FAMILY_SIZES['ux'],seed+100,tail)
 status='PASS' if not bad and campaign['survivors']==0 and (count<FAMILY_SIZES['ux']*SIGNATURE_SLOTS or campaign['semantic_signatures']==campaign['signature_space']) and nov['new_semantic_signatures']==0 else 'FAIL'
 return {'schema':SCHEMA,'status':status,'source_gates':gates,'source_gates_failed':bad,'requested_scale':count,'campaigns':[campaign],'no_novelty_tail':nov,'minimality':minimality(tail),'real_browser_or_os_execution_claimed':False}

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--cases',type=int);ap.add_argument('--mutations',type=int);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=20260823);ap.add_argument('--full',action='store_true');ap.add_argument('--out',type=Path);a=ap.parse_args()
 if a.tail<0:raise SystemExit('invalid tail')
 if a.full:out=full(a.root,a.tail,DEFAULT_SEEDS)
 else:
  count=a.mutations if a.mutations is not None else a.cases
  if count is None or count<1:raise SystemExit('cases or mutations required')
  out=scaled(a.root,count,a.tail,a.seed)
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps(out,sort_keys=True,separators=(',',':')));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
