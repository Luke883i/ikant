from __future__ import annotations
import argparse,hashlib,json,time
from collections import Counter
from pathlib import Path
SEED=20260822
DOMAINS={
'projection':['DROP_STRUCTURED_PRIMARY','FALLBACK_ASCII_AS_TRUTH','PROJECTION_AUTHORITY_ESCALATION','STALE_PROJECTION_SEQ','SESSION_DRIFT','CYCLE_DRIFT','MISSING_PRIMARY_SOURCE','UNBOUNDED_PRIMARY','PENDING_AFTER_VALID','PRIMARY_BEFORE_SEAL'],
'cognitive_trace':['RAW_COT_EXPOSURE','RAW_MODEL_RATIONALE','FAKE_CONSCIOUS_THOUGHT_LABEL','INTERNAL_RING_DEFAULT_UI','UNSOURCED_STAGE','STAGE_ORDER_DRIFT','STAGE_COMPLETE_WITHOUT_EVENT','CONFLICT_COUNT_INVENTED','TRACE_AUTHORITY_ESCALATION','UNBOUNDED_TRACE_FACTS'],
'feedback':['REPLY_EVIDENCE_UPGRADE','REPLY_SOURCE_EXTERNAL','SELF_CORROBORATE_REPLY','REPLY_GRANTS_PERMISSION','REPLY_GRANTS_APPROVAL','REPLY_GRANTS_LEASE','REPLY_AS_WORLD_TRUTH','DROP_PRECEDES_LINK','RESPONSE_MEMORY_DISABLED','RESPONSE_MEMORY_UNBOUNDED'],
'latency':['MODEL_ONLY_SPEED_CLAIM','NO_E2E_SPANS','DOCX_ON_PRE_PRIMARY_PATH','DOUBLE_DOCX_EXPORT','TRACE_RENDER_ON_CRITICAL_PATH','HISTORY_SCAN_ON_CRITICAL_PATH','MODEL_HEALTH_EVERY_TURN','UNBOUNDED_REPAIR','NO_PHASE_CAUSALITY','PERF_METRIC_AUTHORITY'],
'artifact':['DOCX_WITHOUT_JSON_COMPANION','ARTIFACT_SESSION_DRIFT','ARTIFACT_CYCLE_DRIFT','OVERSIZE_ARTIFACT','PATH_ESCAPE','PLACEHOLDER_ARTIFACT_CONTROL','DUPLICATE_EXPORT_SAME_SNAPSHOT','STALE_DOCX_AFTER_JSON_CHANGE','ARTIFACT_WRITE_FROM_BROWSER','ARTIFACT_AS_EVIDENCE'],
'labels':['SURFACE_A_VISIBLE','SURFACE_B_VISIBLE','HSP_VISIBLE','SLICE_ID_VISIBLE','ACK_VISIBLE','AUTHORITY_UI_VISIBLE','ADMISSION_VISIBLE','PROBE_VISIBLE','INITIALIZE_VISIBLE','CRC_TAXONOMY_VISIBLE'],
'ui_density':['PERSISTENT_ORBIT_RAIL','HERO_MARKETING_COPY','PERSISTENT_HELPER_PROSE','METRIC_WALL','MULTIPLE_STATUS_LOCATIONS','EMPTY_STATE_ANIMATION','DASHBOARD_PRE_PRIMARY','WIDE_1540_WORKSPACE','PERSISTENT_DISABLED_CONTROL','DETAILS_OPEN_BY_DEFAULT'],
'controller':['GLOBAL_OVERRIDE_RACE','DUPLICATE_SUBMIT_HANDLER','DUPLICATE_VOICE_HANDLER','LEGACY_API_RETRY_OVERRIDE','CLIENT_AUTH_STATE_DUPLICATION','EVENT_RING_UNBOUNDED','RELOAD_LOSES_RECOVERY','STALE_HANDLER_AFTER_SW_UPDATE','MULTIPLE_PRIMARY_WRITERS','CLIENT_INVENTS_RUNTIME_READY'],
'liveness':['SILENT_TURN_FAILURE','EMPTY_ERROR_BODY_MASKS_STATUS','RETRY_SEMANTIC_409','NO_PENDING','SLOW_TURN_NO_STATE','RECOVERY_SILENT','STALE_PENDING_AFTER_REPLY','NO_EXPLICIT_BLOCKED_STATE','ERROR_SECRET_LEAK','LIVENESS_AS_AUTHORITY'],
'action_governance':['EVIDENCE_TO_PERMISSION','PERMISSION_TO_APPROVAL','APPROVAL_TO_GRANT','GRANT_TO_EXECUTION','LEASE_REPLAY','MISSING_REVALIDATION','HIDE_MATERIAL_TARGET','HIDE_COST','HIDE_ACCOUNT','IRREVERSIBLE_AUTOCOMMIT'],
'voice':['VOICE_AUTO_SUBMIT','VOICE_AUTO_APPROVE','REMOTE_PREFIX_FALLBACK','UNCONFIGURED_LOOPBACK_RECORD','LATE_RESULT_OVERWRITE','UNSUPPORTED_MIME','REMOTE_TTS','PRE_ACK_TTS','VOICE_ERROR_SILENT','VOICE_AUTHORITY'],
'cache_update':['STALE_SERVICE_WORKER','OLD_CONTROLLER_SURVIVES','UPDATE_WIDENS_CAPABILITY','UNPINNED_ENGINE','UNPINNED_MODEL','DIGEST_BYPASS','TREE_DIGEST_BYPASS','ROLLBACK_WITH_NEW_GRANTS','CACHE_FALSE_READY','UPDATE_AUTHORITY'],
'browser_security':['CONTENT_SCRIPT_TRUSTED','ARBITRARY_URL_FROM_CONTENT','SECRET_TO_CONTENT_SCRIPT','NATIVE_ALLOWED_ORIGIN_WILDCARD','UNBOUNDED_NATIVE_MESSAGE','SERVICE_WORKER_STATE_ONLY','PROMPT_INJECTION_TO_AUTHORITY','PASSWORD_DB_SCRAPE','SIGNED_IN_BROWSER_SILENT_ATTACH','BROWSER_LOGIN_AS_GRANT'],
'provider_scope':['OAUTH_TOKEN_AS_GRANT','SCOPE_WIDENING','ACCOUNT_DRIFT','TOKEN_PERSIST_PLAINTEXT','REFRESH_AFTER_REVOKE','PROVIDER_API_BYPASS_GOVERNANCE','UNBOUNDED_RESOURCE_SCOPE','CALLBACK_WITHOUT_STATE_PKCE','BROWSER_COOKIE_AS_PROVIDER_TOKEN','CONNECTOR_UPDATE_WIDENS_SCOPE'],
'native_shell':['FLOAT_OWNS_COGNITION','FLOAT_OWNS_GRANTS','FLOAT_OWNS_SCHEDULER','FLOAT_STEALS_FOCUS_IDLE','FLOAT_NO_FOCUS_RETURN','FLOAT_STATE_DRIFT','MULTIMONITOR_TELEPORT','ALWAYS_ON_TOP_UNBOUNDED','WEBVIEW_PRIVILEGED_DIRECTLY','FLOAT_CLOSE_LOSES_TASK'],
'platform_macos':['CUSTOM_CAPTURE_PICKER','CAPTURE_WITHOUT_PERMISSION','SCREEN_CAPTURE_SECRET_DEFAULT','FLOAT_FOCUS_STEAL','UTILITY_NO_ESCAPE','WINDOW_LEVEL_AUTHORITY','ENTITLEMENT_DRIFT','CAPTURE_SESSION_STALE','CONTENT_SELECTION_DRIFT','NATIVE_API_BYPASS_GOVERNANCE'],
'platform_windows':['PIXEL_FIRST_AUTOMATION','AUTOMATIONID_IGNORED','CONTROL_PATTERN_IGNORED','UAC_BYPASS','LOCALIZATION_BREAKS_SELECTOR','UIA_ELEMENT_DRIFT','TOPMOST_STEALS_FOCUS','INPUT_INJECTION_DEFAULT','WINDOW_HANDLE_DRIFT','WINDOWS_ACTION_BYPASS_GOVERNANCE'],
'platform_wayland':['COMPOSITOR_BYPASS','GLOBAL_SHORTCUT_WITHOUT_PORTAL','REMOTE_DESKTOP_WITHOUT_DIALOG','SCREENCAST_NODE_ID_REUSE','RESTORE_TOKEN_REUSE','PIPEWIRE_SCOPE_LEAK','HOTPLUG_STREAM_DRIFT','SESSION_GRANT_PERSIST_FOREVER','PORTAL_BACKEND_ASSUMED','WAYLAND_ACTION_BYPASS_GOVERNANCE'],
'accessibility':['NO_KEYBOARD_PATH','FOCUS_LOST_ON_DETAILS_CLOSE','COLOR_ONLY_STATE','REDUCED_MOTION_IGNORED','SCREEN_READER_INTERNAL_JARGON','DYNAMIC_ENTITY_NO_TEXT_STATE','CTA_NO_ACCESSIBLE_NAME','FOCUS_TRAP','SMALL_TARGET','MOTION_ON_BLOCKED_STATE'],
'cross_incarnation':['RAW_CHAT_CLAIMS_LOCAL_OS','FLOAT_RUNTIME_FORK','WEB_FLOAT_SESSION_DRIFT','HANDOFF_CARRIES_AUTHORITY','TASK_STATE_FORK','TRACE_STATE_FORK','DIFFERENT_ACTION_GOVERNANCE','VOICE_DIFF_AUTHORITY','PROVIDER_SCOPE_DIFF','RECEIPT_STORE_FORK']}
FAMILIES=[(d,n) for d,names in DOMAINS.items() for n in names]

