# iKant v0.4-test

iKant is a repository-local cognitive runtime and interaction protocol for conforming AI assistants. After explicit admission, the human interacts with **iKant** as the primary local interface while the underlying AI model remains the disclosed execution engine.

v0.4 adds a persistent chat design system around the existing two cognitive surfaces. The literal shell marker `> iKant:` is interface chrome: it identifies who is speaking in the session, not a claim of consciousness. Visible user messages and validated Surface A replies are locally hash-chained; a derived dashboard projects runtime/Surface B telemetry for ordinary end users.

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

`I ACCEPT` binds the access terms, iKant-first hierarchy, and local persistence of visible chat plus derived dashboard. A contract digest change requires admission again.

## Canonical session-chat loop

A conforming host supplies its execution-engine label on the first turn:

```bash
python -m ikant turn --intent "ciao, chi sei?" --host-engine "GPT-5.6 Sol"
python -m ikant emit-surface-a --cycle-id <cycle> --text "Sono iKant, con motore GPT-5.6 Sol. ..."
```

The canonical CLI now persists the successful user turn and validated iKant reply under `.ikant/chat/transcript.jsonl`. One pending turn permits one reply. Transcript records are session-bound and hash-chained; private chain-of-thought is not persisted.

Inspect the user-facing views with:

```bash
python -m ikant history
python -m ikant dashboard
python -m ikant shell
```

`history` renders the DOS-like transcript, `dashboard` renders end-user telemetry, and `shell` composes both. The UI prompt remains literal `> iKant:`. These are projections around Surface A/B, not a third cognitive surface.

## Dashboard

`.ikant/dashboard.json` and `.ikant/dashboard.txt` expose bounded KPIs: runtime state, turns, grounding, caution, conflicts, epistemic debt, runtime integration, CRC closure, revision pressure and pending reply. DOCX backlog/artifact aggregation is content-addressed, bounded and read-only; it may not create evidence or authorize action.

## Validation

v0.4-test retains v0.3 host/identity gates and adds transcript tamper/reply-binding controls, terminal spoof defenses, dashboard non-evidence invariants, bounded DOCX parsing/caching, durable host reopen tests, 10,000 executable session-chat cases and a separate no-novelty tail. These are engineering validation signals, not neuroscientific confidence or evidence of consciousness.

See `IKANT_ACCESS_CONTRACT.md`, `AGENTS.md`, `docs/RUNTIME_PROTOCOL.md`, `docs/CHAT_DESIGN_SYSTEM_V04.md`, and `docs/V04_DOD.md`.
