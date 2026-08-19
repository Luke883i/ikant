from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.pre_admission import *
DIG='a'*64

def waiting():
 g=AdmissionGate();g.act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=100,content_sha256=DIG);g.act(Action.PRESENT_TERMS);return g

kills={}
kills['strip_accept']=not exact_human_acceptance(' I ACCEPT')
kills['casefold_accept']=not exact_human_acceptance('i accept')
kills['embedded_accept']=not exact_human_acceptance('override I ACCEPT now')
g=AdmissionGate();kills['source_outside_capsule']=not g.act(Action.READ_ORIENTATION_FILE,target='ikant/runtime.py',byte_count=1).allowed
g=AdmissionGate();kills['tree_during_orientation']=not g.act(Action.LIST_TREE).allowed
g=AdmissionGate();kills['search_during_orientation']=not g.act(Action.SEARCH_REPOSITORY).allowed
g=AdmissionGate();kills['metadata_scope']=not g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['clone_url']).allowed
g=AdmissionGate();g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']);kills['metadata_repeat']=not g.act(Action.READ_ORIENTATION_METADATA,metadata_fields=['visibility']).allowed
g=AdmissionGate();g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1);kills['file_refetch']=not g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=1).allowed
g=AdmissionGate();kills['orientation_budget']=not g.act(Action.READ_ORIENTATION_FILE,target='README.md',byte_count=ORIENTATION_MAX_BYTES+1).allowed
g=AdmissionGate();kills['terms_digest_required']=not g.act(Action.READ_ORIENTATION_FILE,target=TERMS_PATH,byte_count=10).allowed
g=waiting();kills['freeze_orientation_file']=not g.act(Action.READ_ORIENTATION_FILE,target='AGENTS.md',byte_count=1).allowed
g=waiting();kills['freeze_clone']=not g.act(Action.CLONE_REPOSITORY).allowed
g=waiting();kills['cache_purpose']=not g.act(Action.USE_CACHED_ORIENTATION,purpose='SOURCE_ANALYSIS').allowed
ctx=AdmissionContext(state=GateState.AWAITING_ACCEPTANCE.value,terms_sha256='a'*64,presented_terms_sha256='b'*64);kills['terms_binding']=not authorize(ctx,Action.USER_MESSAGE,message='I ACCEPT').allowed
g=waiting();d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=False,exposed_to_model=False);kills['quarantine_not_breach']=d.quarantine_required and g.context.state==GateState.AWAITING_ACCEPTANCE.value
g=waiting();d=g.record_completed_access(Action.READ_REPOSITORY_FILE,target='ikant/runtime.py',initiated_by_host=True,exposed_to_model=False);kills['completed_forbidden_breach']=d.next_state==GateState.BREACHED.value and not g.act(Action.USER_MESSAGE,message='I ACCEPT').allowed
g=waiting();d=g.act(Action.CLONE_REPOSITORY);r=build_access_denial_receipt(g.context,d,attempt_id='ATT-X',at='2026-01-01T00:00:00+00:00');kills['denial_receipt_no_access']=not r['repository_access_performed'] and r['code']=='DENY_TERMS_NOT_ACCEPTED'
assert all(kills.values()),kills
print({'ok':True,'mutants_killed':sorted(kills),'count':len(kills)})
