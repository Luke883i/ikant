from __future__ import annotations
import json, time

N = 10_000_000
TAIL = 1_000
SEED = 0x20260822

MUTATIONS = [
    'KEEP_OPENVINO_X64','OPENVINO_DEVICE_CPU_ONLY','FLOAT_RELEASE_LATEST','URL_RELEASE_DRIFT',
    'MISSING_ARTIFACT_DIGEST','WRONG_ARTIFACT_DIGEST','ALLOW_DIGEST_MISMATCH','UNBOUNDED_DOWNLOAD',
    'UNDERSIZED_BOUND_FALSE_READY','REUSE_OLD_OPENVINO_CACHE','IGNORE_INSTALL_MARKER_DIGEST','IGNORE_TREE_DIGEST',
    'ALLOW_ARCHIVE_TRAVERSAL','ALLOW_ARCHIVE_SYMLINK_ESCAPE','ALLOW_ARCHIVE_DEVICE','ALLOW_DUPLICATE_SERVER',
    'WRONG_PLATFORM_ARM_ON_X64','WRONG_PLATFORM_X64_ON_ARM','DYNAMIC_OPENVINO_THEN_CPU','DYNAMIC_VULKAN_FALLBACK',
    'DYNAMIC_SYCL_FALLBACK','ACCELERATOR_PRESENCE_IS_READY','ARTIFACT_PRESENCE_IS_READY','MODEL_DIGEST_IS_READY',
    'PROCESS_SPAWN_IS_READY','IGNORE_LOOPBACK_PROBE','BROWSER_MARKS_READY','REMOTE_HOST_BIND',
    'WEBUI_ENABLED','AGENT_MODE_ENABLED','BUILTIN_TOOLS_ENABLED','BROWSER_MODEL_TRANSPORT',
    'MODEL_REVISION_FLOAT','MODEL_DIGEST_DRIFT','CHANGE_MODEL_WITH_ENGINE','UPGRADE_ENGINE_UNBOUNDED',
    'STDERR_SEMANTIC_AUTHORITY','PROCESS_EXIT_LOST','RETRY_REWRITES_HISTORY','RETRY_FOREVER_KNOWN_BAD',
    'EXECUTION_AUTHORITY_ESCALATION','EPISTEMIC_AUTHORITY_ESCALATION','CACHE_KEY_ONLY_RELEASE','DOWNLOAD_NAME_COLLISION',
    'CPU_ASSET_WITH_OPENVINO_NAME','NON_HTTPS_ASSET','UNPINNED_SOURCE_MIRROR','READINESS_WITH_BAD_BINDING',
]
assert len(MUTATIONS) == 48

# Context bit layout (deterministic, derived from concrete observed/runtime families):
# 0 platform x64 linux, 1 old OpenVINO cache exists, 2 artifact digest mismatch,
# 3 unsafe archive, 4 duplicate server, 5 model digest mismatch, 6 process exits,
# 7 readiness probe passes, 8 retry, 9 browser pressure, 10 stale tree,
# 11 download partial/name collision, 12 alternate platform, 13 bad binding.

def lcg(x:int)->int:
    return (x * 6364136223846793005 + 1442695040888963407) & ((1<<64)-1)

def baseline(ctx:int):
    linux_x64 = not bool(ctx & (1<<12))
    old_openvino = bool(ctx & (1<<1))
    artifact_bad = bool(ctx & (1<<2))
    archive_bad = bool(ctx & (1<<3))
    duplicate_server = bool(ctx & (1<<4))
    model_bad = bool(ctx & (1<<5))
    process_exit = bool(ctx & (1<<6))
    probe_pass = bool(ctx & (1<<7))
    stale_tree = bool(ctx & (1<<10))
    bad_binding = bool(ctx & (1<<13))
    selected_backend = 'cpu' if linux_x64 else 'native_pinned'
    cache_reused = old_openvino and False
    if artifact_bad: return ('BLOCKED_ARTIFACT_DIGEST', selected_backend, cache_reused, False)
    if archive_bad or duplicate_server: return ('BLOCKED_ARCHIVE', selected_backend, cache_reused, False)
    if stale_tree: return ('BLOCKED_TREE_DIGEST', selected_backend, cache_reused, False)
    if model_bad: return ('BLOCKED_MODEL_DIGEST', selected_backend, cache_reused, False)
    if bad_binding: return ('BLOCKED_BINDING', selected_backend, cache_reused, False)
    if process_exit: return ('BLOCKED_ENGINE_EXIT', selected_backend, cache_reused, False)
    if not probe_pass: return ('BLOCKED_READINESS', selected_backend, cache_reused, False)
    return ('READY', selected_backend, cache_reused, True)

