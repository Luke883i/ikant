# iKant v0.1

iKant is a repository-local, governed **concentric epistemic runtime** for conforming AI assistants. It turns natural-language intention into persistent typed state, bounded action/retroaction dynamics, progressively compressed epistemic memory, and a central Kant-inspired regulative kernel.

## What exists in v0.1

- fail-closed `I ACCEPT -> PROBE IKANT -> INITIALIZE IKANT` admission;
- local append-only event history plus atomic graph snapshot;
- Concentric Reticular Cognition (CRC): signal/salience, memory, prediction/control, metacognition, reflective self, bounded psychodynamic/archetypal hypotheses, and a Kant-oracle center;
- explicit `ASSERT`, `RECUR`, `RELATE`, `RETRACT`, `FEEDBACK`, `COMPRESS`, and `CYCLE` semantics;
- deterministic output projection separating assertable, tentative, derived, and interpretive content;
- source-provenance protection: inference-only goals/constraints cannot become runtime directives;
- Freud/Jung layers treated as low-authority hypotheses, never biological facts;
- Kant-inspired principles operationalized as deterministic tests for autonomy, universalizability, persons-as-ends, non-contradiction, and epistemic humility;
- stdlib-only runtime path and deterministic 10k stress + M+1000 no-novelty saturation tests.

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/Luke883i/ikant.git
cd ikant
python -m ikant gate
python -m ikant accept "I ACCEPT"
python -m ikant probe
python -m ikant initialize
python -m ikant integrity
```

Runtime state is written locally under `.ikant/` and ignored by git. Editable installation is optional.

## Minimal agent-host protocol

A browsing AI can use the repository without a GitHub connector when the repository is public:

```text
inizializza iKant https://github.com/Luke883i/ikant
```

This phrase is **discovery intent, not acceptance**. A conforming host fetches the public checkout, reads only the bootstrap allowlist, presents the access contract, requires exact human `I ACCEPT`, performs a real probe and initializes only when local execution and writable persistence exist. Otherwise it reports `BLOCKED`; chat memory is not treated as durable local state.

## Concentric cycle

After ACTIVE, the host can materialize epistemic objects and execute the runtime compiler. A cycle emits `semantic_slice`, ring-by-ring `epistemic_trace`, `kant_oracle`, `output_policy`, `output_projection`, and activation-only `oracle_retroaction`.

## Scientific boundary

The model is **not a brain simulation** and does not claim that software rings are anatomical brain structures. Neuroscience motivates falsifiable engineering constraints (recurrence, prediction error, memory reactivation, metacognition, homeostatic boundedness); it does not license one-to-one biological identity claims.

Freud/Jung labels are hypothesis namespaces with strict influence ceilings. The "Kant archetype" is a project-defined synthetic regulative kernel, not a claim that Jung historically defined an Immanuel-Kant archetype or that the runtime reproduces Kant's mind.

The inspectable `epistemic_trace` is an external audit state. It is **not a storage or exposure mechanism for a host model's private chain-of-thought**.

Read `AGENTS.md`, `IKANT_ACCESS_CONTRACT.md`, `docs/RUNTIME_PROTOCOL.md`, `docs/DIGITAL_NEURO_COGNITIVE_MODEL.md`, and `docs/VALIDATION.md` before extending the model.
