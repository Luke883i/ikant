from __future__ import annotations
import json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.session_egress import DashboardEgressGuard,EgressState,EgressViolation,activate_runtime_egress,existing_runtime_egress
from ikant.transport import build_reference_attestation,write_machine_payload
from ikant.invariants import V09_EGRESS_SCHEMA
class R:
 def __init__(self,root):self.state_dir=Path(root)/'.ikant';self.state_dir.mkdir(parents=True,exist_ok=True);self.runtime={'status':'ACTIVE','session_id':'S'};self.events=[]
 def require_active(self):pass
 def _write_runtime(self):pass
 def _event(self,*a):self.events.append(a)
def kill_recreate():
 with tempfile.TemporaryDirectory() as td:
  r=R(td);g=activate_runtime_egress(r,initialization=True);g.path.unlink()
  try:activate_runtime_egress(r,initialization=True)
  except EgressViolation:return True
  return False
def kill_runtime_only_resume():
 with tempfile.TemporaryDirectory() as td:
  r=R(td);g=activate_runtime_egress(r,initialization=True);rc=g.seal_frame('d',kind='TURN');g.acknowledge_visible(rc,'dx')
  try:g.resume(runtime_integrity_ok=True)
  except EgressViolation:return True
  return False
def kill_machine_sink(value):
 try:write_machine_payload(value,{'x':1})
 except PermissionError:return True
 return False
def kill_v09_pending_upgrade():
 with tempfile.TemporaryDirectory() as td:
  r=R(td);p=r.state_dir/'egress.json';p.write_text(json.dumps({'schema':V09_EGRESS_SCHEMA,'runtime_session_id':'S','state':'FRAME_PENDING','epoch':1,'frame_seq':1,'last_frame_sha256':'a'*64,'last_cycle_id':'C','last_kind':'TURN','updated_at':'x','breach_reason':None}));return existing_runtime_egress(r).state==EgressState.BREACHED
def source_has(path,needle):return needle in (ROOT/path).read_text(encoding='utf-8')
def source_lacks(path,needle):return needle not in (ROOT/path).read_text(encoding='utf-8')
checks={'recreate_missing_egress':kill_recreate(),'breach_resume_runtime_only':kill_runtime_only_resume(),'machine_stdout':kill_machine_sink('stdout'),'machine_stderr':kill_machine_sink('stderr'),'machine_dash':kill_machine_sink('-'),'active_accept_bypass':source_has('ikant/app_cli.py',"active and command in {'accept','probe','initialize'}"),'ambient_machine_env':source_lacks('ikant/app_cli.py','IKANT_MACHINE_CHANNEL'),'versioned_cli_entrypoint':source_lacks('ikant/__main__.py','v05_cli'),'versioned_session_host_import':source_lacks('ikant/session_host.py','dashboard_v05') and source_lacks('ikant/session_host.py','host_v05'),'v09_pending_promoted':kill_v09_pending_upgrade(),'surface_b_optional':source_has('ikant/runtime_host.py','export_docx=True'),'pending_frame_replaceable':source_has('ikant/session_egress.py','pending frame artifact digest mismatch'),'ack_before_delivery':source_has('ikant/app_cli.py','deliver_human(text)') and source_has('ikant/app_cli.py','acknowledge_prepared_frame'),'digest_unbound_acceptance':source_has('ikant/admission.py','presented/checkout contract digest mismatch'),'registry_bypass':source_has('IKANT_ACCESS_CONTRACT.md','ikant.invariants')}
survivors=[k for k,v in checks.items() if not v];out={'schema':'ikant-reticular-v11-fault-mutation/v0.11-test','mutants':len(checks),'killed':len(checks)-len(survivors),'survivors':survivors,'checks':checks,'status':'PASS' if not survivors else 'FAIL'};print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if not survivors else 1)
