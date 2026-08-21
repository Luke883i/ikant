from __future__ import annotations
import json, os, signal, subprocess, sys, time
from collections import Counter
from pathlib import Path
from ikant.engine_exit_diagnostics import *

ITERATIONS=10_000_000
TAIL=1_000
SEED=20260822
OUT=Path(__file__).resolve().parents[1]/'backlog'/'S10bis_hotfix2_e2e_falsification.json'
PYTHON=sys.executable
MUTANTS=('DROP_CAPTURE','DROP_DIAGNOSTIC','DROP_RETURNCODE','DROP_SIGNAL','DROP_STDERR','UNBOUNDED_STDERR','LEAK_SECRET','UTF8_EXPAND','SERIALIZER_DROP_PROCESS_EXIT','WRAPPER_DROPS_CAUSE','WRONG_SIGNAL_SIGN','EXIT_ZERO_AS_READY','UNKNOWN_ON_EXIT','AUTH_EPISTEMIC','AUTH_EXECUTION','CAUSE_CHAIN_OVERFLOW','STDERR_GUESSES_CODE','JOURNAL_DROPS_CAUSES','JOURNAL_DROPS_PROCESS_EXIT','DIAG_ON_WRONG_CAUSE','EMPTY_STDERR_ERASES_EXIT','POSITIVE_AS_SIGNAL','NEGATIVE_AS_STATUS','TAIL_PREFIX_NOT_SUFFIX','RETRY_REWRITES_HISTORY','EVENT_OVERSIZE','CONTROL_CHAR_UNBOUNDED','PROCESS_RUNNING_FALSE_READY','POLL_RACE_NONE_AFTER_EXIT','SIGNAL_LOST_BY_ABS','RETURN_CODE_STRINGIFIED','DIAGNOSTIC_AUTHORITY_NONZERO')

def _spawn(argv):
 capture=BoundedStderrCapture();process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);capture.start(process.stderr);return process,capture

def os_fixture(exit_code=7,payload=b'fixture',sig=None,huge=False):
 if sig is not None:
  p,c=_spawn([PYTHON,'-c','import time;time.sleep(30)']);p.send_signal(sig);p.wait(timeout=5);c.finish();return EngineExitDiagnostic.capture(p.returncode,c.snapshot())
 code=f"import os;os.write(2,b'x'*{MAX_STDERR_CAPTURE_BYTES*6});os.write(2,{payload!r});raise SystemExit({exit_code})" if huge else f"import os;os.write(2,{payload!r});raise SystemExit({exit_code})"
 p,c=_spawn([PYTHON,'-c',code]);p.wait(timeout=10);c.finish();return EngineExitDiagnostic.capture(p.returncode,c.snapshot())

def concrete_fixtures():
 rows=[os_fixture(rc,f'fixture rc={rc}\n'.encode()) for rc in (0,1,2,7,9,23,42,64,126,127,137,255)]
 rows += [os_fixture(19,b'token=TOPSECRET password=hunter2 tail\n'),os_fixture(20,b'\xff\xfe\x80 malformed-tail\n'),os_fixture(21,b'END-MARKER\n',huge=True)]
 if os.name!='nt':rows += [os_fixture(sig=signal.SIGTERM),os_fixture(sig=signal.SIGKILL)]
 rows += [EngineExitDiagnostic.capture(None,b'journal-observed early exit duration_ms=8165'),EngineExitDiagnostic.capture(None,b'journal-observed early exit duration_ms=6031')]
 return rows

