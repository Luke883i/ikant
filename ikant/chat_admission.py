from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from .pre_admission import ACCEPT, Action, AdmissionContext, GateState, exact_human_acceptance

CHAT_SEMANTIC_ACTIONS=frozenset({
 Action.LIST_TREE,Action.READ_REPOSITORY_FILE,Action.READ_REPOSITORY_METADATA,
 Action.READ_REPOSITORY_HISTORY,Action.READ_REPOSITORY_ISSUE_PR,Action.SEARCH_REPOSITORY,
})
CHAT_MATERIALIZATION_ACTIONS=frozenset({
 Action.CLONE_REPOSITORY,Action.DOWNLOAD_ARCHIVE,Action.GIT_FETCH,
 Action.GIT_LS_REMOTE,Action.MATERIALIZE_CHECKOUT,
})

class ChatStudyState(str,Enum):
 CLOSED='CLOSED';CLEAN_ACCEPTED='CLEAN_ACCEPTED';BREACHED='BREACHED';REMEDIATION_TERMS_PRESENTED='REMEDIATION_TERMS_PRESENTED';REMEDIATED_ACCEPTED='REMEDIATED_ACCEPTED'

@dataclass(frozen=True)
class ChatStudyContext:
 state:str=ChatStudyState.CLOSED.value
 base_gate_state:str=GateState.DISCOVERED.value
 breach_preserved:bool=False
 remediation_terms_sha256:str|None=None

@dataclass(frozen=True)
class ChatStudyDecision:
 allowed:bool;code:str;reason:str;next_context:ChatStudyContext


def bind_admission(base:AdmissionContext)->ChatStudyContext:
 state=base.gate_state
 if state in {GateState.ACCEPTED,GateState.MATERIALIZED}:
  return ChatStudyContext(ChatStudyState.CLEAN_ACCEPTED.value,state.value,False,None)
 if state is GateState.BREACHED:
  return ChatStudyContext(ChatStudyState.BREACHED.value,state.value,True,None)
 return ChatStudyContext(ChatStudyState.CLOSED.value,state.value,False,None)


def present_remediation_terms(ctx:ChatStudyContext,terms_sha256:str)->ChatStudyDecision:
 if ctx.state not in {ChatStudyState.BREACHED.value,ChatStudyState.REMEDIATION_TERMS_PRESENTED.value}:
  return ChatStudyDecision(False,'DENY_REMEDIATION_STATE','remediation is only defined for a preserved pre-acceptance breach',ctx)
 if not isinstance(terms_sha256,str) or len(terms_sha256)!=64 or any(c not in '0123456789abcdef' for c in terms_sha256):
  return ChatStudyDecision(False,'DENY_REMEDIATION_TERMS_DIGEST','current terms require a lowercase SHA-256 digest',ctx)
 nxt=replace(ctx,state=ChatStudyState.REMEDIATION_TERMS_PRESENTED.value,remediation_terms_sha256=terms_sha256,breach_preserved=True)
 return ChatStudyDecision(True,'ALLOW_PRESENT_REMEDIATION_TERMS','current terms may be re-presented to request prospective chat-study authorization; the prior breach remains preserved',nxt)


def accept_remediation(ctx:ChatStudyContext,message:str,*,presented_terms_sha256:str,actor_type='human',evidence_type='explicit_user_message',current_session=True)->ChatStudyDecision:
 if ctx.state!=ChatStudyState.REMEDIATION_TERMS_PRESENTED.value:
  return ChatStudyDecision(False,'DENY_REMEDIATION_NOT_PRESENTED','current remediation terms must be presented after the breach',ctx)
 if presented_terms_sha256!=ctx.remediation_terms_sha256:
  return ChatStudyDecision(False,'DENY_REMEDIATION_DIGEST_MISMATCH','acceptance must bind the exact remediation terms digest that was presented',ctx)
 if not exact_human_acceptance(message,actor_type=actor_type,evidence_type=evidence_type,current_session=current_session):
  return ChatStudyDecision(False,'DENY_NONEXACT_REMEDIATION_ACCEPTANCE','only exact current-session human I ACCEPT authorizes prospective chat study',ctx)
 nxt=replace(ctx,state=ChatStudyState.REMEDIATED_ACCEPTED.value,breach_preserved=True)
 return ChatStudyDecision(True,'ALLOW_REMEDIATED_HUMAN_ACCEPTANCE','prior access remains breached; future same-session semantic study is owner-authorized prospectively only',nxt)


def authorize_chat_action(ctx:ChatStudyContext,action:Action|str)->ChatStudyDecision:
 action=Action(action)
 if ctx.state==ChatStudyState.CLEAN_ACCEPTED.value:
  if action in CHAT_SEMANTIC_ACTIONS:
   return ChatStudyDecision(True,'ALLOW_CLEAN_CHAT_STUDY','clean digest-bound acceptance authorizes same-session semantic study without requiring local ACTIVE',ctx)
  return ChatStudyDecision(False,'DENY_CHAT_SCOPE','chat-study authorization is semantic read/list/search authority only',ctx)
 if ctx.state==ChatStudyState.REMEDIATED_ACCEPTED.value:
  if action in CHAT_SEMANTIC_ACTIONS:
   return ChatStudyDecision(True,'ALLOW_REMEDIATED_CHAT_STUDY','prospective same-session semantic study is allowed while the historical breach remains preserved',ctx)
  if action in CHAT_MATERIALIZATION_ACTIONS:
   return ChatStudyDecision(False,'DENY_REMEDIATED_RUNTIME_MATERIALIZATION','remediated chat study cannot clone/fetch/materialize or establish conforming iKant; use a fresh clean admission context',ctx)
  return ChatStudyDecision(False,'DENY_REMEDIATED_CHAT_SCOPE','remediated authorization is limited to prospective semantic study',ctx)
 return ChatStudyDecision(False,'DENY_CHAT_STUDY_NOT_ACCEPTED','chat study requires clean acceptance or explicit breach remediation',ctx)


def remediation_manifest()->dict:
 return {'schema':'ikant-chat-study-remediation/v0.12-test','clean_chat_study_requires_local_active':False,'prior_breach_preserved':True,'terms_re_presentation_required':True,'exact_current_session_acceptance_required':True,'prospective_only':True,'semantic_actions':sorted(a.value for a in CHAT_SEMANTIC_ACTIONS),'materialization_allowed_after_remediation':False,'official_ikant_allowed_after_remediation':False}