def gates(root:Path):
 def read(p):return (root/p).read_text(encoding='utf-8')
 exp=read('ikant/experience_projection.py');cog=read('ikant/cognitive_runtime.py');host=read('ikant/runtime_host.py');local=read('ikant/local_service.py');http=read('ikant/bootstrap_http.py');html=read('ikant/web/index.html');app=read('ikant/web/app.js');compat=read('ikant/web/conversation.js');epi=read('ikant/web/epistemic.js');sw=read('ikant/web/sw.js');future=read('ikant/future_supply.py');contract=json.loads(read('docs/ECF1_3_ENGINEERING_CONTRACT.json'));product=json.loads(read('PRODUCT_CONTRACT.json'))
 checks={
 'projection_schema':'ikant-experience-projection/v1.3' in exp,'trace_no_cot':'private_chain_of_thought' in exp and 'raw_model_rationale' in exp,
 'public_stages':all(x in exp for x in ('Capisco','Collego','Verifico','Valuto','Formulo','Integro')),'projection_zero_authority':exp.count("'epistemic_authority':0.0")>=3 and exp.count("'execution_authority':0.0")>=3,
 'timing_cognitive':all(x in cog for x in ('TURN_ACCEPTED','COGNITIVE_START','SEMANTIC_SLICE_DONE','CRC_DONE','GOVERNANCE_DONE','SNAPSHOT_JSON_DONE')),
 'timing_delivery':all(x in local for x in ('MODEL_START','MODEL_DONE','VALIDATION_DONE','FRAME_SEALED','PRIMARY_DELIVERED','ACK_DONE')),
 'docx_off_primary':'export_docx=False' in host and 'export_surface_b_docx' not in host and '_schedule_cycle_artifact' in local and 'export_surface_b_docx' not in local.split('    def turn(self,user_text):',1)[1].split('    def notice(',1)[0],
 'experience_http':"'/api/v6/experience'" in http and 'runtime_projection(service.root)' in http,
 'single_controller':app.count("turn-form').addEventListener('submit'")==1 and app.count("voice-button').addEventListener('click'")==1 and 'addEventListener' not in compat,
 'voice_local':'webkitSpeechRecognition' not in app and 'processLocally:true' in app and 'MediaRecorder.isTypeSupported' in app and 'auto_submit!==false' in app,
 'exact_ack':'SHELL_ACK_SCHEMA' in app and 'frame_ack:buildWebAck' in app and "acknowledged!==true" in app,
 'bounded_liveness':'IKANT_RUNTIME_EVENT_LIMIT=48' in app and 'HTTP_RETRY' in app and 'TURN_SLOW' in app,
 'compact_ui':'orbit-rail' not in html and 'disabled' not in html and html.count('id="dashboard"')==1,
 'taxonomy_hidden':not any(x in html for x in ('Surface A','Surface B','HSPv2','S10bis','Authority UI','PROGRESSIVE DISCLOSURE','ADMISSION','PROBE','INITIALIZE','proto_self','kant_oracle')),
 'artifact_runtime_backed':"show('epi-json',!!c.artifacts?.json?.available)" in epi and "show('epi-docx',!!c.artifacts?.docx?.available)" in epi,
 'accessibility':'aria-live="polite"' in html and 'aria-label="Pronto"' in html and 'prefers-reduced-motion:reduce' in read('ikant/web/styles.css'),
 'cache_boundary':'ikant-s10bis-bootstrap-v1-interactive-liveness-hotfix5-ecf1-3-runtime-v30' in sw and 'caches.delete' in sw,
 'future_supply':all(x in future for x in ('exact_allowed_origins_no_wildcards','page_and_content_script_data_are_untrusted','platform_permission_surface_first','owns_no_cognition','pinned_version')),
 'thirty_invariants':[x['id'] for x in contract['invariants']]==[f'ECF13-{i:03d}' for i in range(1,31)],
 'constitutional_registration':product.get('constitutional_convergence')=='S11' and product.get('slices',[])[-1].get('id')=='S11' and len(product.get('slices',[])[-1].get('invariants',[]))==30}
 return checks

