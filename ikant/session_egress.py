from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib, json, os, threading
from pathlib import Path
from typing import Any
from .invariants import EGRESS_SCHEMA, LEGACY_EGRESS_SCHEMA, V09_EGRESS_SCHEMA, FRAME_SCHEMA, JOURNAL_SCHEMA, LEGACY_JOURNAL_SCHEMA, EXIT_COMMAND, RESUME_COMMAND, MAX_FRAME_BYTES
from .store import atomic_json_write, append_jsonl
from .transport import TransportAttestation, validate_transport_attestation
_BIDI={chr(x) for x in list(range(8234,8239))+list(range(8294,8298))}

def _now(): return datetime.now(timezone.utc).isoformat()
def _sha_text(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def _sha_payload(payload): return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class EgressState(str,Enum):
    LOCKED='DASHBOARD_LOCKED'; FRAME_PENDING='FRAME_PENDING'; RELEASE_PENDING='RELEASE_PENDING'; RELEASED='RELEASED'; BREACHED='EGRESS_BREACHED'
@dataclass(frozen=True)
class EgressRecord:
    schema:str; runtime_session_id:str; state:str; epoch:int; frame_seq:int; last_frame_sha256:str|None; last_cycle_id:str|None; last_kind:str|None; updated_at:str; breach_reason:str|None=None; journal_seq:int=0; last_journal_sha256:str='0'*64; pending_frame_path:str|None=None
@dataclass(frozen=True)
class FrameReceipt:
    schema:str; runtime_session_id:str; epoch:int; frame_seq:int; kind:str; cycle_id:str|None; frame_sha256:str; release_after_frame:bool
class EgressViolation(RuntimeError): pass

class DashboardEgressGuard:
    def __init__(self,path:str|Path,*,runtime_session_id:str):
        self.path=Path(path); self.runtime_session_id=str(runtime_session_id)
        if not self.runtime_session_id: raise ValueError('runtime_session_id required')
        self.path.parent.mkdir(parents=True,exist_ok=True); self.journal_path=self.path.with_name('egress-events.jsonl'); self.frames_dir=self.path.with_name('egress-frames'); self.frames_dir.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock(); self.record=self._load(); self.verify()
    @classmethod
    def create(cls,path:str|Path,*,runtime_session_id:str):
        p=Path(path)
        if p.exists(): raise EgressViolation('egress state already exists')
        self=cls.__new__(cls); self.path=p; self.runtime_session_id=str(runtime_session_id)
        if not self.runtime_session_id: raise ValueError('runtime_session_id required')
        p.parent.mkdir(parents=True,exist_ok=True); self.journal_path=p.with_name('egress-events.jsonl'); self.frames_dir=p.with_name('egress-frames'); self.frames_dir.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock(); rec=EgressRecord(EGRESS_SCHEMA,self.runtime_session_id,EgressState.LOCKED.value,1,0,None,None,None,_now()); rec=self._journal(rec,'CREATE'); self._write(rec); self.record=rec; return self
    def _write(self,rec): atomic_json_write(self.path,asdict(rec))
    def _journal(self,rec,event,payload=None):
        seq=rec.journal_seq+1; body={'schema':JOURNAL_SCHEMA,'seq':seq,'at':_now(),'runtime_session_id':self.runtime_session_id,'event':str(event),'state':rec.state,'epoch':rec.epoch,'frame_seq':rec.frame_seq,'payload':dict(payload or {}),'prev_sha256':rec.last_journal_sha256}; body['sha256']=_sha_payload(body); append_jsonl(self.journal_path,body); return replace(rec,journal_seq=seq,last_journal_sha256=body['sha256'],updated_at=body['at'])
    def _migrate_v10(self,raw):
        state=str(raw.get('state') or '')
        if state not in {x.value for x in EgressState}: raise EgressViolation('legacy v0.10 egress state invalid')
        rec=EgressRecord(EGRESS_SCHEMA,self.runtime_session_id,state,max(1,int(raw.get('epoch',1))),max(0,int(raw.get('frame_seq',0))),raw.get('last_frame_sha256'),raw.get('last_cycle_id'),raw.get('last_kind'),_now(),breach_reason=raw.get('breach_reason'),journal_seq=max(0,int(raw.get('journal_seq',0))),last_journal_sha256=str(raw.get('last_journal_sha256') or '0'*64),pending_frame_path=raw.get('pending_frame_path'))
        rec=self._journal(rec,'MIGRATE_V10',{'legacy_state':state,'pending_preserved':state in {EgressState.FRAME_PENDING.value,EgressState.RELEASE_PENDING.value}}); self._write(rec); return rec
    def _migrate_v09(self,raw):
        state=str(raw.get('state') or '')
        if state not in {x.value for x in EgressState}: raise EgressViolation('legacy v0.9 egress state invalid')
        unsafe=state in {EgressState.FRAME_PENDING.value,EgressState.RELEASE_PENDING.value}
        rec=EgressRecord(EGRESS_SCHEMA,self.runtime_session_id,EgressState.BREACHED.value if unsafe else state,max(1,int(raw.get('epoch',1))),max(0,int(raw.get('frame_seq',0))),raw.get('last_frame_sha256'),raw.get('last_cycle_id'),raw.get('last_kind'),_now(),breach_reason='legacy v0.9 pending frame is not crash-recoverable' if unsafe else raw.get('breach_reason'))
        rec=self._journal(rec,'MIGRATE_V09',{'legacy_state':state,'unsafe_pending':unsafe}); self._write(rec); return rec
    def _load(self):
        if not self.path.exists(): raise EgressViolation('required egress state missing')
        try: raw=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as exc: raise EgressViolation('egress state unreadable') from exc
        if raw.get('schema')==LEGACY_EGRESS_SCHEMA: return self._migrate_v10(raw)
        if raw.get('schema')==V09_EGRESS_SCHEMA: return self._migrate_v09(raw)
        try: rec=EgressRecord(**raw)
        except (TypeError,ValueError) as exc: raise EgressViolation('egress state shape invalid') from exc
        if rec.schema!=EGRESS_SCHEMA: raise EgressViolation('egress schema mismatch')
        if rec.runtime_session_id!=self.runtime_session_id: raise EgressViolation('egress runtime session mismatch')
        if rec.state not in {x.value for x in EgressState}: raise EgressViolation('egress state invalid')
        return rec
    @property
    def state(self): return EgressState(self.record.state)
    def require_locked(self):
        if self.state!=EgressState.LOCKED: raise EgressViolation(f'iKant dashboard egress not locked: {self.state.value}')
    def classify_user_text(self,text): return 'EXIT' if text==EXIT_COMMAND else ('RESUME' if text==RESUME_COMMAND else 'INTENT')
    def _validate_frame(self,text):
        if not text.strip(): raise EgressViolation('dashboard frame must not be empty')
        if len(text.encode('utf-8'))>MAX_FRAME_BYTES: raise EgressViolation('dashboard frame exceeds bound')
        if '\r' in text or '\x1b' in text or '\x00' in text or any(ch in _BIDI for ch in text): raise EgressViolation('dashboard frame contains forbidden control bytes')
    def _pending_path(self,epoch,seq): return self.frames_dir/f'epoch-{epoch:04d}-frame-{seq:08d}.txt'
    def _persist_pending(self,path,text):
        tmp=path.with_suffix(path.suffix+'.tmp')
        with tmp.open('w',encoding='utf-8',newline='\n') as h: h.write(text); h.flush(); os.fsync(h.fileno())
        tmp.replace(path)
    def seal_frame(self,frame_text,*,kind,cycle_id=None,release_after_frame=False):
        with self._lock:
            self.require_locked(); text=str(frame_text); self._validate_frame(text); seq=self.record.frame_seq+1; dg=_sha_text(text); p=self._pending_path(self.record.epoch,seq); self._persist_pending(p,text); st=EgressState.RELEASE_PENDING.value if release_after_frame else EgressState.FRAME_PENDING.value; rec=replace(self.record,state=st,frame_seq=seq,last_frame_sha256=dg,last_cycle_id=cycle_id,last_kind=str(kind),breach_reason=None,pending_frame_path=str(p)); rec=self._journal(rec,'SEAL_FRAME',{'kind':str(kind),'cycle_id':cycle_id,'frame_sha256':dg,'release':bool(release_after_frame)}); self._write(rec); self.record=rec; return FrameReceipt(FRAME_SCHEMA,self.runtime_session_id,rec.epoch,seq,str(kind),cycle_id,dg,bool(release_after_frame))
    def pending_frame(self):
        with self._lock:
            if self.state not in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}: return None
            if not self.record.pending_frame_path: self._breach('pending frame path missing'); raise EgressViolation('pending frame path missing')
            p=Path(self.record.pending_frame_path)
            try: text=p.read_text(encoding='utf-8')
            except OSError as exc: self._breach('pending frame artifact unreadable'); raise EgressViolation('pending frame artifact unreadable') from exc
            if _sha_text(text)!=self.record.last_frame_sha256: self._breach('pending frame artifact digest mismatch'); raise EgressViolation('pending frame artifact digest mismatch')
            return FrameReceipt(FRAME_SCHEMA,self.runtime_session_id,self.record.epoch,self.record.frame_seq,str(self.record.last_kind or 'RECOVERY'),self.record.last_cycle_id,str(self.record.last_frame_sha256),self.state==EgressState.RELEASE_PENDING),text
    def _breach(self,reason):
        rec=replace(self.record,state=EgressState.BREACHED.value,breach_reason=str(reason),pending_frame_path=None); rec=self._journal(rec,'BREACH',{'reason':str(reason)}); self._write(rec); self.record=rec
    def acknowledge_visible(self,receipt,actual_visible_text):
        with self._lock:
            if self.state not in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}: self._breach('acknowledgement without pending frame'); return False
            ok=receipt.schema==FRAME_SCHEMA and receipt.runtime_session_id==self.runtime_session_id and receipt.epoch==self.record.epoch and receipt.frame_seq==self.record.frame_seq and receipt.frame_sha256==self.record.last_frame_sha256 and _sha_text(str(actual_visible_text))==receipt.frame_sha256 and bool(receipt.release_after_frame)==(self.state==EgressState.RELEASE_PENDING)
            if not ok: self._breach('human-visible output differed from sealed dashboard frame'); return False
            p=Path(self.record.pending_frame_path) if self.record.pending_frame_path else None; st=EgressState.RELEASED.value if self.state==EgressState.RELEASE_PENDING else EgressState.LOCKED.value; event='ACK_RELEASE' if st==EgressState.RELEASED.value else 'ACK_FRAME'; rec=replace(self.record,state=st,pending_frame_path=None); rec=self._journal(rec,event,{'frame_sha256':receipt.frame_sha256}); self._write(rec); self.record=rec
            if p:
                try: p.unlink()
                except FileNotFoundError: pass
            return True
    def resume(self,*,runtime_integrity_ok:bool,transport_attestation:TransportAttestation|dict|None=None):
        with self._lock:
            if self.state not in {EgressState.RELEASED,EgressState.BREACHED}: raise EgressViolation('resume only valid after release or egress breach')
            if not runtime_integrity_ok: raise EgressViolation('runtime integrity required to resume iKant')
            attested=False; attestation_sha=None
            if self.state==EgressState.BREACHED:
                ok,errs=validate_transport_attestation(transport_attestation)
                if not ok: raise EgressViolation('breach resume requires valid host transport attestation: '+'; '.join(errs))
                raw=asdict(transport_attestation) if isinstance(transport_attestation,TransportAttestation) else dict(transport_attestation); attested=True; attestation_sha=raw.get('sha256')
            rec=replace(self.record,state=EgressState.LOCKED.value,epoch=self.record.epoch+1,frame_seq=0,last_frame_sha256=None,last_cycle_id=None,last_kind=None,breach_reason=None,pending_frame_path=None); rec=self._journal(rec,'RESUME',{'runtime_integrity_ok':True,'transport_attested':attested,'transport_attestation_sha256':attestation_sha}); self._write(rec); self.record=rec
    def verify(self):
        rows=[]
        if self.journal_path.exists():
            for n,line in enumerate(self.journal_path.read_text(encoding='utf-8').splitlines(),1):
                if not line.strip(): continue
                try: rows.append(json.loads(line))
                except json.JSONDecodeError as exc: raise EgressViolation(f'egress journal malformed at line {n}') from exc
        prev='0'*64
        for seq,row in enumerate(rows,1):
            if row.get('schema') not in {LEGACY_JOURNAL_SCHEMA,JOURNAL_SCHEMA} or row.get('seq')!=seq or row.get('runtime_session_id')!=self.runtime_session_id or row.get('prev_sha256')!=prev: raise EgressViolation('egress journal sequence/schema/session/predecessor mismatch')
            supplied=row.get('sha256'); material=dict(row); material.pop('sha256',None)
            if supplied!=_sha_payload(material): raise EgressViolation('egress journal digest mismatch')
            prev=supplied
        if self.record.journal_seq!=len(rows) or self.record.last_journal_sha256!=prev: raise EgressViolation('egress state/journal divergence')
        if self.state in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}: self.pending_frame()
        elif self.record.pending_frame_path is not None: raise EgressViolation('non-pending state references pending artifact')
        return {'schema':'ikant-dashboard-egress-integrity/v0.11-test','ok':True,'state':self.record.state,'epoch':self.record.epoch,'frame_seq':self.record.frame_seq,'journal_seq':self.record.journal_seq,'pending_recoverable':self.state in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}}
    def attach_projection(self,dashboard,*,notice=None):
        out=dict(dashboard); out['session_egress']={'schema':EGRESS_SCHEMA,'state':self.record.state,'epoch':self.record.epoch,'frame_seq':self.record.frame_seq,'journal_seq':self.record.journal_seq,'exclusive_human_output':self.state in {EgressState.LOCKED,EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING},'recovery_required':self.state in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING},'exit_command':EXIT_COMMAND,'resume_command':RESUME_COMMAND,'notice':notice}; return out