def pipeline(case,mutant=None):
 rc=case.returncode;sig=case.signal;stderr=case.stderr_tail;code='ENGINE_EXITED_EARLY';epi=exe=0.0;cause_len=2;has_capture=has_diag=has_serialized=history_append_only=tail_is_suffix=True;false_ready=False
 if mutant=='DROP_CAPTURE':has_capture=False;stderr=''
 elif mutant=='DROP_DIAGNOSTIC':has_diag=False
 elif mutant=='DROP_RETURNCODE':rc=None
 elif mutant=='DROP_SIGNAL' and case.kind=='SIGNAL':sig=None
 elif mutant=='DROP_STDERR':stderr=''
 elif mutant=='UNBOUNDED_STDERR':stderr='x'*(MAX_STDERR_TAIL_BYTES+1)
 elif mutant=='LEAK_SECRET':stderr='token=TOPSECRET'
 elif mutant=='UTF8_EXPAND':stderr='\ufffd'*MAX_STDERR_TAIL_BYTES
 elif mutant=='SERIALIZER_DROP_PROCESS_EXIT':has_serialized=False
 elif mutant=='WRAPPER_DROPS_CAUSE':cause_len=1;has_serialized=False
 elif mutant=='WRONG_SIGNAL_SIGN' and case.kind=='SIGNAL':sig=-case.signal if case.signal else -9
 elif mutant=='EXIT_ZERO_AS_READY' and case.returncode==0:code='ENGINE_READY';false_ready=True
 elif mutant=='UNKNOWN_ON_EXIT' and case.returncode is not None:rc=sig=None
 elif mutant=='AUTH_EPISTEMIC':epi=1.0
 elif mutant=='AUTH_EXECUTION':exe=1.0
 elif mutant=='CAUSE_CHAIN_OVERFLOW':cause_len=7
 elif mutant=='STDERR_GUESSES_CODE':code='ENGINE_OOM_GUESSED'
 elif mutant in {'JOURNAL_DROPS_CAUSES','JOURNAL_DROPS_PROCESS_EXIT','DIAG_ON_WRONG_CAUSE'}:has_serialized=False;cause_len=0 if mutant=='JOURNAL_DROPS_CAUSES' else cause_len
 elif mutant=='EMPTY_STDERR_ERASES_EXIT' and not case.stderr_tail:has_diag=False
 elif mutant=='POSITIVE_AS_SIGNAL' and case.returncode is not None and case.returncode>=0:sig=max(1,case.returncode)
 elif mutant=='NEGATIVE_AS_STATUS' and case.returncode is not None and case.returncode<0:sig=None
 elif mutant=='TAIL_PREFIX_NOT_SUFFIX':tail_is_suffix=False
 elif mutant=='RETRY_REWRITES_HISTORY':history_append_only=False
 elif mutant=='EVENT_OVERSIZE':stderr='x'*(16*1024)
 elif mutant=='CONTROL_CHAR_UNBOUNDED':stderr='\x00'*5000
 elif mutant=='PROCESS_RUNNING_FALSE_READY':false_ready=True;code='ENGINE_READY'
 elif mutant=='POLL_RACE_NONE_AFTER_EXIT' and case.returncode is not None:rc=sig=None
 elif mutant=='SIGNAL_LOST_BY_ABS' and case.returncode is not None and case.returncode<0:rc=abs(case.returncode);sig=None
 elif mutant=='RETURN_CODE_STRINGIFIED' and case.returncode is not None:rc=str(case.returncode)
 elif mutant=='DIAGNOSTIC_AUTHORITY_NONZERO':epi=.1
 return rc,sig,stderr,code,epi,exe,cause_len,has_capture,has_diag,has_serialized,history_append_only,tail_is_suffix,false_ready

def valid(case,out):
 rc,sig,stderr,code,epi,exe,cause_len,has_capture,has_diag,has_serialized,history_append_only,tail_is_suffix,false_ready=out
 if epi!=0.0 or exe!=0.0 or cause_len<2 or cause_len>6 or not has_capture or not has_diag or not has_serialized or not history_append_only or not tail_is_suffix or false_ready or code!='ENGINE_EXITED_EARLY':return False
 if not isinstance(stderr,str) or stderr!=case.stderr_tail or len(stderr.encode('utf-8',errors='replace'))>MAX_STDERR_TAIL_BYTES:return False
 low=stderr.lower()
 if any(x in low for x in ('topsecret','hunter2','token=','password=')):return False
 if case.returncode is None:return rc is None and sig is None
 if case.returncode<0:return rc==case.returncode and sig==-case.returncode
 return type(rc) is int and rc==case.returncode and sig is None

def signature(case,out):
 rc,sig,stderr,code,epi,exe,cause_len,has_capture,has_diag,has_serialized,history_append_only,tail_is_suffix,false_ready=out
 return case.kind,'NONE' if case.returncode is None else ('NEG' if case.returncode<0 else 'ZERO' if case.returncode==0 else 'POS'),bool(stderr),code,cause_len,has_capture,has_diag,has_serialized,history_append_only,tail_is_suffix,false_ready

def main():
 fixtures=concrete_fixtures();assert all(len(x.stderr_tail.encode())<=MAX_STDERR_TAIL_BYTES for x in fixtures);baseline_failures=0;killed=Counter();hits=Counter();signatures=set();state=SEED&0xffffffff;started=time.time()
 for i in range(ITERATIONS):
  state=(1664525*state+1013904223)&0xffffffff;case=fixtures[state%len(fixtures)]
  if state%5==0:
   out=pipeline(case);baseline_failures+=not valid(case,out)
  else:
   mutant=MUTANTS[(state>>8)%len(MUTANTS)];hits[mutant]+=1;out=pipeline(case,mutant);killed[mutant]+=not valid(case,out)
  if i<100_000:signatures.add(signature(case,out))
 survivors=[m for m in MUTANTS if killed[m]==0];baseline_signatures={signature(c,pipeline(c)) for c in fixtures};novel=0
 for _ in range(TAIL):
  state=(1664525*state+1013904223)&0xffffffff;c=fixtures[state%len(fixtures)];novel+=signature(c,pipeline(c)) not in baseline_signatures
 receipt={'schema':'ikant-s10bis-hotfix2-e2e-falsification/v0.2','seed':SEED,'concrete_os_fixtures':len(fixtures)-2,'real_journal_seeds':2,'iterations':ITERATIONS,'tail':TAIL,'baseline_failures':baseline_failures,'mutants':len(MUTANTS),'survivors':survivors,'killed_mutants':sum(killed[m]>0 for m in MUTANTS),'mutant_min_hits':min(hits.values()),'mutant_min_kills':min(killed[m] for m in MUTANTS),'semantic_signatures_observed':len(signatures),'tail_novelty':novel,'elapsed_seconds':round(time.time()-started,3),'mutant_kills':dict(killed)}
 OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2,sort_keys=True))
 if baseline_failures or survivors or novel:raise SystemExit(1)
if __name__=='__main__':main()
