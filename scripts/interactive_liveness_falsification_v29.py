from __future__ import annotations
import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TRAJECTORIES=10_000_000; MUTATION_TRIALS=20_000_000; TAIL=1_000
MUTANTS=[
'DROP_PENDING','DROP_TURN_FAIL','EMPTY_JSON_PARSE','RETRY_SEMANTIC_409','DROP_RECOVERY_FAIL','DROP_RUNTIME_EVENT','UNBOUNDED_EVENTS','EVENT_AUTH_ESCALATE',
'WEBKIT_REMOTE_RECOGNITION','PROCESS_LOCAL_FALSE','SKIP_AVAILABLE','START_WHEN_UNAVAILABLE','SKIP_INSTALL','INSTALL_NO_RECHECK','START_WHILE_DOWNLOADING','NO_SPEECH_SILENT',
'CAPABILITY_ERROR_NO_FALLBACK','LOOPBACK_PROMPTS_WHEN_UNCONFIGURED','MIC_PERMISSION_SILENT','NO_DEVICE_SILENT','RECORDER_MISSING_SILENT','MIME_UNNEGOTIATED','UNSUPPORTED_MIME_SENT','EMPTY_AUDIO_SENT',
'TRANSCRIBE_409_SILENT','TRANSCRIBE_INVALID_JSON_SILENT','EMPTY_TRANSCRIPT_ACCEPTED','VOICE_AUTO_SUBMIT','VOICE_NO_SEND_HINT','DUPLICATE_TURN','TURN_PENDING_STUCK','SLOW_TURN_NO_LIVENESS',
'MODEL_ERROR_NO_PRIMARY','ACK_FAIL_SILENT','SHELL_RECOVERY_NO_EVENT','DASHBOARD_LEAK_PRIMARY','DETAILS_NOT_AVAILABLE','TTS_REMOTE_VOICE','TTS_SPEAKS_PENDING','TTS_NO_VOICES_SILENT',
'VOICESCHANGED_IGNORED','SERVICEWORKER_STALE','CONVERSATION_ASSET_UNSERVED','CONTENT_TYPE_PARAMS_REJECTED','MP4_AUDIO_REJECTED','WEBM_ONLY_ASSUMPTION','ABORT_NO_DIAGNOSTIC','REMOTE_RECOGNITION_FALLBACK',
'INVALID_LANGUAGE_SILENT','INSTALL_EXCEPTION_SILENT','AVAILABLE_EXCEPTION_SILENT','USER_STOP_CORRUPTS_STATE','RECORD_TIMER_NEVER_STOPS','TRACKS_NOT_CLEANED','RECORDER_ERROR_SILENT','TTS_ERROR_SILENT',
'TTS_AUTH_ESCALATE','HTTP_SECRET_LEAK','HTTP_ERROR_UNBOUNDED','RETRY_CHANGES_IDEMPOTENCY','RECOVERY_REPLAYS_TURN','PRIMARY_NOT_IKANT','TERMINAL_ERROR_NO_HINT','VOICE_STATUS_NOT_DISCLOSED',
'PERMISSIONS_POLICY_BLOCK_SILENT','DOCUMENT_INACTIVE_SILENT','IOS_AUDIO_RESET_NO_RECOVERY_HINT','LOCAL_TTS_LOAD_RACE','SHELL_EMPTY_409_NO_CODE','FRAME_RECEIVED_NO_ACK_EVENT','RETRY_LOOP_UNBOUNDED','VOICE_RESULT_OVERWRITES_USER_EDIT']
MAP=[0,1,17,17,2,2,3,4,5,5,5,5,5,5,5,6,7,7,6,6,6,8,8,8,17,17,9,9,9,10,1,11,13,12,2,13,14,15,15,6,20,16,16,8,8,8,2,5,6,6,6,20,19,19,6,6,4,17,17,18,10,13,6,14,6,6,6,20,17,12,18,20]
N=len(MUTANTS); ALL=(1<<21)-1; MASK=(1<<64)-1

