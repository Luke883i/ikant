from __future__ import annotations
import tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation,EXIT_COMMAND
from ikant.admission import issue_receipt,digest
from ikant.pre_admission import AdmissionGate,Action,GateState

FRAME='+--+\n| > iKant |\n+--+'
kills={}
with tempfile.TemporaryDirectory() as td:
 g=DashboardEgressGuard(Path(td)/'e.json',runtime_session_id='S');r=g.seal_frame(FRAME,kind='TURN');kills['prefix_output']=not g.acknowledge_visible(r,'x'+FRAME) and g.state==EgressState.BREACHED
with tempfile.TemporaryDirectory() as td:
 g=DashboardEgressGuard(Path(td)/'e.json',runtime_session_id='S');r=g.seal_frame(FRAME,kind='TURN');kills['suffix_output']=not g.acknowledge_visible(r,FRAME+'x')
with tempfile.TemporaryDirectory() as td:
 g=DashboardEgressGuard(Path(td)/'e.json',runtime_session_id='S');r=g.seal_frame(FRAME,kind='TURN')
 try:g.seal_frame(FRAME+'2',kind='TURN');kills['double_seal']=False
 except EgressViolation:kills['double_seal']=True
with tempfile.TemporaryDirectory() as td:
 g=DashboardEgressGuard(Path(td)/'e.json',runtime_session_id='S');kills['exit_strip']=g.classify_user_text(' EXIT IKANT')!='EXIT';kills['exit_casefold']=g.classify_user_text('exit ikant')!='EXIT';kills['exit_embedded']=g.classify_user_text('please EXIT IKANT')!='EXIT'
with tempfile.TemporaryDirectory() as td:
 g=DashboardEgressGuard(Path(td)/'e.json',runtime_session_id='S');r=g.seal_frame(FRAME,kind='EXIT',release_after_frame=True);g.acknowledge_visible(r,FRAME)
 try:g.resume(runtime_integrity_ok=False);kills['resume_without_integrity']=False
 except EgressViolation:kills['resume_without_integrity']=True
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'e.json';g=DashboardEgressGuard(p,runtime_session_id='S');r=g.seal_frame(FRAME,kind='TURN');g.acknowledge_visible(r,FRAME)
 try:DashboardEgressGuard(p,runtime_session_id='OTHER');kills['session_rebind']=False
 except EgressViolation:kills['session_rebind']=True
contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text();dg=digest(contract)
try:issue_receipt(contract,'I ACCEPT');kills['missing_presented_digest']=False
except PermissionError:kills['missing_presented_digest']=True
try:issue_receipt(contract,'I ACCEPT',presented_terms_sha256='0'*64);kills['changed_contract_digest']=False
except PermissionError:kills['changed_contract_digest']=True
g=AdmissionGate();d=g.record_completed_access(Action.READ_ORIENTATION_FILE,target='README.md',initiated_by_host=True,exposed_to_model=False);kills['unaccounted_orientation']=d.code=='PRE_ACCEPT_UNACCOUNTED_ORIENTATION_BREACH' and g.context.state==GateState.BREACHED.value
g=AdmissionGate();d=g.record_completed_access(Action.READ_ORIENTATION_FILE,target='README.md',initiated_by_host=False,exposed_to_model=False);kills['unexposed_overfetch_quarantine']=d.quarantine_required and g.context.state==GateState.DISCOVERED.value
assert all(kills.values()),kills
print({'ok':True,'mutants_killed':sorted(kills),'count':len(kills)})
