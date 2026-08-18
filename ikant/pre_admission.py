from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

ACCEPT = 'I ACCEPT'
TERMS_PATH = 'IKANT_ACCESS_CONTRACT.md'

class GateState(str, Enum):
    DISCOVERED='DISCOVERED'
    TERMS_ENVELOPE='TERMS_ENVELOPE'
    TERMS_PRESENTED='TERMS_PRESENTED'
    ACCEPTED='ACCEPTED'
    MATERIALIZED='MATERIALIZED'
    BREACHED='BREACHED'

class Action(str, Enum):
    FETCH_TERMS='FETCH_TERMS'
    PRESENT_TERMS='PRESENT_TERMS'
    USER_MESSAGE='USER_MESSAGE'
    CLONE_REPOSITORY='CLONE_REPOSITORY'
    DOWNLOAD_ARCHIVE='DOWNLOAD_ARCHIVE'
    LIST_TREE='LIST_TREE'
    READ_REPOSITORY_FILE='READ_REPOSITORY_FILE'
    READ_REPOSITORY_METADATA='READ_REPOSITORY_METADATA'
    READ_REPOSITORY_HISTORY='READ_REPOSITORY_HISTORY'
    READ_REPOSITORY_ISSUE_PR='READ_REPOSITORY_ISSUE_PR'
    SEARCH_REPOSITORY='SEARCH_REPOSITORY'
    GIT_FETCH='GIT_FETCH'
    GIT_LS_REMOTE='GIT_LS_REMOTE'
    MATERIALIZE_CHECKOUT='MATERIALIZE_CHECKOUT'

_REPO_ACCESS = {
    Action.CLONE_REPOSITORY, Action.DOWNLOAD_ARCHIVE, Action.LIST_TREE,
    Action.READ_REPOSITORY_FILE, Action.READ_REPOSITORY_METADATA, Action.READ_REPOSITORY_HISTORY, Action.READ_REPOSITORY_ISSUE_PR, Action.SEARCH_REPOSITORY,
    Action.GIT_FETCH, Action.GIT_LS_REMOTE, Action.MATERIALIZE_CHECKOUT,
}
REPOSITORY_ACCESS = frozenset(_REPO_ACCESS)

@dataclass(frozen=True)
class Decision:
    allowed: bool
    state: str
    code: str
    reason: str
    next_state: str
    target: str | None = None
    acceptance_valid: bool = False


def exact_human_acceptance(message: str, *, actor_type: str='human', evidence_type: str='explicit_user_message', current_session: bool=True) -> bool:
    return message == ACCEPT and actor_type == 'human' and evidence_type == 'explicit_user_message' and current_session is True


