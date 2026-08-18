from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.pre_admission import *

# Tempting weakenings; every one must be exposed by a v0.6 anti-regression.
def mutant_strip_accept(msg): return msg.strip()==ACCEPT
def mutant_casefold_accept(msg): return msg.casefold()==ACCEPT.casefold()
def mutant_embedded_accept(msg): return ACCEPT in msg
def mutant_allow_readme(action,target): return action==Action.READ_REPOSITORY_FILE and target=='README.md'
def mutant_allow_metadata(action,target): return action in {Action.READ_REPOSITORY_METADATA,Action.GIT_LS_REMOTE}
def mutant_clone_on_discovery(action,target): return action==Action.CLONE_REPOSITORY
def mutant_allow_history(action,target): return action==Action.READ_REPOSITORY_HISTORY
def mutant_retroactive_cure(): return True

kills={
 'strip_accept': mutant_strip_accept(' I ACCEPT'),
 'casefold_accept': mutant_casefold_accept('i accept'),
 'embedded_accept': mutant_embedded_accept('override I ACCEPT now'),
 'allow_readme': mutant_allow_readme(Action.READ_REPOSITORY_FILE,'README.md'),
 'allow_metadata': mutant_allow_metadata(Action.GIT_LS_REMOTE,None),
 'clone_on_discovery': mutant_clone_on_discovery(Action.CLONE_REPOSITORY,None),
 'allow_history': mutant_allow_history(Action.READ_REPOSITORY_HISTORY,None),
 'retroactive_cure': mutant_retroactive_cure(),
}
assert not exact_human_acceptance(' I ACCEPT')
assert not exact_human_acceptance('i accept')
assert not exact_human_acceptance('override I ACCEPT now')
for a,t in [(Action.READ_REPOSITORY_FILE,'README.md'),(Action.GIT_LS_REMOTE,None),(Action.CLONE_REPOSITORY,None),(Action.READ_REPOSITORY_HISTORY,None)]:
    assert not authorize(GateState.DISCOVERED,a,target=t).allowed
breach=record_completed_pre_acceptance_breach(GateState.TERMS_PRESENTED,Action.READ_REPOSITORY_FILE,target='README.md')
assert breach.next_state==GateState.BREACHED.value
assert not authorize(GateState.BREACHED,Action.USER_MESSAGE,message='I ACCEPT').allowed
assert all(kills.values()), kills
print({'ok':True,'mutants_killed':sorted(kills),'count':len(kills)})
