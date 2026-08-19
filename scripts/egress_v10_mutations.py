from __future__ import annotations
import json,tempfile,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.session_egress import *
from ikant.invariants import V09_EGRESS_SCHEMA
FRAME='+--+\n| > iKant |\n+--+';k={}
def guard(td):
 p=Path(td)/'egress.json';return DashboardEgressGuard(p,runtime_session_id='S') if p.exists() else DashboardEgressGuard.create(p,runtime_session_id='S')
with tempfile.TemporaryDirectory() as td:
 g=guard(td);r=g.seal_frame(FRAME,kind='TURN');k['two_phase_pending']=g.state==EgressState.FRAME_PENDING
 try:g.seal_frame(FRAME,kind='TURN');k['double_seal']=False
 except EgressViolation:k['double_seal']=True
with tempfile.TemporaryDirectory() as td:g=guard(td);r=g.seal_frame(FRAME,kind='TURN');k['prefix']=not g.acknowledge_visible(r,'x'+FRAME)
with tempfile.TemporaryDirectory() as td:g=guard(td);r=g.seal_frame(FRAME,kind='TURN');k['release_flag']=not g.acknowledge_visible(replace(r,release_after_frame=True),FRAME)
with tempfile.TemporaryDirectory() as td:
 g=guard(td);g.seal_frame(FRAME,kind='TURN');Path(g.record.pending_frame_path).write_text(FRAME+'x')
 try:g.pending_frame();k['pending_tamper']=False
 except EgressViolation:k['pending_tamper']=g.state==EgressState.BREACHED
with tempfile.TemporaryDirectory() as td:
 g=guard(td);g.seal_frame(FRAME,kind='TURN');Path(g.record.pending_frame_path).unlink()
 try:g.pending_frame();k['pending_missing']=False
 except EgressViolation:k['pending_missing']=g.state==EgressState.BREACHED
with tempfile.TemporaryDirectory() as td:
 g=guard(td);r=g.seal_frame(FRAME,kind='TURN');g.acknowledge_visible(r,FRAME);rows=g.journal_path.read_text().splitlines();d=json.loads(rows[-1]);d['event']='MUTANT';rows[-1]=json.dumps(d);g.journal_path.write_text('\n'.join(rows)+'\n')
 try:guard(td);k['journal_tamper']=False
 except EgressViolation:k['journal_tamper']=True
with tempfile.TemporaryDirectory() as td:
 g=guard(td);d=json.loads(g.path.read_text());d['journal_seq']+=1;g.path.write_text(json.dumps(d))
 try:guard(td);k['snapshot_journal_drift']=False
 except EgressViolation:k['snapshot_journal_drift']=True
with tempfile.TemporaryDirectory() as td:
 g=guard(td)
 try:g.seal_frame('x'*(MAX_FRAME_BYTES+1),kind='TURN');k['oversize']=False
 except EgressViolation:k['oversize']=True
with tempfile.TemporaryDirectory() as td:
 g=guard(td)
 try:g.seal_frame(FRAME+'\x1b',kind='TURN');k['ansi']=False
 except EgressViolation:k['ansi']=True
with tempfile.TemporaryDirectory() as td:
 g=guard(td)
 try:g.seal_frame(FRAME+'\u202e',kind='TURN');k['bidi']=False
 except EgressViolation:k['bidi']=True
with tempfile.TemporaryDirectory() as td:p=Path(td)/'egress.json';p.write_text(json.dumps({'schema':V09_EGRESS_SCHEMA,'runtime_session_id':'S','state':'FRAME_PENDING','epoch':1,'frame_seq':1,'last_frame_sha256':'a'*64,'last_cycle_id':'C','last_kind':'TURN','updated_at':'x','breach_reason':None}));g=guard(td);k['legacy_pending']=g.state==EgressState.BREACHED
with tempfile.TemporaryDirectory() as td:
 g=guard(td);r=g.seal_frame(FRAME,kind='EXIT',release_after_frame=True);g.acknowledge_visible(r,FRAME)
 try:g.resume(runtime_integrity_ok=False);k['resume_integrity']=False
 except EgressViolation:k['resume_integrity']=True
with tempfile.TemporaryDirectory() as td:g=guard(td);k['exit_exact']=g.classify_user_text(' EXIT IKANT')=='INTENT' and g.classify_user_text('exit ikant')=='INTENT'
assert all(k.values()),k;print({'ok':True,'mutants_killed':sorted(k),'count':len(k)})
