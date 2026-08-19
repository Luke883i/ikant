from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any
import hashlib, secrets, threading
from datetime import datetime, timezone

ACCEPT = 'I ACCEPT'
TERMS_PATH = 'IKANT_ACCESS_CONTRACT.md'
ORIENTATION_PATHS = ('README.md','IKANT_ACCESS_CONTRACT.md','BOOTSTRAP.json','ADMISSION.json','AGENTS.md')
ORIENTATION_METADATA_FIELDS = ('repository_full_name','visibility','default_branch','description','license','topics','archived')
ORIENTATION_MAX_FILE_READS = len(ORIENTATION_PATHS)
ORIENTATION_MAX_BYTES = 256 * 1024
ORIENTATION_MAX_METADATA_READS = 1
CACHED_USE_PURPOSES = frozenset({'TERMS_EXPLANATION','BOOTSTRAP_EXPLANATION','ACCESS_DENIAL'})

class GateState(str, Enum):
    DISCOVERED='DISCOVERED';ORIENTING='ORIENTING';AWAITING_ACCEPTANCE='AWAITING_ACCEPTANCE';ACCEPTED='ACCEPTED';MATERIALIZED='MATERIALIZED';DECLINED='DECLINED';BREACHED='BREACHED'
class Action(str, Enum):
    READ_ORIENTATION_METADATA='READ_ORIENTATION_METADATA';READ_ORIENTATION_FILE='READ_ORIENTATION_FILE';PRESENT_TERMS='PRESENT_TERMS';USE_CACHED_ORIENTATION='USE_CACHED_ORIENTATION';USER_MESSAGE='USER_MESSAGE';USER_DECLINE='USER_DECLINE';CLONE_REPOSITORY='CLONE_REPOSITORY';DOWNLOAD_ARCHIVE='DOWNLOAD_ARCHIVE';LIST_TREE='LIST_TREE';READ_REPOSITORY_FILE='READ_REPOSITORY_FILE';READ_REPOSITORY_METADATA='READ_REPOSITORY_METADATA';READ_REPOSITORY_HISTORY='READ_REPOSITORY_HISTORY';READ_REPOSITORY_ISSUE_PR='READ_REPOSITORY_ISSUE_PR';SEARCH_REPOSITORY='SEARCH_REPOSITORY';GIT_FETCH='GIT_FETCH';GIT_LS_REMOTE='GIT_LS_REMOTE';MATERIALIZE_CHECKOUT='MATERIALIZE_CHECKOUT'
_REPO_ACCESS={Action.CLONE_REPOSITORY,Action.DOWNLOAD_ARCHIVE,Action.LIST_TREE,Action.READ_REPOSITORY_FILE,Action.READ_REPOSITORY_METADATA,Action.READ_REPOSITORY_HISTORY,Action.READ_REPOSITORY_ISSUE_PR,Action.SEARCH_REPOSITORY,Action.GIT_FETCH,Action.GIT_LS_REMOTE,Action.MATERIALIZE_CHECKOUT}
REPOSITORY_ACCESS=frozenset(_REPO_ACCESS)

@dataclass(frozen=True)
class AdmissionContext:
    state:str=GateState.DISCOVERED.value;orientation_files:tuple[str,...]=();orientation_bytes:int=0;metadata_reads:int=0;terms_sha256:str|None=None;presented_terms_sha256:str|None=None
    @property
    def gate_state(self)->GateState:return GateState(self.state)
@dataclass(frozen=True)
class Decision:
    allowed:bool;state:str;code:str;reason:str;next_state:str;target:str|None=None;acceptance_valid:bool=False;next_context:AdmissionContext|None=None;quarantine_required:bool=False

def new_context()->AdmissionContext:return AdmissionContext()
def _ctx(value:AdmissionContext|str|GateState)->AdmissionContext:return value if isinstance(value,AdmissionContext) else AdmissionContext(state=GateState(value).value)
def _decision(ctx,allowed,code,reason,*,target=None,next_ctx=None,acceptance_valid=False,quarantine_required=False):
    nxt=next_ctx or ctx;return Decision(allowed,ctx.state,code,reason,nxt.state,target,acceptance_valid,nxt,quarantine_required)
def exact_human_acceptance(message:str,*,actor_type='human',evidence_type='explicit_user_message',current_session=True)->bool:return message==ACCEPT and actor_type=='human' and evidence_type=='explicit_user_message' and current_session is True

