from __future__ import annotations
import argparse,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.pre_admission import AdmissionContext,Action,GateState
from ikant.chat_admission import *
DIG='e'*64
BAD=('I ACCEPT ',' I ACCEPT','i accept','I ACCEPT\n','yes','')

def scenario(i,rng):
 family=i%10;viol=[]
 base_state=rng.choice((GateState.DISCOVERED,GateState.ORIENTING,GateState.AWAITING_ACCEPTANCE,GateState.ACCEPTED,GateState.MATERIALIZED,GateState.BREACHED,GateState.DECLINED))
 c=bind_admission(AdmissionContext(state=base_state.value))
 if family==0:c=bind_admission(AdmissionContext(state=GateState.ACCEPTED.value))
 elif family==1:c=bind_admission(AdmissionContext(state=GateState.MATERIALIZED.value))
 elif family in (2,3,4,5,6,7,8,9):c=bind_admission(AdmissionContext(state=GateState.BREACHED.value))
 if family==2:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256=DIG).next_context
 elif family==3:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,rng.choice(BAD),presented_terms_sha256=DIG).next_context
 elif family==4:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256='f'*64).next_context
 elif family==5:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256=DIG,current_session=False).next_context
 elif family==6:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256=DIG,actor_type='assistant').next_context
 elif family==7:present_remediation_terms(c,rng.choice(('x','a'*63,'g'*64,'')))
 elif family==8:
  p=present_remediation_terms(c,DIG);c=accept_remediation(p.next_context,'I ACCEPT',presented_terms_sha256=DIG).next_context
 elif family==9:pass
 for action in CHAT_SEMANTIC_ACTIONS:
  d=authorize_chat_action(c,action)
  should=c.state in (ChatStudyState.CLEAN_ACCEPTED.value,ChatStudyState.REMEDIATED_ACCEPTED.value)
  if d.allowed!=should:viol.append(('semantic_gate',family,c.state,action.value,d.allowed,should,d.code))
 for action in CHAT_MATERIALIZATION_ACTIONS:
  d=authorize_chat_action(c,action)
  if d.allowed:viol.append(('materialization_escape',family,c.state,action.value,d.code))
 if c.state==ChatStudyState.REMEDIATED_ACCEPTED.value and not c.breach_preserved:viol.append(('breach_erased',family))
 return family,viol,c.state

def run(n,seed):
 rng=random.Random(seed);viol=[];families=set();states={}
 for i in range(n):
  f,v,s=scenario(i,rng);families.add(f);states[s]=states.get(s,0)+1;viol.extend((i,*x) for x in v)
 return {'ok':not viol,'scenarios':n,'families':len(families),'violations':viol[:10],'states':states}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scenarios',type=int,default=10000);ap.add_argument('--tail',type=int,default=1000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();base=run(a.scenarios,a.seed);tail=run(a.tail,a.seed+99173);out={'ok':base['ok'] and tail['ok'] and base['families']==10 and tail['families']==10,'base':base,'tail':tail};print(out);raise SystemExit(0 if out['ok'] else 2)
if __name__=='__main__':main()