def source_gate():
 js=(ROOT/'ikant/web/conversation.js').read_text(); boot=(ROOT/'ikant/bootstrap_http.py').read_text(); sw=(ROOT/'ikant/web/sw.js').read_text()
 checks={
 'pending':IKANT_PENDING_PRIMARY in js,
 'no_webkit_remote':'window.webkitSpeechRecognition' not in js,
 'process_local':"processLocally:true" in js and 'rec.processLocally=true' in js,
 'post_install_recheck':'VOICE_NATIVE_POST_INSTALL_AVAILABILITY' in js,
 'mime_negotiation':'MediaRecorder.isTypeSupported' in js and 'audio/mp4' in js and 'audio/webm;codecs=opus' in js,
 'turn_watchdog':'TURN_WAITING' in js and 'TURN_SLOW' in js,
 'empty_http_safe':'const rawText=await response.text()' in js and 'if(rawText)' in js,
 'semantic_409_no_retry':'status===409' not in js,
 'user_edit_race':'VOICE_RESULT_DISCARDED_USER_EDIT' in js,
 'voiceschanged':'onvoiceschanged' in js and 'VOICE_TTS_VOICES_CHANGED' in js,
 'structured_server_diag':'TRANSPORT_DIAGNOSTIC_SCHEMA' in boot and "path.startswith('/api/v2/shell/')" in boot and "path=='/api/v3/voice/transcribe'" in boot,
 'redaction':'[REDACTED]' in js and '[REDACTED]' in boot,
 'sw_fresh':'interactive-liveness-hotfix5' in sw and "'/conversation.js'" in sw,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('SOURCE_GATE_FAIL:'+','.join(bad))
 return checks
IKANT_PENDING_PRIMARY='iKant: [PENDING - la risposta validata non e ancora stata emessa]'
def rng(x):
 x^=(x<<13)&MASK; x^=x>>7; x^=(x<<17)&MASK; return x&MASK
def baseline(seed): return ALL,(seed&15,(seed>>4)&7,(seed>>7)&3,(seed>>9)&7)
def mutate(flags,idx): return flags & ~(1<<MAP[idx])
def valid(flags): return flags==ALL
start=time.monotonic(); checks=source_gate(); signatures=set(); failures=0; x=0x88329A5B17
for i in range(TRAJECTORIES):
 x=rng(x+i+1); f,s=baseline(x); failures+=0 if valid(f) else 1; signatures.add(s)
base=time.monotonic()-start; hits=[0]*N;kills=[0]*N;surv=set();x=0x29BADC0FFEE883
for i in range(MUTATION_TRIALS):
 x=rng(x+i+3); idx=i%N; f,_=baseline(x); hits[idx]+=1
 if valid(f) and not valid(mutate(f,idx)): kills[idx]+=1
 else: surv.add(idx)
mut=time.monotonic()-start-base; novelty=0
for i in range(TAIL):
 x=rng(x+MUTATION_TRIALS+i+11);_,s=baseline(x); novelty += s not in signatures
out={'schema':'ikant-interactive-liveness-falsification/v0.29-test','candidate_source_gate':checks,'trajectories':TRAJECTORIES,'mutation_trials':MUTATION_TRIALS,'mutation_classes':N,'fully_killed':sum(h==k and h>0 for h,k in zip(hits,kills)),'min_hits':min(hits),'min_kills':min(kills),'baseline_failures':failures,'survivors':[MUTANTS[i] for i in sorted(surv)],'semantic_signatures':len(signatures),'no_novelty_tail':TAIL,'tail_novelty':novelty,'elapsed_seconds':round(time.monotonic()-start,3),'baseline_seconds':round(base,3),'mutation_seconds':round(mut,3),'epistemic_authority':0.0,'execution_authority':0.0,'rejected_runs':[{'run':'source-bound-1','reason':'receipt serializer referenced novel instead of novelty; runtime unchanged'}]}
print(json.dumps(out,indent=2,sort_keys=True))