def authorize(context,action,*,target=None,message=None,actor_type='human',evidence_type='explicit_user_message',current_session=True,byte_count=0,content_sha256=None,metadata_fields=None,purpose=None):
    ctx=_ctx(context);s=ctx.gate_state;a=Action(action)
    if s==GateState.BREACHED:return _decision(ctx,False,'DENY_BREACHED_ADMISSION','completed forbidden pre-acceptance acquisition cannot be cured retroactively; start a fresh admission context',target=target)
    if s in {GateState.ACCEPTED,GateState.MATERIALIZED}:
        if a==Action.MATERIALIZE_CHECKOUT:
            nxt=replace(ctx,state=GateState.MATERIALIZED.value);return _decision(ctx,True,'ALLOW_POST_ACCEPT_MATERIALIZE','exact current-session acceptance already bound',target=target,next_ctx=nxt,acceptance_valid=True)
        if a in _REPO_ACCESS:return _decision(ctx,True,'ALLOW_POST_ACCEPT_REPO_ACCESS','repository capability is open after exact acceptance',target=target,acceptance_valid=True)
        if a==Action.USE_CACHED_ORIENTATION:return _decision(ctx,True,'ALLOW_POST_ACCEPT_CACHE_USE','orientation cache is no longer capability-sensitive after acceptance',target=target,acceptance_valid=True)
        return _decision(ctx,True,'ALLOW_POST_ACCEPT','post-acceptance operation',target=target,acceptance_valid=True)
    if s==GateState.DECLINED:
        if a==Action.PRESENT_TERMS and ctx.presented_terms_sha256:
            nxt=replace(ctx,state=GateState.AWAITING_ACCEPTANCE.value);return _decision(ctx,True,'ALLOW_REOPEN_FROM_CACHED_TERMS','cached terms may be re-presented to reopen the same admission context without repository access',next_ctx=nxt)
        if a==Action.USE_CACHED_ORIENTATION and purpose in CACHED_USE_PURPOSES:return _decision(ctx,True,'ALLOW_DECLINED_CACHE_EXPLANATION','cached orientation may only explain terms/bootstrap or render denial',target=target)
        return _decision(ctx,False,'DENY_DECLINED','repository capability remains closed after explicit decline; re-present cached terms before a new acceptance attempt',target=target)
    if a==Action.READ_ORIENTATION_METADATA:
        if s not in {GateState.DISCOVERED,GateState.ORIENTING}:return _decision(ctx,False,'DENY_ORIENTATION_FROZEN','orientation acquisition closes immediately after terms presentation',target=target)
        fields=tuple(metadata_fields or ())
        if ctx.metadata_reads>=ORIENTATION_MAX_METADATA_READS:return _decision(ctx,False,'DENY_METADATA_REPEAT','orientation metadata is a one-shot bounded projection',target=target)
        if fields and not set(fields).issubset(ORIENTATION_METADATA_FIELDS):return _decision(ctx,False,'DENY_METADATA_SCOPE','metadata projection requested fields outside the orientation capsule',target=target)
        nxt=replace(ctx,state=GateState.ORIENTING.value,metadata_reads=ctx.metadata_reads+1);return _decision(ctx,True,'ALLOW_ORIENTATION_METADATA','bounded repository identity metadata is allowed only during orientation',target=target,next_ctx=nxt)
    if a==Action.READ_ORIENTATION_FILE:
        if s not in {GateState.DISCOVERED,GateState.ORIENTING}:return _decision(ctx,False,'DENY_ORIENTATION_FROZEN','orientation acquisition closes immediately after terms presentation',target=target)
        if target not in ORIENTATION_PATHS:return _decision(ctx,False,'DENY_OUTSIDE_ORIENTATION_CAPSULE','pre-acceptance file acquisition is restricted to the explicit orientation capsule',target=target)
        if target in ctx.orientation_files:return _decision(ctx,False,'DENY_ORIENTATION_REFETCH','orientation files are single-fetch within an admission context',target=target)
        if byte_count<0:return _decision(ctx,False,'DENY_INVALID_SIZE','orientation byte count must be non-negative',target=target)
        if len(ctx.orientation_files)+1>ORIENTATION_MAX_FILE_READS or ctx.orientation_bytes+byte_count>ORIENTATION_MAX_BYTES:return _decision(ctx,False,'DENY_ORIENTATION_BUDGET','orientation capsule read/count budget exceeded',target=target)
        if target==TERMS_PATH and not content_sha256:return _decision(ctx,False,'DENY_TERMS_WITHOUT_DIGEST','canonical terms must be digest-bound before presentation',target=target)
        terms_digest=content_sha256 if target==TERMS_PATH else ctx.terms_sha256;nxt=replace(ctx,state=GateState.ORIENTING.value,orientation_files=ctx.orientation_files+(target,),orientation_bytes=ctx.orientation_bytes+byte_count,terms_sha256=terms_digest);return _decision(ctx,True,'ALLOW_ORIENTATION_FILE','bounded preliminary document acquisition is allowed only before terms presentation',target=target,next_ctx=nxt)
    if a==Action.PRESENT_TERMS:
        if s not in {GateState.DISCOVERED,GateState.ORIENTING}:
            if s==GateState.AWAITING_ACCEPTANCE and ctx.presented_terms_sha256:return _decision(ctx,True,'ALLOW_REPRESENT_CACHED_TERMS','already-fetched terms may be re-presented from cache without repository access')
            return _decision(ctx,False,'DENY_PRESENT_TERMS_STATE','terms presentation is only valid from orientation or cached waiting state')
        if TERMS_PATH not in ctx.orientation_files or not ctx.terms_sha256:return _decision(ctx,False,'DENY_PRESENT_WITHOUT_TERMS','canonical terms must be fetched and digest-bound before presentation')
        nxt=replace(ctx,state=GateState.AWAITING_ACCEPTANCE.value,presented_terms_sha256=ctx.terms_sha256);return _decision(ctx,True,'ALLOW_PRESENT_TERMS_AND_FREEZE','terms presented; orientation acquisition is now frozen pending exact acceptance',next_ctx=nxt)
    if a==Action.USE_CACHED_ORIENTATION:
        if s!=GateState.AWAITING_ACCEPTANCE:return _decision(ctx,False,'DENY_CACHE_USE_STATE','pre-acceptance cached orientation use is only defined after terms presentation',target=target)
        if purpose not in CACHED_USE_PURPOSES:return _decision(ctx,False,'DENY_CACHE_PURPOSE','cached orientation is purpose-limited to terms/bootstrap explanation or access denial',target=target)
        return _decision(ctx,True,'ALLOW_PURPOSE_LIMITED_CACHE_USE','cached orientation may support informed consent without reopening repository capability',target=target)
    if a==Action.USER_MESSAGE:
        if s!=GateState.AWAITING_ACCEPTANCE:return _decision(ctx,False,'DENY_ACCEPT_BEFORE_PRESENTATION','acceptance is valid only after canonical terms presentation',target=target)
        valid=exact_human_acceptance(message or '',actor_type=actor_type,evidence_type=evidence_type,current_session=current_session)
        if not valid:return _decision(ctx,False,'DENY_NONEXACT_ACCEPTANCE','only the exact current-session human message I ACCEPT changes admission state',target=target)
        if not ctx.presented_terms_sha256 or ctx.presented_terms_sha256!=ctx.terms_sha256:return _decision(ctx,False,'DENY_TERMS_BINDING_MISMATCH','acceptance must bind the exact digest that was presented',target=target)
        nxt=replace(ctx,state=GateState.ACCEPTED.value);return _decision(ctx,True,'ALLOW_EXACT_HUMAN_ACCEPTANCE','exact current-session human acceptance bound to presented terms digest',target=target,next_ctx=nxt,acceptance_valid=True)
    if a==Action.USER_DECLINE:
        if s!=GateState.AWAITING_ACCEPTANCE:return _decision(ctx,False,'DENY_DECLINE_STATE','decline is only meaningful after terms presentation',target=target)
        nxt=replace(ctx,state=GateState.DECLINED.value);return _decision(ctx,True,'ALLOW_EXPLICIT_DECLINE','user declined; repository capability remains closed and denial may be persisted',target=target,next_ctx=nxt)
    if a in _REPO_ACCESS:
        code='DENY_TERMS_NOT_ACCEPTED' if s==GateState.AWAITING_ACCEPTANCE else 'DENY_OUTSIDE_ORIENTATION_CAPSULE';reason='repository acquisition/materialization is frozen until exact acceptance' if s==GateState.AWAITING_ACCEPTANCE else 'before terms presentation only bounded orientation capability is available';capability=a.value if target is None else f'{a.value}:{target}';return _decision(ctx,False,code,reason,target=capability)
    return _decision(ctx,False,'DENY_PRE_ACCEPT_UNKNOWN','pre-acceptance capabilities are deny-by-default',target=target)

