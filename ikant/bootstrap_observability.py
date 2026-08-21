from __future__ import annotations
import hashlib,json,os,re,secrets,threading,time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
EVENT_SCHEMA='ikant-bootstrap-event/v0.29-test';STATUS_SCHEMA='ikant-bootstrap-status/v0.29-test';EVENTS_SCHEMA='ikant-bootstrap-events/v0.29-test';MAX_EVENT_BYTES=16*1024;MAX_API_EVENTS=256;MAX_RAW_BYTES=8*1024*1024;MAX_ARCHIVES=4
STEPS=(('WEB_APP','Web app locale'),('MANIFEST','Manifest runtime'),('ENGINE_COMPONENT','Engine locale'),('MODEL_COMPONENT','Modello LLM locale'),('ENGINE_PROCESS','Processo LLM'),('ENGINE_READINESS','Readiness LLM'),('PRODUCT_SERVICE','Servizio iKant'));STEP_IDS=frozenset(x[0] for x in STEPS);OUTCOMES=frozenset({'START','PROGRESS','PASS','FAIL','INFO'});_REDACT=re.compile(r'(?i)(authorization\s*[:=]\s*bearer\s+|api[_-]?key\s*[:=]\s*|token\s*[:=]\s*|password\s*[:=]\s*)([^\s,;]+)');_QUERY=re.compile(r'(https://[^\s?]+)\?[^\s]+')
class BootstrapDiagnosticError(RuntimeError):pass
@dataclass(frozen=True)
class JournalState:seq:int;tail_sha256:str;integrity:str
def new_attempt_id()->str:return f'ATT-{time.time_ns()//1_000_000:013d}-{secrets.token_hex(6)}'
def safe_text(v:Any,limit:int=1024)->str:
 s=str(v or '').replace('\x00','').replace('\r',' ').replace('\n',' ').strip();s=_REDACT.sub(lambda m:m.group(1)+'[REDACTED]',s);s=_QUERY.sub(r'\1?[REDACTED]',s);return s[:limit]
def exception_chain(exc:BaseException,limit:int=6)->list[dict[str,str]]:
 out=[];seen=set();cur:BaseException|None=exc
 while cur is not None and len(out)<limit and id(cur) not in seen:seen.add(id(cur));out.append({'type':type(cur).__name__,'message':safe_text(cur,768)});cur=cur.__cause__ or cur.__context__
 return out
def classify_failure(step:str,exc:BaseException):
 chain=exception_chain(exc);names={x['type'] for x in chain};msg=' '.join(x['message'].lower() for x in chain)
 if 'DownloadError' in names:
  if any(x in msg for x in ('name resolution','temporary failure','network is unreachable','timed out','timeout','nodename nor servname')):return 'NETWORK_DOWNLOAD_FAILED',{'id':'CHECK_NETWORK_AND_RETRY','label':'Verifica la rete e riprova','action':'retry'}
  if 'digest mismatch' in msg:return 'COMPONENT_DIGEST_MISMATCH',{'id':'REMOVE_PARTIAL_AND_RETRY','label':'Rimuovi il download parziale e riprova','action':'retry'}
  if 'http ' in msg:return 'COMPONENT_HTTP_FAILED',{'id':'CHECK_SOURCE_AND_RETRY','label':'Verifica la sorgente e riprova','action':'retry'}
  if 'exceeds bound' in msg:return 'COMPONENT_DOWNLOAD_BOUND_EXCEEDED',{'id':'VERIFY_RUNTIME_MANIFEST','label':'Verifica dimensione e manifest','action':'manual'}
  return 'COMPONENT_DOWNLOAD_FAILED',{'id':'RETRY_DOWNLOAD','label':'Riprova il download','action':'retry'}
 if 'EngineSupervisorError' in names:
  if 'readiness timeout' in msg:return 'ENGINE_READINESS_TIMEOUT',{'id':'CHECK_ENGINE_AND_RETRY','label':'Controlla il runtime LLM e riprova','action':'retry'}
  if 'exited before readiness' in msg:return 'ENGINE_EXITED_EARLY',{'id':'CHECK_ENGINE_AND_RETRY','label':'Controlla il runtime LLM e riprova','action':'retry'}
  if 'readiness probe failed' in msg:return 'ENGINE_READINESS_FAILED',{'id':'CHECK_ENGINE_AND_RETRY','label':'Controlla la readiness del runtime LLM e riprova','action':'retry'}
  return 'ENGINE_START_FAILED',{'id':'CHECK_ENGINE_AND_RETRY','label':'Controlla il runtime locale e riprova','action':'retry'}
 if 'ModelManagerError' in names or 'ComponentStoreError' in names:return 'COMPONENT_INSTALL_FAILED',{'id':'CLEAR_COMPONENT_CACHE_AND_RETRY','label':'Ripristina il componente locale e riprova','action':'retry'}
 if step=='MANIFEST' or 'ComponentManifestError' in names or 'JSONDecodeError' in names:return 'RUNTIME_MANIFEST_INVALID',{'id':'VERIFY_RUNTIME_MANIFEST','label':'Verifica MODEL_RUNTIME.json','action':'manual'}
 return 'BOOTSTRAP_FAILED',{'id':'OPEN_RAW_DIAGNOSTICS','label':'Apri il log tecnico e riprova','action':'retry'}
