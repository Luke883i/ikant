from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,os,time
from pathlib import Path
from typing import Any,Iterable

from .human_frame import ActorSessionBinding,normalize_entitlements,validate_human_frame,validate_interaction_receipt
from .store import acquire_writer_lock,atomic_json_write

AGENCY_EVENT_SCHEMA='ikant-agency-event/v0.19-test'
AGENCY_PROJECTION_SCHEMA='ikant-agency-projection/v0.19-test'
CAPABILITY_GRANT_SCHEMA='ikant-capability-grant/v0.19-test'
EXECUTION_LEASE_SCHEMA='ikant-execution-lease/v0.19-test'

class AgencyIntegrityError(RuntimeError):pass
class AgencyAuthorityError(PermissionError):pass

def _canonical(payload:dict[str,Any])->bytes:
    return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def _digest(payload:dict[str,Any])->str:return hashlib.sha256(_canonical(payload)).hexdigest()
def _now(value:float|None)->float:return float(time.time() if value is None else value)

def _grant_id(frame:dict[str,Any],receipt:dict[str,Any])->str:
    return 'cg-'+_digest({'frame_sha256':frame.get('sha256'),'receipt_mac':receipt.get('mac_sha256'),'session_id':frame.get('session_id')})[:24]
def _lease_id(binding:dict[str,Any],grant_refs:list[dict[str,Any]],ents:tuple[tuple[str,str],...])->str:
    return 'xl-'+_digest({'binding':binding,'grant_refs':grant_refs,'entitlements':ents})[:24]

class AgencyJournal:
    def __init__(self,path:str|Path,*,session_id:str):
        self.path=Path(path);self.session_id=str(session_id);self.path.parent.mkdir(parents=True,exist_ok=True)
    def rows(self)->list[dict[str,Any]]:
        if not self.path.exists():return []
        out=[]
        for lineno,line in enumerate(self.path.read_text(encoding='utf-8').splitlines(),1):
            if not line.strip():continue
            try:out.append(json.loads(line))
            except json.JSONDecodeError as exc:raise AgencyIntegrityError(f'malformed agency journal line {lineno}') from exc
        return out
    def verify(self)->dict[str,Any]:
        rows=self.rows();prev='0'*64
        for seq,row in enumerate(rows,1):
            if row.get('schema')!=AGENCY_EVENT_SCHEMA:raise AgencyIntegrityError('agency event schema mismatch')
            if row.get('seq')!=seq:raise AgencyIntegrityError('agency event sequence non-contiguous')
            if row.get('session_id')!=self.session_id:raise AgencyIntegrityError('agency event session mismatch')
            if row.get('prev_sha256')!=prev:raise AgencyIntegrityError('agency event predecessor mismatch')
            material=dict(row);actual=material.pop('sha256',None)
            if actual!=_digest(material):raise AgencyIntegrityError('agency event digest mismatch')
            prev=actual
        return {'ok':True,'events':len(rows),'last_sha256':prev}
    def append(self,event_type:str,payload:dict[str,Any],*,at:float|None=None)->dict[str,Any]:
        rows=self.rows();self.verify();prev=rows[-1]['sha256'] if rows else '0'*64
        row={'schema':AGENCY_EVENT_SCHEMA,'seq':len(rows)+1,'session_id':self.session_id,'at':_now(at),'event_type':str(event_type),'payload':payload,'prev_sha256':prev}
        row['sha256']=_digest(row)
        with self.path.open('a',encoding='utf-8') as h:
            h.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');h.flush();os.fsync(h.fileno())
        return row

@dataclass(frozen=True)
class AgencyState:
    grants:dict[str,dict[str,Any]]
    leases:dict[str,dict[str,Any]]
    events:int
    journal_sha256:str

