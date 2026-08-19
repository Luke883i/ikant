from __future__ import annotations
import argparse,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.session_egress import DashboardEgressGuard,EgressState

def main():
 p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=2000);a=p.parse_args();recoveries=0
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'egress.json';g=DashboardEgressGuard(path,runtime_session_id='SES-D')
  for i in range(a.frames):
   text=f'+--+\n| > iKant durable {i} |\n+--+';r=g.seal_frame(text,kind='TURN',cycle_id=f'C{i}')
   if i%37==0:
    g=DashboardEgressGuard(path,runtime_session_id='SES-D');rr,replay=g.pending_frame();assert replay==text and rr.frame_sha256==r.frame_sha256;assert g.acknowledge_visible(rr,replay);recoveries+=1
   else:assert g.acknowledge_visible(r,text)
   assert g.state==EgressState.LOCKED
  exit_text='+--+\n| EXIT |\n+--+';g.seal_frame(exit_text,kind='EXIT',release_after_frame=True);g=DashboardEgressGuard(path,runtime_session_id='SES-D');rr,replay=g.pending_frame();assert rr.release_after_frame and replay==exit_text;assert g.acknowledge_visible(rr,replay);recoveries+=1;assert g.state==EgressState.RELEASED;assert g.verify()['ok']
  print({'ok':True,'frames':a.frames+1,'crash_recoveries':recoveries,'journal_seq':g.record.journal_seq,'state':g.state.value})
if __name__=='__main__':main()