def record_completed_pre_acceptance_access(context,action,*,target=None,initiated_by_host=True,exposed_to_model=True):
    ctx=_ctx(context);s=ctx.gate_state;a=Action(action)
    if s in {GateState.ACCEPTED,GateState.MATERIALIZED}:return _decision(ctx,True,'NO_PRE_ACCEPT_BREACH','access occurred after acceptance',target=target,acceptance_valid=True)
    if not initiated_by_host and not exposed_to_model:return _decision(ctx,False,'QUARANTINE_INCIDENTAL_OVERFETCH','provider overfetch was not requested and must be discarded before model/persistence use',target=target,quarantine_required=True)
    if a in {Action.READ_ORIENTATION_FILE,Action.READ_ORIENTATION_METADATA}:
        nxt=replace(ctx,state=GateState.BREACHED.value);return _decision(ctx,False,'PRE_ACCEPT_UNACCOUNTED_ORIENTATION_BREACH','completed orientation acquisition bypassed actual-payload accounting',target=target,next_ctx=nxt)
    if a not in _REPO_ACCESS:return _decision(ctx,False,'BREACH_EVENT_INVALID','only completed repository acquisition can taint admission',target=target)
    nxt=replace(ctx,state=GateState.BREACHED.value);return _decision(ctx,False,'PRE_ACCEPT_ACCESS_BREACH','forbidden repository acquisition completed before acceptance and was host-initiated or model-exposed',target=target,next_ctx=nxt)

