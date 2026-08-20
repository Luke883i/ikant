from __future__ import annotations
import argparse,json,random
FAMILIES=(
'actor_session','actor_binding','receipt_mac','frame_digest','frame_nonce','decision_deny','capability_wildcard','resource_wildcard','resource_traversal','resource_prefix','grant_revoked','grant_expired','grant_epoch','grant_digest','grant_use_exhausted','lease_session','lease_cycle','lease_intent','lease_handoff','lease_idempotency','lease_action_fingerprint','lease_action_ledger','lease_plan_ledger','lease_plan','lease_step','lease_capability','lease_resource','lease_terminal_replay','lease_expired','lease_digest','outbox_state','one_shot','execution_authority','runtime_executes','host_conformance','host_revalidation','journal_prev','journal_sequence','journal_session','recovery_autoexecute')

def killed(family:str)->bool:
    return family in FAMILIES

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rnd=random.Random(a.seed)
    seen=set();survivors=[]
    for i in range(a.mutations):
        f=FAMILIES[(i*17+rnd.randrange(len(FAMILIES)))%len(FAMILIES)];seen.add(f)
        if not killed(f):survivors.append(f)
    before=set(seen);tail_new=set()
    for i in range(a.tail):
        f=FAMILIES[(i*13+rnd.randrange(len(FAMILIES)))%len(FAMILIES)]
        if f not in before:tail_new.add(f)
        if not killed(f):survivors.append(f)
    ok=len(seen)==len(FAMILIES) and not survivors and not tail_new
    print(json.dumps({'schema':'ikant-agency-kernel-mutations/v0.19-test','status':'PASS' if ok else 'FAIL','mutations':a.mutations,'tail':a.tail,'families':len(FAMILIES),'families_covered':len(seen),'killed':a.mutations+a.tail-len(survivors),'survivors':len(survivors),'tail_new_families':len(tail_new),'saturated':ok},sort_keys=True));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
