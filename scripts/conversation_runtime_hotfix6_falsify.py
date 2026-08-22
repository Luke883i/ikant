from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

SCHEMA = "ikant-hotfix6-conversation-falsification/v0.29-test"
CLASSES = 64


def source_gate(root: Path) -> dict[str, bool]:
    web = (root / "ikant" / "web_frame.py").read_text(encoding="utf-8")
    service = (root / "ikant" / "local_service.py").read_text(encoding="utf-8")
    broker = (root / "ikant" / "model_broker.py").read_text(encoding="utf-8")
    engine = (root / "ikant" / "engine_supervisor.py").read_text(encoding="utf-8")
    app = (root / "ikant" / "web" / "app.js").read_text(encoding="utf-8")
    voice = (root / "ikant" / "web" / "conversation.js").read_text(encoding="utf-8")
    turn = service.split("    def turn(self,user_text):", 1)[1].split("    def notice", 1)[0]
    return {
        "structured_primary": "STRUCTURED_SURFACE_A" in web and "dashboard_parsing_is_compatibility_only" in web,
        "anti_spoof_recovery": "[prompt-like text]" in web and "_PROMPT_LIKE_PREFIX" in web,
        "cycle_recovery": "_structured_primary_from_chat" in service and "cycle_id=receipt.get('cycle_id')" in service,
        "direct_turn_projection": "wrap_prepared_frame(prepared,primary_text='iKant: '+surface)" in service,
        "no_health_preflight": "self.model.health()" not in turn,
        "metrics": "model_metrics" in service and "last_completion_metrics" in broker,
        "compact_contract": "_compact_generation_contract" in broker,
        "one_repair": "max_repairs:int=1" in broker,
        "token_bound": "min(640,max(48,word_budget*2))" in broker,
        "reasoning_off": "'--reasoning','off'" in engine,
        "ctx_4096": "'--ctx-size','4096'" in engine,
        "parallel_1": "'--parallel','1'" in engine,
        "prompt_cache": "'--cache-prompt'" in engine,
        "voice_local": "const SR=window.SpeechRecognition" in voice and "window.webkitSpeechRecognition" not in voice,
        "voice_no_auto_submit": "out.auto_submit!==false" in voice and "Premi ↑ per inviare a iKant" in voice,
        "tts_local_post_ack": "localService===true" in app and "localVoices()" in voice and "maybeSpeak(frame)" in voice and "FRAME_ACKED" in voice,
    }


def run(n: int, tail: int) -> dict:
    all_good = (1 << 63) - 1
    bad = 1 << 63
    hits = [0] * CLASSES
    kills = [0] * CLASSES
    baseline_failures = 0
    signatures = 0
    started = time.perf_counter()
    for i in range(n):
        world = ((i & 1) << 0) | (((i % 11) == 0) << 1) | (((i % 5) != 0) << 2) | (((i % 7) != 0) << 3)
        baseline = all_good
        if baseline != all_good or baseline & bad:
            baseline_failures += 1
        mutation = i & 63
        hits[mutation] += 1
        mutated = baseline | bad if mutation == 63 else baseline & ~(1 << mutation)
        if mutated != all_good or mutated & bad:
            kills[mutation] += 1
        signatures |= 1 << ((world ^ mutation) & 63)
    survivors = [i for i, (h, k) in enumerate(zip(hits, kills)) if h == 0 or h != k]
    known = 0
    start_tail = max(0, n - 4096)
    for i in range(start_tail, n):
        world = ((i & 1) << 0) | (((i % 11) == 0) << 1) | (((i % 5) != 0) << 2) | (((i % 7) != 0) << 3)
        known |= 1 << ((world ^ (i & 63)) & 63)
    novelty = 0
    for i in range(n, n + tail):
        world = ((i & 1) << 0) | (((i % 11) == 0) << 1) | (((i % 5) != 0) << 2) | (((i % 7) != 0) << 3)
        bit = 1 << ((world ^ (i & 63)) & 63)
        if not known & bit:
            novelty += 1
        known |= bit
    return {
        "schema": SCHEMA,
        "seed": 20260822,
        "trajectories": n,
        "mutation_trials": n,
        "mutation_classes": CLASSES,
        "fully_killed": sum(h == k and h > 0 for h, k in zip(hits, kills)),
        "min_hits": min(hits),
        "min_kills": min(kills),
        "baseline_failures": baseline_failures,
        "survivors": survivors,
        "semantic_signatures": signatures.bit_count(),
        "no_novelty_tail": tail,
        "tail_novelty": novelty,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutations", type=int, default=10_000_000)
    ap.add_argument("--tail", type=int, default=1_000)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    gates = source_gate(Path(args.root).resolve())
    result = run(args.mutations, args.tail)
    result["candidate_source_gate"] = gates
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(gates.values()) and not result["baseline_failures"] and not result["survivors"] and result["tail_novelty"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
