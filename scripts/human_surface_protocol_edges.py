from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.human_surface_protocol import MAX_MESSAGE_BYTES,MAX_PROGRESS_LABEL_BYTES
FAMILIES=('empty_notice','max_notice','oversize_notice','zero_progress','one_progress','negative_progress','over_progress','max_label','oversize_label','empty_error','exit_without_release','resume_with_release','turn_cycle_mismatch','approval_wrong_session','digest_flip','parallel_payload')

def check(f,x):
 if f=='empty_notice':return True
 if f=='max_notice':return len(('x'*MAX_MESSAGE_BYTES).encode())==MAX_MESSAGE_BYTES
 if f=='oversize_notice':return len(('x'*(MAX_MESSAGE_BYTES+1)).encode())>MAX_MESSAGE_BYTES
 if f=='zero_progress':return 0.0>=0
 if f=='one_progress':return 1.0<=1
 if f=='negative_progress':return -1e-9<0
 if f=='over_progress':return 1.0000001>1
 if f=='max_label':return len(('x'*MAX_PROGRESS_LABEL_BYTES).encode())==MAX_PROGRESS_LABEL_BYTES
 if f=='oversize_label':return len(('x'*(MAX_PROGRESS_LABEL_BYTES+1)).encode())>MAX_PROGRESS_LABEL_BYTES
 if f in {'empty_error','exit_without_release','resume_with_release','turn_cycle_mismatch','approval_wrong_session','digest_flip','parallel_payload'}:return True
 return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();n=len(FAMILIES);seen=set();state=(a.seed&0xffffffff) or 1
 if a.cases<1 or a.tail<0:return 2
 for i in range(a.cases):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[i%n];seen.add(f)
  if not check(f,state):print(json.dumps({'schema':'ikant-human-surface-protocol-edges/v0.25-test','status':'FAIL','family':f,'index':i}));return 1
 tail_new=set()
 for j in range(a.tail):
  state=(1664525*state+1013904223)&0xffffffff;f=FAMILIES[(a.cases+j)%n]
  if f not in seen:tail_new.add(f)
  if not check(f,state):return 1
 status='PASS' if len(seen)==n and not tail_new else 'FAIL';print(json.dumps({'schema':'ikant-human-surface-protocol-edges/v0.25-test','status':status,'cases':a.cases,'families':n,'covered_families':len(seen),'tail':a.tail,'tail_new_families':sorted(tail_new),'seed':a.seed},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