class AgencyKernel:
    """Durable zero-epistemic-authority capability/lease kernel.

    The journal is canonical. JSON projection is rebuildable. Human interaction is channel-bound,
    not a proof of civil identity. Capability grants never bypass v0.15-v0.18 governance; leases
    merely add an execution precondition for a concrete v0.17 handoff.
    """
    def __init__(self,state_dir:str|Path,*,session_id:str,binding:ActorSessionBinding,interaction_secret:bytes,durable:bool=True):
        self.state_dir=Path(state_dir);self.session_id=str(session_id);self.binding=binding;self.secret=bytes(interaction_secret);self.durable=bool(durable)
        if binding.session_id!=self.session_id:raise ValueError('agency binding session mismatch')
        if len(self.secret)<32:raise ValueError('interaction secret must be at least 32 bytes')
        self.journal=AgencyJournal(self.state_dir/'agency-events.jsonl',session_id=self.session_id)
        self.projection_path=self.state_dir/'agency.json';self.lock_path=self.state_dir/'agency.writer.lock'
        self.journal.verify();self._persist_projection()
    def _locked(self):return acquire_writer_lock(self.lock_path)
    def state(self)->AgencyState:
        grants={};leases={};rows=self.journal.rows();last='0'*64
        for row in rows:
            last=row['sha256'];typ=row['event_type'];p=dict(row.get('payload') or {})
            if typ=='GRANT_ISSUED':grants[p['grant_id']]=dict(p)
            elif typ=='GRANT_REVOKED':
                gid=p['grant_id']
                if gid not in grants:raise AgencyIntegrityError('revocation references missing grant')
                grants[gid]={**grants[gid],'status':'REVOKED','grant_epoch':int(p['grant_epoch']),'revoked_at':p['revoked_at'],'revocation_frame_sha256':p['frame_sha256']}
            elif typ=='LEASE_ISSUED':leases[p['lease_id']]=dict(p)
            elif typ in {'LEASE_CONSUMED','LEASE_CANCELLED'}:
                lid=p['lease_id']
                if lid not in leases:raise AgencyIntegrityError('lease terminal event references missing lease')
                leases[lid]={**leases[lid],'status':'CONSUMED' if typ=='LEASE_CONSUMED' else 'CANCELLED','terminal_at':p['at'],'terminal_reason':p.get('reason')}
            else:raise AgencyIntegrityError('unknown agency event type')
        return AgencyState(grants,leases,len(rows),last)
    def projection(self)->dict[str,Any]:
        st=self.state();return {'schema':AGENCY_PROJECTION_SCHEMA,'session_id':self.session_id,'actor_binding_id':self.binding.binding_id,'channel_authenticated':True,'human_identity_proven':False,'grant_count':len(st.grants),'active_grant_count':sum(1 for g in st.grants.values() if g.get('status')=='ACTIVE'),'lease_count':len(st.leases),'pending_lease_count':sum(1 for l in st.leases.values() if l.get('status')=='PENDING'),'journal_events':st.events,'journal_sha256':st.journal_sha256,'epistemic_authority':0.0,'execution_authority':0.0,'runtime_executes_actions':False}
    def _persist_projection(self):
        if self.durable:atomic_json_write(self.projection_path,self.projection())
    def verify(self)->dict[str,Any]:self.journal.verify();self.state();return {**self.projection(),'ok':True}
    def _append(self,typ:str,payload:dict[str,Any],*,at:float|None=None):
        lock=self._locked()
        try:
            row=self.journal.append(typ,payload,at=at);self._persist_projection();return row
        finally:lock.release()
    def issue_grant(self,frame:dict[str,Any],receipt:dict[str,Any],*,now:float|None=None)->dict[str,Any]:
        ok,fe=validate_human_frame(frame)
        if not ok:raise AgencyAuthorityError('invalid grant frame: '+'; '.join(fe))
        ok,re=validate_interaction_receipt(frame,receipt,binding=self.binding,secret=self.secret)
        if not ok:raise AgencyAuthorityError('invalid grant interaction: '+'; '.join(re))
        if frame.get('purpose')!='CAPABILITY_GRANT' or receipt.get('decision')!='APPROVE':raise AgencyAuthorityError('explicit capability grant approval required')
        if frame.get('session_id')!=self.session_id:raise AgencyAuthorityError('grant session mismatch')
        gid=_grant_id(frame,receipt);st=self.state()
        if gid in st.grants:return dict(st.grants[gid])
        expires=frame.get('expires_at');t=_now(now)
        if expires is not None and float(expires)<=t:raise AgencyAuthorityError('grant already expired')
        ents=normalize_entitlements(frame.get('requested_entitlements',[]) or [])
        grant={'schema':CAPABILITY_GRANT_SCHEMA,'grant_id':gid,'session_id':self.session_id,'actor_binding_id':self.binding.binding_id,'frame_sha256':frame['sha256'],'receipt_mac_sha256':receipt['mac_sha256'],'entitlements':[{'capability':c,'resource':r} for c,r in ents],'max_uses':int(frame.get('max_uses',1)),'expires_at':None if expires is None else float(expires),'grant_epoch':0,'status':'ACTIVE','issued_at':t,'human_identity_proven':False,'channel_authenticated':True,'epistemic_authority':0.0,'execution_authority':0.0,'grant_is_not_execution':True}
        grant['sha256']=_digest(grant);self._append('GRANT_ISSUED',grant,at=t);return grant
    def revoke_grant(self,grant_id:str,frame:dict[str,Any],receipt:dict[str,Any],*,now:float|None=None)->dict[str,Any]:
        gid=str(grant_id);st=self.state();grant=st.grants.get(gid)
        if not grant:raise AgencyAuthorityError('grant not found')
        if grant.get('status')=='REVOKED':return dict(grant)
        ok,fe=validate_human_frame(frame)
        if not ok:raise AgencyAuthorityError('invalid revoke frame: '+'; '.join(fe))
        ok,re=validate_interaction_receipt(frame,receipt,binding=self.binding,secret=self.secret)
        if not ok:raise AgencyAuthorityError('invalid revoke interaction: '+'; '.join(re))
        if frame.get('purpose')!='CAPABILITY_REVOKE' or frame.get('subject_id')!=gid or receipt.get('decision')!='REVOKE':raise AgencyAuthorityError('explicit grant-bound revocation required')
        t=_now(now);epoch=int(grant.get('grant_epoch',0))+1
        self._append('GRANT_REVOKED',{'grant_id':gid,'grant_epoch':epoch,'revoked_at':t,'frame_sha256':frame['sha256'],'receipt_mac_sha256':receipt['mac_sha256']},at=t)
        return dict(self.state().grants[gid])
    def _grant_available(self,grant:dict[str,Any],st:AgencyState,now:float)->bool:
        if grant.get('status')!='ACTIVE':return False
        exp=grant.get('expires_at')
        if exp is not None and float(exp)<=now:return False
        reserved=0;gid=grant['grant_id']
        for lease in st.leases.values():
            if lease.get('status')=='CANCELLED':continue
            if any(ref.get('grant_id')==gid for ref in lease.get('grant_refs',[]) or []):reserved+=1
        return reserved<int(grant.get('max_uses',1))
    def issue_lease(self,envelope:dict[str,Any],entitlements:Iterable,*,now:float|None=None,expires_at:float|None=None)->dict[str,Any]:
        if str(envelope.get('session_id') or '')!=self.session_id:raise AgencyAuthorityError('handoff session mismatch')
        if envelope.get('handoff_state')!='HOST_REVALIDATION_REQUIRED' or envelope.get('handoff_kind')!='HOST':raise AgencyAuthorityError('handoff not host-revalidation-ready')
        if envelope.get('execution_eligible') is not False or envelope.get('execution_authority') not in {0,0.0}:raise AgencyAuthorityError('handoff authority boundary drift')
        if not str(envelope.get('handoff_id') or '') or not str(envelope.get('idempotency_key') or '') or not str(envelope.get('action_fingerprint') or ''):raise AgencyAuthorityError('handoff binding incomplete')
        ents=normalize_entitlements(entitlements);required_caps=tuple(sorted(set(str(x).strip().casefold() for x in envelope.get('required_capabilities',[]) or [])))
        ent_caps=tuple(sorted(set(c for c,_ in ents)))
        if not ents or ent_caps!=required_caps:raise AgencyAuthorityError('lease entitlements must exactly cover handoff required capabilities')
        binding={k:envelope.get(k) for k in ('session_id','cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256','plan_id','step_id')}
        if any(v in {None,''} for v in binding.values()):raise AgencyAuthorityError('handoff exact binding incomplete')
        t=_now(now);st=self.state();chosen=[]
        for entitlement in ents:
            matches=[]
            for gid,grant in st.grants.items():
                granted={(x.get('capability'),x.get('resource')) for x in grant.get('entitlements',[]) or []}
                if entitlement in granted and self._grant_available(grant,st,t):matches.append(grant)
            if not matches:raise AgencyAuthorityError('missing active grant for entitlement:'+entitlement[0]+'@'+entitlement[1])
            chosen.append(sorted(matches,key=lambda g:g['grant_id'])[0])
        refs=[]
        for g in sorted({g['grant_id']:g for g in chosen}.values(),key=lambda g:g['grant_id']):refs.append({'grant_id':g['grant_id'],'grant_epoch':int(g.get('grant_epoch',0)),'grant_sha256':g.get('sha256')})
        lid=_lease_id(binding,refs,ents);existing=st.leases.get(lid)
        if existing:
            if existing.get('status')=='PENDING' and self.validate_lease(existing,envelope,now=t)[0]:return dict(existing)
            raise AgencyAuthorityError('lease replay after terminal or invalid state')
        effective_exp=expires_at;grant_exps=[float(g['expires_at']) for g in chosen if g.get('expires_at') is not None]
        if grant_exps:effective_exp=min(float(effective_exp),min(grant_exps)) if effective_exp is not None else min(grant_exps)
        if effective_exp is not None and float(effective_exp)<=t:raise AgencyAuthorityError('lease already expired')
        lease={'schema':EXECUTION_LEASE_SCHEMA,'lease_id':lid,**binding,'entitlements':[{'capability':c,'resource':r} for c,r in ents],'grant_refs':refs,'issued_at':t,'expires_at':None if effective_exp is None else float(effective_exp),'status':'PENDING','one_shot':True,'outbox_state':'PENDING','epistemic_authority':0.0,'execution_authority':0.0,'lease_is_precondition_not_execution':True,'runtime_executes_action':False}
        lease['sha256']=_digest(lease);self._append('LEASE_ISSUED',lease,at=t);return lease
    def validate_lease(self,lease:dict[str,Any],envelope:dict[str,Any],*,now:float|None=None)->tuple[bool,list[str]]:
        t=_now(now);raw=dict(lease or {});e=[];st=self.state()
        if raw.get('schema')!=EXECUTION_LEASE_SCHEMA:e.append('lease schema')
        current=st.leases.get(str(raw.get('lease_id') or ''))
        if not current or current.get('sha256')!=raw.get('sha256'):e.append('lease journal binding')
        if current and current.get('status')!='PENDING':e.append('lease not pending')
        if raw.get('session_id')!=self.session_id or raw.get('session_id')!=envelope.get('session_id'):e.append('lease session')
        for key in ('cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256','plan_id','step_id'):
            if raw.get(key)!=envelope.get(key):e.append('lease '+key)
        if raw.get('one_shot') is not True or raw.get('outbox_state')!='PENDING':e.append('lease outbox')
        if raw.get('execution_authority') not in {0,0.0} or raw.get('runtime_executes_action') is not False:e.append('lease authority')
        exp=raw.get('expires_at')
        if exp is not None and float(exp)<=t:e.append('lease expired')
        for ref in raw.get('grant_refs',[]) or []:
            grant=st.grants.get(str(ref.get('grant_id') or ''))
            if not grant or grant.get('status')!='ACTIVE':e.append('lease grant inactive');continue
            if int(grant.get('grant_epoch',-1))!=int(ref.get('grant_epoch',-2)):e.append('lease grant epoch')
            if grant.get('sha256')!=ref.get('grant_sha256'):e.append('lease grant digest')
            gexp=grant.get('expires_at')
            if gexp is not None and float(gexp)<=t:e.append('lease grant expired')
        material=dict(raw);actual=material.pop('sha256',None)
        if actual!=_digest(material):e.append('lease digest')
        return not e,e
    def consume_lease(self,lease_id:str,*,now:float|None=None,reason:str='external terminal receipt recorded')->dict[str,Any]:
        st=self.state();lease=st.leases.get(str(lease_id))
        if not lease:raise AgencyAuthorityError('lease not found')
        if lease.get('status')=='CONSUMED':return dict(lease)
        if lease.get('status')!='PENDING':raise AgencyAuthorityError('lease is not consumable')
        t=_now(now);self._append('LEASE_CONSUMED',{'lease_id':lease['lease_id'],'at':t,'reason':str(reason)},at=t);return dict(self.state().leases[lease['lease_id']])
    def cancel_lease(self,lease_id:str,*,now:float|None=None,reason:str='cancelled before material execution')->dict[str,Any]:
        st=self.state();lease=st.leases.get(str(lease_id))
        if not lease:raise AgencyAuthorityError('lease not found')
        if lease.get('status')=='CANCELLED':return dict(lease)
        if lease.get('status')!='PENDING':raise AgencyAuthorityError('terminal lease cannot be cancelled')
        t=_now(now);self._append('LEASE_CANCELLED',{'lease_id':lease['lease_id'],'at':t,'reason':str(reason)},at=t);return dict(self.state().leases[lease['lease_id']])
    def pending_outbox(self,*,now:float|None=None)->list[dict[str,Any]]:
        t=_now(now);st=self.state();out=[]
        for lease in st.leases.values():
            if lease.get('status')!='PENDING':continue
            env={k:lease.get(k) for k in ('session_id','cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256','plan_id','step_id')}
            out.append({**lease,'currently_valid':self.validate_lease(lease,env,now=t)[0],'recovery_requires_explicit_host_revalidation':True})
        return sorted(out,key=lambda x:x['lease_id'])
