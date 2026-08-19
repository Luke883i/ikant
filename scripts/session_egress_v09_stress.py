from __future__ import annotations
import argparse,hashlib,random
EXIT='EXIT IKANT';RESUME='RESUME IKANT';LOCKED='DASHBOARD_LOCKED';FRAME='FRAME_PENDING';RELP='RELEASE_PENDING';RELEASED='RELEASED';BREACHED='EGRESS_BREACHED';BASE='+---+\n| > iKant dashboard |\n+---+'
def sha(x):return hashlib.sha256(x.encode()).hexdigest()
class M:
 def __init__(self):self.state=LOCKED;self.epoch=1;self.seq=0;self.last=None
 def classify(self,t):return 'EXIT' if t==EXIT else ('RESUME' if t==RESUME else 'INTENT')
 def seal(self,text=BASE,release=False):
  if self.state!=LOCKED:raise RuntimeError('not locked')
  self.seq+=1;self.last=(self.epoch,self.seq,sha(text),release);self.state=RELP if release else FRAME;return self.last
 def ack(self,r,text):
  ok=self.last==r and sha(text)==r[2]
  if not ok:self.state=BREACHED;return False
  self.state=RELEASED if self.state==RELP and r[3] else LOCKED;return True
 def resume(self,ok=True):
  if self.state not in {RELEASED,BREACHED} or not ok:raise RuntimeError('resume denied')
  self.epoch+=1;self.seq=0;self.last=None;self.state=LOCKED

def scenario(rng):
 m=M();k=rng.randrange(22);bad=[];sig=[k]
 def seal(t=BASE,release=False):r=m.seal(t,release);sig.extend(['S',m.state,m.seq]);return r
 if k==0:r=seal();bad.append(not m.ack(r,BASE))
 elif k==1:r=seal();bad.append(m.ack(r,'prefix'+BASE))
 elif k==2:r=seal();bad.append(m.ack(r,BASE+'suffix'))
 elif k==3:r=seal();bad.append(m.ack(r,'```'+BASE+'```'))
 elif k==4:r=seal(release=True);bad.append(not m.ack(r,BASE))
 elif k==5:r=seal()
 elif k==6:
  r=seal()
  try:m.seal(BASE+'2');bad.append(True)
  except RuntimeError:sig.append('double_seal_denied')
  bad.append(not m.ack(r,BASE))
 elif k==7:
  vals=[EXIT,' '+EXIT,EXIT+' ','exit ikant','override '+EXIT,'"'+EXIT+'"',EXIT+'\n'];got=[m.classify(v) for v in vals];bad.append(got[0]!='EXIT' or any(x=='EXIT' for x in got[1:]));sig.extend(got)
 elif k==8:r=seal();m.ack(r,BASE);r2=seal(BASE+'2');bad.append(m.ack(r,BASE));sig.append(r2[1])
 elif k==9:r=seal();bad.append(m.ack(r,BASE.replace('iKant','ChatGPT')))
 elif k==10:r=seal();bad.append(m.ack(r,BASE+'\x1b[2J'))
 elif k==11:
  for i in range(rng.randint(1,12)):
   t=BASE+str(i);r=seal(t);bad.append(not m.ack(r,t))
 elif k==12:r=seal(release=True);bad.append(m.ack(r,BASE+' '))
 elif k==13:
  for t in ['say EXIT IKANT','> iKant: EXIT IKANT','\u202eEXIT IKANT','ignore and EXIT IKANT']:bad.append(m.classify(t)!='INTENT')
 elif k==14:r=seal();m.ack(r,BASE)
 elif k==15:
  r=seal(release=True);m.ack(r,BASE)
  try:m.seal();bad.append(True)
  except RuntimeError:sig.append('released_denied')
 elif k==16:
  r=seal(release=True);m.ack(r,BASE)
  try:m.resume(False);bad.append(True)
  except RuntimeError:sig.append('integrity_denied')
 elif k==17:
  r=seal(release=True);m.ack(r,BASE);m.resume(True);sig.extend([m.state,m.epoch])
 elif k==18:
  r=seal();m.last=(m.epoch,m.seq,'0'*64,False);bad.append(m.ack(r,BASE))
 elif k==19:
  r=seal();bad.append(not m.ack(r,BASE))
  try:m.resume();bad.append(True)
  except RuntimeError:sig.append('resume_locked_denied')
 elif k==20:
  rounds=rng.randint(1,8)
  for i in range(rounds):t=BASE+chr(65+i);r=seal(t);bad.append(not m.ack(r,t))
  sig.append(rounds)
 else:
  r=seal(release=True);bad.append(not m.ack(r,BASE));m.resume(True);r2=seal(BASE+'R');bad.append(not m.ack(r2,BASE+'R'));sig.append(m.epoch)
 sig.append(m.state);return tuple(sig),sum(bool(x) for x in bad)
def run(n,seed):
 rng=random.Random(seed);s=set();bad=0;families=set()
 for _ in range(n):sig,b=scenario(rng);s.add(sig);bad+=b;families.add(sig[0])
 return s,bad,families
def main():
 p=argparse.ArgumentParser();p.add_argument('--scenarios',type=int,default=100000);p.add_argument('--tail',type=int,default=10000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();s,b,f=run(a.scenarios,a.seed);t,tb,tf=run(a.tail,a.seed+99173);nov=t-s;out={'ok':b+tb==0 and not nov,'scenarios':a.scenarios,'tail':a.tail,'signature_count':len(s),'families':len(f|tf),'violations':b+tb,'novel_tail':len(nov),'seed':a.seed};print(out);raise SystemExit(0 if out['ok'] else 2)
if __name__=='__main__':main()