def egress_path(runtime): return Path(runtime.state_dir)/'egress.json'
def _marker(runtime): return (runtime.runtime.get('egress_guard') or {}) if isinstance(getattr(runtime,'runtime',None),dict) else {}
def _mark_required(runtime,*,adopted=False):
    runtime.runtime['egress_guard']={'required':True,'schema':EGRESS_SCHEMA,'runtime_session_id':str(runtime.runtime.get('session_id') or ''),'adopted_legacy':bool(adopted)}; runtime._write_runtime(); runtime._event('EGRESS_REQUIRED',runtime.runtime.get('session_id'),{'schema':EGRESS_SCHEMA,'adopted_legacy':bool(adopted)})
def activate_runtime_egress(runtime,*,initialization=False):
    runtime.require_active(); path=egress_path(runtime); marker=_marker(runtime)
    if marker.get('required'):
        if not path.exists(): raise EgressViolation('required egress state missing; silent recreation forbidden')
        return DashboardEgressGuard(path,runtime_session_id=str(runtime.runtime.get('session_id') or ''))
    if path.exists():
        guard=DashboardEgressGuard(path,runtime_session_id=str(runtime.runtime.get('session_id') or '')); _mark_required(runtime,adopted=True); return guard
    if not initialization: raise EgressViolation('ACTIVE runtime has no egress guard; creation is initialization-only')
    guard=DashboardEgressGuard.create(path,runtime_session_id=str(runtime.runtime.get('session_id') or '')); _mark_required(runtime,adopted=False); return guard
def existing_runtime_egress(runtime):
    path=egress_path(runtime); marker=_marker(runtime)
    if not path.exists():
        if marker.get('required'): raise EgressViolation('required egress state missing; fail closed')
        return None
    guard=DashboardEgressGuard(path,runtime_session_id=str(runtime.runtime.get('session_id') or ''))
    if not marker.get('required'): _mark_required(runtime,adopted=True)
    return guard
