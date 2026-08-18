from __future__ import annotations
import argparse,json,random,tempfile,time
from pathlib import Path
from types import SimpleNamespace

from ikant.chat_session import ChatLog, sanitize_terminal_text
from ikant.dashboard import project_dashboard, render_dashboard_ascii

FAMILIES=("hello","identity","analysis","unicode","multiline","escape","long","repeat","uncertain","conflict","dashboard","backlog")

def runtime(root:Path):
    state=root/".ikant";state.mkdir(parents=True)
    snap=state/"snap.json"
    snap.write_text(json.dumps({"session_id":"SES-STRESS","cycle_id":"C0","reticulum":{"diagnostics":{"epistemic_debt_open_count":0},"roa_alignment":{"crc_basic":True}},"dynamic_state":{"central_oracle":{"regulative_mode":"REFLECTIVE_SYNTHESIS","base_oracle":{"faculties":{"sensibility_grounding":.8}}},"central_projection":{"must_surface_conflicts":[]},"proto_self":{"proto_self_index":.62},"surface_a_contract":{"regulation":{"epistemic_caution":.25}}}}),encoding="utf-8")
    obj=SimpleNamespace();obj.root=root;obj.state_dir=state;obj.nodes={"sentinel":SimpleNamespace(evidence=.37)};obj.runtime={"session_id":"SES-STRESS","status":"ACTIVE","cycle_count":0,"compression":{"trend":{"metrics":{"revision_pressure":.1}}},"cognitive":{"last_snapshot":str(snap)}};return obj

def user_text(family,i,rng):
    if family=="escape":return f"case {i}\x1b[2J preserve terminal safety {rng.randrange(99)}"
    if family=="unicode":return f"perché realtà etica café Δ case {i}"
    if family=="multiline":return f"first line {i}\nsecond line\nthird line"
    if family=="long":return " ".join(["context"]*120)+f" {i}"
    if family=="repeat":return "repeat stable intention"
    return f"{family} user case {i} value {rng.randrange(1000)}"

def ikant_text(family,i):return f"iKant response for {family} case {i}, concise and externally visible only."

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--cases",type=int,default=10000);ap.add_argument("--novelty-tail",type=int,default=2000);ap.add_argument("--seed",type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic();signatures=set();tail_new=set()
    with tempfile.TemporaryDirectory() as td:
        rt=runtime(Path(td));log=ChatLog(rt.state_dir/"chat"/"transcript.jsonl",runtime_session_id=rt.runtime["session_id"]);sentinel=rt.nodes["sentinel"].evidence
        for i in range(a.cases):
            family=FAMILIES[i%len(FAMILIES)];u=log.append("user",user_text(family,i,rng));log.append("ikant",ikant_text(family,i),reply_to_seq=u["seq"],cycle_id=f"C{i}",response_id=f"R{i}");rt.runtime["cycle_count"]+=1
            if i in {0, 4999, a.cases-1}:
                log.verify();dash=project_dashboard(rt,backlog_paths=[]);render=render_dashboard_ascii(dash);assert render.endswith("> iKant:");assert sanitize_terminal_text(render)==render
            signatures.add(family)
        baseline=set(signatures)
        for j in range(a.novelty_tail):
            family=FAMILIES[rng.randrange(len(FAMILIES))];idx=a.cases+j;u=log.append("user",user_text(family,idx,rng));log.append("ikant",ikant_text(family,idx),reply_to_seq=u["seq"],cycle_id=f"T{j}",response_id=f"TR{j}")
            if family not in baseline:tail_new.add(family)
        receipt=log.verify();dash=project_dashboard(rt,backlog_paths=[]);assert rt.nodes["sentinel"].evidence==sentinel;assert not tail_new;assert receipt["records"]==2*(a.cases+a.novelty_tail)
        print(json.dumps({"schema":"ikant-chat-ux-stress/v0.4-test","status":"PASS","cases":a.cases,"novelty_tail":a.novelty_tail,"total_cases":a.cases+a.novelty_tail,"scenario_signatures":sorted(signatures),"saturation_m":len(signatures),"new_tail_signatures":sorted(tail_new),"records":receipt["records"],"dashboard_overall":dash["overall"],"sentinel_evidence_unchanged":True,"elapsed_s":round(time.monotonic()-t,3)},sort_keys=True))
if __name__=="__main__":main()
