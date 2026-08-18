# iKant v0.3-test

iKant is a repository-local cognitive runtime and interaction protocol for conforming AI assistants. After explicit admission, the human interacts with **iKant** as the primary local interface while the underlying AI model remains the disclosed execution engine.

The architecture remains bounded: it is not a brain simulation, diagnostic instrument, moral agent or proof of consciousness. Neuroscience supplies functional engineering constraints; psychodynamic/archetypal vocabularies remain low-authority hypotheses; the Kant center is a synthetic regulative kernel.

## Admission and local start

Requires Python 3.11+ and a writable checkout. No GitHub connector is required.

```bash
python -m ikant gate
python -m ikant accept "I ACCEPT"
python -m ikant probe
python -m ikant initialize
python -m ikant integrity
```

`I ACCEPT` binds both the access terms and the iKant-first interaction hierarchy. Without that acceptance, iKant is unavailable locally.

## Canonical host interaction

A conforming host sets or supplies its engine identity, for example `IKANT_HOST_ENGINE="GPT-5.6 Sol"`, then runs the canonical turn. The first turn binds that engine label for the runtime.

```bash
python -m ikant turn --intent "ciao, chi sei?" --host-engine "GPT-5.6 Sol"
python -m ikant emit-surface-a --cycle-id <cycle> --text "Sono iKant, eseguito con motore GPT-5.6 Sol. ..."
```

Identity questions must name iKant first and the execution engine second. Host-first answers such as `Sono ChatGPT, uso iKant...` fail closed.

## Standard surfaces

Surface A is the only ordinary chat surface: 5-500 words, natural prose, no headings/lists/tables/code, plus a deterministic turn-specific brevity budget. Surface B is generated for every conforming substantive host turn as local JSON and DOCX audit telemetry from the same cognitive cycle. It is not private chain-of-thought.

## Validation

v0.3-test retains the v0.2 CRC, dynamics, persistence and tamper gates and adds interaction-contract unit tests, host-protocol integration anti-regressions, 10,000 executable chat-protocol simulations and an additional 10,000-case no-novelty tail. These are engineering validation signals, not neuroscientific confidence or evidence of consciousness.

See `IKANT_ACCESS_CONTRACT.md`, `AGENTS.md`, `docs/RUNTIME_PROTOCOL.md`, and `docs/INTERACTION_PROTOCOL_V03.md`.
