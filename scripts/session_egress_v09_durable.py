from __future__ import annotations
import argparse,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.session_egress import DashboardEgressGuard,EgressState

def main():
 p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=2000);a=p.parse_args()
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'egress.json';g=DashboardEgressGuard(path,runtime_session_id='SES-D')
  for i in range(a.frames):
   text=f'+--+\n| > iKant {i} |\n+--+';r=g.seal_frame(text,kind='TURN',cycle_id=f'C{i}');assert g.state==EgressState.FRAME_PENDING;assert g.acknowledge_visible(r,text);assert g.state==EgressState.LOCKED
   if i%97==0:g=DashboardEgressGuard(path,runtime_session_id='SES-D')
  r=g.seal_frame('+--+\n| EXIT |\n+--+',kind='EXIT',release_after_frame=True);assert g.acknowledge_visible(r,'+--+\n| EXIT |\n+--+');assert g.state==EgressState.RELEASED
  print({'ok':True,'frames':a.frames+1,'epoch':g.record.epoch,'state':g.state.value,'last_seq':g.record.frame_seq})
if __name__=='__main__':main()