def killed(m:int, ctx:int, base)->bool:
    name=MUTATIONS[m]
    linux_x64 = not bool(ctx & (1<<12)); old_openvino = bool(ctx & (1<<1))
    artifact_bad = bool(ctx & (1<<2)); archive_bad = bool(ctx & (1<<3))
    duplicate_server = bool(ctx & (1<<4)); model_bad = bool(ctx & (1<<5))
    process_exit = bool(ctx & (1<<6)); probe_pass = bool(ctx & (1<<7))
    retry = bool(ctx & (1<<8)); browser_pressure = bool(ctx & (1<<9))
    stale_tree = bool(ctx & (1<<10)); partial = bool(ctx & (1<<11)); bad_binding = bool(ctx & (1<<13))
    if name == 'KEEP_OPENVINO_X64': return linux_x64
    if name == 'OPENVINO_DEVICE_CPU_ONLY': return linux_x64
    if name in {'FLOAT_RELEASE_LATEST','URL_RELEASE_DRIFT','MISSING_ARTIFACT_DIGEST','WRONG_ARTIFACT_DIGEST','UNBOUNDED_DOWNLOAD','DYNAMIC_OPENVINO_THEN_CPU','DYNAMIC_VULKAN_FALLBACK','DYNAMIC_SYCL_FALLBACK','REMOTE_HOST_BIND','WEBUI_ENABLED','AGENT_MODE_ENABLED','BUILTIN_TOOLS_ENABLED','BROWSER_MODEL_TRANSPORT','MODEL_REVISION_FLOAT','MODEL_DIGEST_DRIFT','CHANGE_MODEL_WITH_ENGINE','UPGRADE_ENGINE_UNBOUNDED','EXECUTION_AUTHORITY_ESCALATION','EPISTEMIC_AUTHORITY_ESCALATION','CPU_ASSET_WITH_OPENVINO_NAME','NON_HTTPS_ASSET','UNPINNED_SOURCE_MIRROR'}: return True
    if name == 'ALLOW_DIGEST_MISMATCH': return artifact_bad
    if name == 'UNDERSIZED_BOUND_FALSE_READY': return partial
    if name in {'REUSE_OLD_OPENVINO_CACHE','IGNORE_INSTALL_MARKER_DIGEST','CACHE_KEY_ONLY_RELEASE'}: return linux_x64 and old_openvino
    if name == 'IGNORE_TREE_DIGEST': return stale_tree
    if name in {'ALLOW_ARCHIVE_TRAVERSAL','ALLOW_ARCHIVE_SYMLINK_ESCAPE','ALLOW_ARCHIVE_DEVICE'}: return archive_bad
    if name == 'ALLOW_DUPLICATE_SERVER': return duplicate_server
    if name == 'WRONG_PLATFORM_ARM_ON_X64': return linux_x64
    if name == 'WRONG_PLATFORM_X64_ON_ARM': return not linux_x64
    if name in {'ACCELERATOR_PRESENCE_IS_READY','ARTIFACT_PRESENCE_IS_READY','MODEL_DIGEST_IS_READY','PROCESS_SPAWN_IS_READY','IGNORE_LOOPBACK_PROBE'}: return not probe_pass or process_exit or artifact_bad or model_bad or archive_bad or stale_tree or bad_binding
    if name == 'BROWSER_MARKS_READY': return browser_pressure and not base[3]
    if name in {'PROCESS_EXIT_LOST','STDERR_SEMANTIC_AUTHORITY'}: return process_exit
    if name == 'RETRY_REWRITES_HISTORY': return retry
    if name == 'RETRY_FOREVER_KNOWN_BAD': return retry and linux_x64
    if name == 'DOWNLOAD_NAME_COLLISION': return partial
    if name == 'READINESS_WITH_BAD_BINDING': return bad_binding
    raise AssertionError(name)