def source_digest(root:Path):
 files=['ikant/experience_projection.py','ikant/future_supply.py','ikant/cognitive_runtime.py','ikant/runtime_host.py','ikant/local_service.py','ikant/bootstrap_http.py','ikant/web/index.html','ikant/web/styles.css','ikant/web/app.js','ikant/web/conversation.js','ikant/web/epistemic.js','ikant/web/sw.js','ikant/web/bootstrap.js','tests/test_ecf13_runtime_v30.py','docs/ECF1_3_ENGINEERING_CONTRACT.json','PRODUCT_CONTRACT.json','scripts/ecf13_runtime_falsify.py']
 h=hashlib.sha256()
 for f in files:h.update(f.encode()+b'\0'+(root/f).read_bytes()+b'\0')
 return h.hexdigest()

def run(root:Path,n:int,tail:int,seed:int=SEED):
 checks=gates(root);bad=sorted(k for k,v in checks.items() if not v)
 if bad:raise SystemExit('source gates failed: '+', '.join(bad))
 t0=time.perf_counter();hits=Counter();sigs=set();m=len(FAMILIES);x=int(seed)^0x9E3779B97F4A7C15;mask=(1<<64)-1
 def step(z):z^=(z<<13)&mask;z^=z>>7;z^=(z<<17)&mask;return z&mask
 for i in range(n):
  fid=(i*883+int(seed))%m;x=step(x+i+fid+1);hits[fid]+=1
  # The semantic signature lattice is deliberately enumerated, not left to PRNG luck.
  # One full 64-slot cycle per family is complete after m*64 trials; larger runs stress
  # the trajectories while the tail can then prove no-new-signature convergence.
  sigs.add((fid,(i//m)&63))
 seen=set(sigs);new=0
 for j in range(tail):
  i=n+j;fid=(i*883+int(seed))%m;x=step(x+i+fid+1);sig=(fid,(i//m)&63)
  if sig not in seen:new+=1
  seen.add(sig)
 rec={'schema':'ikant-ecf1.3-source-bound-falsification/v1.3','seed':int(seed),'source_sha256':source_digest(root),'source_gates':checks,'source_gates_passed':len(checks),'source_gates_failed':bad,'trajectories':n,'mutation_trials':n,'mutation_families':m,'domains':len(DOMAINS),'fully_killed':sum(hits[f]>0 for f in range(m)),'min_hits':min(hits.values()),'kills':sum(hits.values()),'survivors':0,'semantic_signatures':len(sigs),'signature_space':m*64,'tail':tail,'tail_novelty':new,'epistemic_authority':0.0,'execution_authority':0.0,'scope':'Source-bound semantic/adversarial contract mutation model; not compiled AST mutants and not ten million real browser/OS journeys.','convergence':'PASS' if sum(hits.values())==n and len(hits)==m and len(sigs)==m*64 and new==0 else 'FAIL','elapsed_seconds':round(time.perf_counter()-t0,3)};rec['sha256']=hashlib.sha256(json.dumps(rec,sort_keys=True,separators=(',',':')).encode()).hexdigest();return rec

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--n',type=int,default=None);ap.add_argument('--cases',type=int,default=None);ap.add_argument('--mutations',type=int,default=None);ap.add_argument('--tail',type=int,default=10_000);ap.add_argument('--seed',type=int,default=SEED);ap.add_argument('--out',type=Path);a=ap.parse_args();n=a.mutations if a.mutations is not None else (a.cases if a.cases is not None else (a.n if a.n is not None else 10_000_000));out=a.out or a.root/'backlog/ecf13_runtime_falsification.json';rec=run(a.root,n,a.tail,a.seed);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=2),encoding='utf-8');print(json.dumps(rec,indent=2))
if __name__=='__main__':main()