def _canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
class BootstrapJournal:
 def __init__(self,root):self.root=Path(root).resolve();self.path=self.root/'.ikant'/'bootstrap-events.jsonl';self.path.parent.mkdir(parents=True,exist_ok=True);self._lock=threading.RLock();self._seq=0;self._tail='0'*64;self._integrity='OK';self._rotate();self._replay()
 @property
 def state(self):return JournalState(self._seq,self._tail,self._integrity)
 def _rotate(self):
  if not self.path.is_file() or self.path.stat().st_size<=MAX_RAW_BYTES:return
  for i in range(MAX_ARCHIVES,0,-1):
   src=self.path.with_name(self.path.name+('' if i==1 else f'.{i-1}'));dst=self.path.with_name(self.path.name+f'.{i}')
   if i==MAX_ARCHIVES:dst.unlink(missing_ok=True)
   if src.exists():os.replace(src,dst)
 def _replay(self):
  if not self.path.is_file():return
  prev='0'*64;seq=0
  try:
   with self.path.open('rb') as fh:
    for raw in fh:
     if len(raw)>MAX_EVENT_BYTES+1:raise BootstrapDiagnosticError('bootstrap journal line outside bound')
     e=json.loads(raw);claimed=str(e.pop('event_sha256',''))
     if e.get('previous_sha256')!=prev or int(e.get('seq') or 0)!=seq+1:raise BootstrapDiagnosticError('bootstrap journal chain discontinuity')
     if hashlib.sha256(_canon(e)).hexdigest()!=claimed:raise BootstrapDiagnosticError('bootstrap journal digest mismatch')
     seq+=1;prev=claimed
   self._seq,self._tail=seq,prev
  except Exception:self._integrity='CORRUPT'
 def append(self,*,attempt_id,attempt,step,outcome,code,target='',detail='',bytes_count=None,total_bytes=None,remediation=None,cause_chain=None):
  if step not in STEP_IDS or outcome not in OUTCOMES or not str(attempt_id).startswith('ATT-'):raise BootstrapDiagnosticError('invalid bootstrap event')
  with self._lock:
   if self._integrity!='OK':raise BootstrapDiagnosticError('bootstrap journal integrity unavailable')
   e={'schema':EVENT_SCHEMA,'seq':self._seq+1,'timestamp_ms':time.time_ns()//1_000_000,'attempt_id':safe_text(attempt_id,64),'attempt':max(1,int(attempt)),'step':step,'outcome':outcome,'code':safe_text(code,96),'target':safe_text(target,192),'detail':safe_text(detail,1024),'bytes':max(0,int(bytes_count)) if isinstance(bytes_count,int) and not isinstance(bytes_count,bool) else None,'total_bytes':max(0,int(total_bytes)) if isinstance(total_bytes,int) and not isinstance(total_bytes,bool) else None,'remediation':{'id':safe_text((remediation or {}).get('id'),96),'label':safe_text((remediation or {}).get('label'),240),'action':safe_text((remediation or {}).get('action'),32)} if remediation else None,'cause_chain':[{'type':safe_text(x.get('type'),96),'message':safe_text(x.get('message'),768)} for x in (cause_chain or [])[:6]],'previous_sha256':self._tail,'epistemic_authority':0.0,'execution_authority':0.0};digest=hashlib.sha256(_canon(e)).hexdigest();e['event_sha256']=digest;raw=_canon(e)+b'\n'
   if len(raw)>MAX_EVENT_BYTES:raise BootstrapDiagnosticError('bootstrap event outside bound')
   fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
   try:os.write(fd,raw);os.fsync(fd)
   finally:os.close(fd)
   self._seq+=1;self._tail=digest;return dict(e)
 def _scan(self,attempt_id=None,after_seq=0,limit=None):
  out=[]
  if not self.path.is_file():return out
  try:
   with self.path.open('r',encoding='utf-8') as fh:
    for line in fh:
     e=json.loads(line)
     if int(e.get('seq') or 0)<=int(after_seq):continue
     if attempt_id is not None and str(e.get('attempt_id') or '')!=str(attempt_id):continue
     out.append(e)
     if limit and len(out)>=limit:break
  except Exception:return []
  return out
 def events(self,*,attempt_id=None,after_seq=0,limit=MAX_API_EVENTS):return self._scan(attempt_id,after_seq,max(1,min(MAX_API_EVENTS,int(limit))))
 def raw_bytes(self):
  if not self.path.is_file():return b''
  if self.path.stat().st_size>MAX_RAW_BYTES:raise BootstrapDiagnosticError('bootstrap raw log outside API bound')
  return self.path.read_bytes()
 def status(self,*,attempt_id,attempt):
  latest={}
  for e in self._scan(attempt_id):latest[str(e.get('step') or '')]=e
  rows=[];passed=failed=running=0
  for sid,label in STEPS:
   e=latest.get(sid);st=str(e.get('outcome')) if e else 'PENDING';passed+=st=='PASS';failed+=st=='FAIL';running+=st in {'START','PROGRESS','INFO'};rows.append({'id':sid,'label':label,'status':st,'code':e.get('code') if e else None,'target':e.get('target') if e else None,'detail':e.get('detail') if e else None,'bytes':e.get('bytes') if e else None,'total_bytes':e.get('total_bytes') if e else None,'remediation':e.get('remediation') if e else None,'seq':e.get('seq') if e else None})
  overall='BLOCKED' if failed else 'READY' if passed==len(STEPS) else 'PREPARING' if running or latest else 'STARTING';raw_ok=self.path.is_file() and self.path.stat().st_size<=MAX_RAW_BYTES;return {'schema':STATUS_SCHEMA,'attempt_id':str(attempt_id),'attempt':max(1,int(attempt)),'overall':overall,'steps':rows,'summary':{'passed':passed,'failed':failed,'running':running,'total':len(STEPS)},'journal':{'path':'.ikant/bootstrap-events.jsonl','integrity':self._integrity,'last_seq':self._seq,'tail_sha256':self._tail,'raw_available':raw_ok},'silent_failure':bool(overall=='BLOCKED' and failed==0),'presentation_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