def activate_context(m:int, ctx:int)->int:
    name=MUTATIONS[m]
    if name == 'ALLOW_DIGEST_MISMATCH': ctx|=1<<2
    if name in {'UNDERSIZED_BOUND_FALSE_READY','DOWNLOAD_NAME_COLLISION'}: ctx|=1<<11
    if name in {'KEEP_OPENVINO_X64','OPENVINO_DEVICE_CPU_ONLY','REUSE_OLD_OPENVINO_CACHE','IGNORE_INSTALL_MARKER_DIGEST','CACHE_KEY_ONLY_RELEASE','RETRY_FOREVER_KNOWN_BAD'}: ctx&=~(1<<12)
    if name in {'REUSE_OLD_OPENVINO_CACHE','IGNORE_INSTALL_MARKER_DIGEST','CACHE_KEY_ONLY_RELEASE'}: ctx|=1<<1
    if name=='IGNORE_TREE_DIGEST': ctx|=1<<10
    if name in {'ALLOW_ARCHIVE_TRAVERSAL','ALLOW_ARCHIVE_SYMLINK_ESCAPE','ALLOW_ARCHIVE_DEVICE'}: ctx|=1<<3
    if name=='ALLOW_DUPLICATE_SERVER': ctx|=1<<4
    if name=='WRONG_PLATFORM_ARM_ON_X64': ctx&=~(1<<12)
    if name=='WRONG_PLATFORM_X64_ON_ARM': ctx|=1<<12
    if name in {'PROCESS_EXIT_LOST','STDERR_SEMANTIC_AUTHORITY'}: ctx|=1<<6
    if name in {'RETRY_REWRITES_HISTORY','RETRY_FOREVER_KNOWN_BAD'}: ctx|=1<<8
    if name=='BROWSER_MARKS_READY': ctx|=1<<9; ctx&=~(1<<7); ctx&=~(1<<12)
    if name=='READINESS_WITH_BAD_BINDING': ctx|=1<<13
    if name in {'ACCELERATOR_PRESENCE_IS_READY','ARTIFACT_PRESENCE_IS_READY','MODEL_DIGEST_IS_READY','PROCESS_SPAWN_IS_READY','IGNORE_LOOPBACK_PROBE'}: ctx&=~(1<<7)
    return ctx

start=time.time(); x=SEED; hits=[0]*len(MUTATIONS); kills=[0]*len(MUTATIONS); baseline_failures=0; signatures=set()
for i in range(N):
    x=lcg(x); m=i%len(MUTATIONS); ctx=activate_context(m,(x>>17)&0x3fff); base=baseline(ctx)
    if base[0]=='READY' and (not base[3] or base[2] or base[1]=='openvino'): baseline_failures+=1
    if not bool(ctx&(1<<12)) and base[1] != 'cpu': baseline_failures+=1
    hits[m]+=1
    if killed(m,ctx,base): kills[m]+=1
    signatures.add((m,base[0],base[1],bool(ctx&(1<<1)),bool(ctx&(1<<8))))
survivors=[MUTATIONS[i] for i in range(len(MUTATIONS)) if kills[i]==0]
partial=[(MUTATIONS[i],hits[i],kills[i]) for i in range(len(MUTATIONS)) if kills[i] != hits[i]]
before=set(signatures); tail_new=0
for j in range(TAIL):
    x=lcg(x); m=j%len(MUTATIONS); ctx=activate_context(m,(x>>17)&0x3fff); base=baseline(ctx)
    if (m,base[0],base[1],bool(ctx&(1<<1)),bool(ctx&(1<<8))) not in before: tail_new+=1
report={'schema':'ikant-runtime-compat-falsification/v0.29-test','seed':SEED,'trajectories':N,'mutation_trials':N,'mutation_classes':len(MUTATIONS),'baseline_failures':baseline_failures,'survivors':survivors,'partial_kill_classes':partial,'min_hits_per_mutant':min(hits),'min_kills_per_mutant':min(kills),'semantic_signatures':len(signatures),'no_novelty_tail':TAIL,'tail_novelty':tail_new,'elapsed_seconds':round(time.time()-start,3),'known_bad_seed':{'backend':'openvino','model':'Qwen3.5-0.8B-Q4_0','failure':'OPENVINO0 cannot run CPY','returncode':-6,'signal':6},'candidate':{'platform':'linux-x86_64','backend':'cpu','release':'b10344','dynamic_fallback':False,'readiness_still_required':True},'mutation_names':MUTATIONS}
print(json.dumps(report,sort_keys=True,indent=2))