def authorize(state: str | GateState, action: str | Action, *, target: str | None=None, message: str | None=None,
              actor_type: str='human', evidence_type: str='explicit_user_message', current_session: bool=True) -> Decision:
    s = GateState(state); a = Action(action)
    if s == GateState.BREACHED:
        return Decision(False, s.value, 'DENY_BREACHED_ADMISSION', 'a completed pre-acceptance repository access cannot be cured retroactively; start a fresh admission context', s.value, target)
    if s in {GateState.ACCEPTED, GateState.MATERIALIZED}:
        if a == Action.MATERIALIZE_CHECKOUT:
            return Decision(True, s.value, 'ALLOW_POST_ACCEPT_MATERIALIZE', 'exact current-session acceptance already bound', GateState.MATERIALIZED.value, target, True)
        if a in _REPO_ACCESS:
            return Decision(True, s.value, 'ALLOW_POST_ACCEPT_REPO_ACCESS', 'repository access is allowed only after exact acceptance', s.value, target, True)
        return Decision(True, s.value, 'ALLOW_POST_ACCEPT', 'post-acceptance operation', s.value, target, True)

    if a == Action.FETCH_TERMS:
        if target != TERMS_PATH:
            return Decision(False, s.value, 'DENY_NON_TERMS_FETCH', 'before acceptance only the exact terms envelope may be fetched directly', s.value, target)
        if s != GateState.DISCOVERED:
            return Decision(False, s.value, 'DENY_TERMS_REFETCH', 'terms envelope fetch is single-purpose and not a general repository read capability', s.value, target)
        return Decision(True, s.value, 'ALLOW_TERMS_ENVELOPE_ONLY', 'sole pre-acceptance repository-read exception', GateState.TERMS_ENVELOPE.value, target)

    if a == Action.PRESENT_TERMS:
        if s == GateState.TERMS_PRESENTED:
            return Decision(True, s.value, 'ALLOW_REPRESENT_CACHED_TERMS', 'the already-fetched canonical terms may be presented again without repository access', s.value, target)
        if s != GateState.TERMS_ENVELOPE:
            return Decision(False, s.value, 'DENY_PRESENT_WITHOUT_ENVELOPE', 'terms must come from the canonical envelope', s.value, target)
        return Decision(True, s.value, 'ALLOW_PRESENT_TERMS', 'present the canonical terms without reading other repository content', GateState.TERMS_PRESENTED.value, target)

    if a == Action.USER_MESSAGE:
        if s != GateState.TERMS_PRESENTED:
            return Decision(False, s.value, 'DENY_ACCEPT_BEFORE_PRESENTATION', 'acceptance is valid only after terms presentation', s.value, target)
        valid = exact_human_acceptance(message or '', actor_type=actor_type, evidence_type=evidence_type, current_session=current_session)
        if not valid:
            return Decision(False, s.value, 'DENY_NONEXACT_ACCEPTANCE', 'only the exact current-session human message I ACCEPT changes admission state', s.value, target)
        return Decision(True, s.value, 'ALLOW_EXACT_HUMAN_ACCEPTANCE', 'exact current-session human acceptance bound', GateState.ACCEPTED.value, target, True)

    if a in _REPO_ACCESS:
        return Decision(False, s.value, 'DENY_PRE_ACCEPT_REPO_ACCESS', 'clone, tree, metadata, archive, git and repository-file reads are forbidden before acceptance', s.value, target)

    return Decision(False, s.value, 'DENY_PRE_ACCEPT_UNKNOWN', 'pre-acceptance capabilities are deny-by-default', s.value, target)


def record_completed_pre_acceptance_breach(state: str | GateState, action: str | Action, *, target: str | None=None) -> Decision:
    s=GateState(state);a=Action(action)
    if s in {GateState.ACCEPTED,GateState.MATERIALIZED}:
        return Decision(True,s.value,'NO_PRE_ACCEPT_BREACH','access occurred after acceptance',s.value,target,True)
    if a not in _REPO_ACCESS and not (a==Action.FETCH_TERMS and target!=TERMS_PATH):
        return Decision(False,s.value,'BREACH_EVENT_INVALID','only completed forbidden repository access can taint admission',s.value,target)
    return Decision(False,s.value,'PRE_ACCEPT_ACCESS_BREACH','forbidden repository access completed before acceptance; admission attempt is irrecoverably tainted',GateState.BREACHED.value,target)

def policy_manifest() -> dict[str, Any]:
    return {
        'schema': 'ikant-pre-admission-firewall/v0.6-test',
        'initial_state': GateState.DISCOVERED.value,
        'terms_envelope_path': TERMS_PATH,
        'acceptance_phrase': ACCEPT,
        'pre_acceptance_default': 'DENY',
        'terms_envelope_is_only_repository_read_exception': True,
        'repository_materialization_requires_acceptance': True,
        'completed_pre_acceptance_breach_is_nonretroactive': True,
        'forbidden_before_acceptance': sorted(a.value for a in _REPO_ACCESS),
        'acceptance_constraints': {
            'actor_type': 'human', 'evidence_type': 'explicit_user_message',
            'current_session': True, 'exact_bytes': ACCEPT,
            'embedded_quote_invalid': True, 'whitespace_variant_invalid': True,
            'case_variant_invalid': True, 'assistant_generated_invalid': True,
            'prior_session_invalid': True, 'override_instruction_invalid': True,
        },
    }
