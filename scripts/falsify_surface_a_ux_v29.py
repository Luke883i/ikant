from __future__ import annotations
import json,time
from pathlib import Path
N=10_000_000; TAIL=1000
MUTANTS=(
'REASONING_AUTO','REASONING_ON','THINKING_KWARG_ONLY','DROP_INTERACTION_CONTRACT','VALIDATE_FORMAT_ONLY','DROP_IDENTITY_FIRST','DROP_ENGINE_DISCLOSURE','ACCEPT_TOOL_CALL','ACCEPT_EMPTY_CONTENT','ACCEPT_REASONING_ONLY','UNBOUNDED_OUTPUT','DROP_REPAIR_LOOP','FALLBACK_CLAIMS_ACTION','FALLBACK_IDENTITY_INVALID','FALLBACK_EMPTY','FALLBACK_OVER_BUDGET','PRIMARY_FULL_DASHBOARD','PRIMARY_EMPTY_WHEN_PENDING','PRIMARY_STALE_CYCLE','PRIMARY_DROP_IKANT_PREFIX','DETAILS_MISSING','DETAILS_DEFAULT_PRIMARY','DETAILS_MUTATED','ACK_PRIMARY_AS_CANONICAL','ACK_WRONG_DIGEST','VOICE_READS_DASHBOARD','PENDING_AFTER_VALID','VALID_BEFORE_REPLY','AUTHORITY_FROM_MODEL','AUTHORITY_FROM_UI','BROWSER_MARKS_READY','BROWSER_MODEL_TRANSPORT','TOOLS_ENABLED','REMOTE_ENDPOINT','FLOATING_ENGINE','FLOATING_MODEL','UNPINNED_DIGEST','RETRY_REWRITES_HISTORY','FALLBACK_MARKED_MODEL','MODEL_MARKED_FALLBACK','SOURCE_STALE_CYCLE','SURFACE_B_CYCLE_MISMATCH','PARALLEL_REPLY','DASHBOARD_LEAK_ON_SYNC','DASHBOARD_LEAK_ON_RECOVERY','ERROR_HIDDEN_BY_PENDING','EXIT_HIDDEN_BY_PENDING','CONTROL_BYTES_PRIMARY','NO_NOVELTY_GRAMMAR_DRIFT','PRIMARY_ASSET_UNSERVED','STALE_PRIMARY_CACHE','TERMINAL_PRIMARY_STYLE')
K=len(MUTANTS)

def base(i,m):
    identity=(i%7==0);fallback=(i%101==0);kind=1 if i%997==0 else (2 if i%991==0 else 0);pending=(i%13==0)
    primary=5 if kind==1 else (6 if kind==2 else (0 if pending else 1))
    if m in (5,6):identity=True
    if m in (12,14,15):fallback=True
    if m==13:fallback=True;identity=True
    if m in (17,27):kind=0;pending=True;primary=0
    if m in (26,19):kind=0;pending=False;primary=1
    if m==45:kind=1;primary=5
    if m==46:kind=2;primary=6
    return [1,1,1,0,1,0,1 if fallback else 0,0,1,1,1,1,0,0,0,0,1,1,1,0,kind,primary,1 if (kind==0 and pending) else 0,1 if (kind==0 and not pending) else 0,identity,1,1,1]

def mutate(s,m):
    if m in (0,1,2):s[0]=0
    elif m in (3,4,5,6,13):s[2]=0
    elif m==7:s[3]=1
    elif m==8:s[4]=0
    elif m==9:s[4]=0;s[5]=1
    elif m in (10,11,15):s[1]=0
    elif m==12:s[7]=1
    elif m==14:s[4]=0
    elif m in (16,21,25,43,44):s[21]=2
    elif m==17:s[21]=3
    elif m in (18,38,39,40):s[8]=0
    elif m==19:s[21]=4
    elif m==20:s[10]=0
    elif m in (22,23,24,48):s[11]=0
    elif m==26:s[21]=0
    elif m==27:s[21]=1
    elif m in (28,29):s[12]=1
    elif m==30:s[13]=1
    elif m==31:s[14]=1
    elif m==32:s[15]=1
    elif m==33:s[16]=0
    elif m in (34,35,36):s[17]=0
    elif m==37:s[18]=0
    elif m==41:s[9]=0
    elif m==42:s[19]=1
    elif m in (45,46):s[21]=0
    elif m==47:s[21]=7
    elif m==49:s[25]=0
    elif m==50:s[26]=0
    elif m==51:s[27]=0

def valid(s):
    if not s[0] or not s[1] or not s[2] or s[3] or not s[4] or s[5]:return False
    if s[6] and s[7]:return False
    if not s[8] or not s[9] or not s[10] or not s[11]:return False
    if s[12]!=0 or s[13] or s[14] or s[15] or not s[16] or not s[17] or not s[18] or s[19]:return False
    kind,primary,pending,validated=s[20],s[21],s[22],s[23]
    if primary in (2,3,4,7):return False
    if kind==0 and pending==validated:return False
    if kind==0 and pending and primary!=0:return False
    if kind==0 and validated and primary!=1:return False
    if kind==0 and primary not in (0,1):return False
    if kind==1 and primary!=5:return False
    if kind==2 and primary!=6:return False
    if not s[25] or not s[26] or not s[27]:return False
    return True

hits=[0]*K;kills=[0]*K;basefail=0;sig=set();start=time.time()
for i in range(N):
    m=i%K;s=base(i,m)
    if not valid(s):basefail+=1;continue
    hits[m]+=1;t=s.copy();mutate(t,m)
    if not valid(t):kills[m]+=1
    sig.add((s[24],s[6],s[20],s[21],s[22],s[23],s[25],s[26],s[27],i%23))
surv=[MUTANTS[j] for j in range(K) if hits[j]==0 or kills[j]!=hits[j]]
before=len(sig)
for i in range(N,N+TAIL):
    m=i%K;s=base(i,m)
    if valid(s):sig.add((s[24],s[6],s[20],s[21],s[22],s[23],s[25],s[26],s[27],i%23))
receipt={'schema':'ikant-surface-a-ux-falsification/v0.29-test','trajectories':N,'mutation_trials':sum(hits),'mutation_classes':K,'baseline_failures':basefail,'survivors':surv,'fully_killed':sum(h>0 and h==k for h,k in zip(hits,kills)),'min_hits':min(hits),'min_kills':min(kills),'semantic_signatures':len(sig),'no_novelty_tail':TAIL,'tail_novelty':len(sig)-before,'elapsed_seconds':round(time.time()-start,3),'epistemic_authority':0.0,'execution_authority':0.0,'mutants':{MUTANTS[j]:{'hits':hits[j],'kills':kills[j]} for j in range(K)}}
print(json.dumps(receipt,indent=2,sort_keys=True))
path=Path('backlog/surface_a_ux_falsification_v29.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
raise SystemExit(0 if basefail==0 and not surv and len(sig)-before==0 else 1)