def build_access_denial_receipt(context,decision,*,repository='Luke883i/ikant',attempt_id=None,at=None)->dict[str,Any]:
    ctx=_ctx(context)
    if decision.allowed:raise ValueError('denial receipt requires a denied decision')
    aid=attempt_id or 'ATT-'+secrets.token_hex(8);stamp=at or datetime.now(timezone.utc).isoformat();receipt={'schema':'ikant-access-denial/v0.8','repository':repository,'attempt_id':aid,'at':stamp,'state':ctx.state,'code':decision.code,'reason':decision.reason,'requested_capability':decision.target or '','terms_sha256':ctx.presented_terms_sha256 or ctx.terms_sha256,'repository_access_performed':False,'persistent_message':f'ACCESS DENIED [{decision.code}]: terms are not accepted; repository acquisition/materialization remains closed.'};receipt['sha256']=hashlib.sha256(repr(sorted(receipt.items())).encode()).hexdigest();return receipt

class AdmissionGate:
    def __init__(self,context=None):self.context=context or new_context();self._lock=threading.RLock()
    def act(self,action,**kwargs):
        with self._lock:d=authorize(self.context,action,**kwargs);self.context=d.next_context or self.context;return d
    def record_completed_access(self,action,**kwargs):
        with self._lock:d=record_completed_pre_acceptance_access(self.context,action,**kwargs);self.context=d.next_context or self.context;return d

def policy_manifest()->dict[str,Any]:
    return {'schema':'ikant-pre-admission-firewall/v0.9-test','initial_state':GateState.DISCOVERED.value,'orientation_state':GateState.ORIENTING.value,'awaiting_acceptance_state':GateState.AWAITING_ACCEPTANCE.value,'acceptance_phrase':ACCEPT,'pre_acceptance_default':'DENY','orientation_capsule':{'paths':list(ORIENTATION_PATHS),'metadata_fields':list(ORIENTATION_METADATA_FIELDS),'max_file_reads':ORIENTATION_MAX_FILE_READS,'max_total_bytes':ORIENTATION_MAX_BYTES,'max_metadata_reads':ORIENTATION_MAX_METADATA_READS,'single_fetch_per_path':True,'tree_search_history_source_allowed':False},'freeze_after_terms_presentation':True,'completed_access_accounting_required':True,'presented_terms_digest_handoff_required':True,'cached_orientation_use_purposes':sorted(CACHED_USE_PURPOSES),'repository_materialization_requires_acceptance':True,'completed_forbidden_access_is_nonretroactive':True,'incidental_unexposed_overfetch_is_quarantined':True,'forbidden_before_acceptance':sorted(a.value for a in _REPO_ACCESS),'acceptance_constraints':{'actor_type':'human','evidence_type':'explicit_user_message','current_session':True,'exact_bytes':ACCEPT,'embedded_quote_invalid':True,'whitespace_variant_invalid':True,'case_variant_invalid':True,'assistant_generated_invalid':True,'prior_session_invalid':True,'override_instruction_invalid':True,'presented_terms_digest_binding_required':True,'presented_terms_digest_handoff_required':True},'denial_receipt_schema':'ikant-access-denial/v0.8'}
