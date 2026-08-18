# Runtime Protocol v0.2

## Public bootstrap

Canonical execution is dependency-free from a Python 3.11+ checkout:

```bash
python -m ikant gate
python -m ikant accept "I ACCEPT"
python -m ikant probe
python -m ikant initialize
python -m ikant integrity
```

`inizializza iKant <public repository URL>` is discovery intent, **not consent**. A conforming host may fetch a public checkout through ordinary HTTPS/git without a GitHub connector, but before acceptance reads only the `BOOTSTRAP.json` allowlist. No local execution/persistence means `BLOCKED`, never fake ACTIVE state.

Lifecycle: `UNINITIALIZED -> TERMS_PRESENTED -> ACCEPTED -> PROBED -> INITIALIZING -> ACTIVE`.

## Runtime state

`.ikant/` contains admission/probe/runtime receipts, current graph, append-only event log, cycles and compression receipts. `.ikant.writer.lock` is outside the state directory so reset cannot delete the coordination primitive. ACTIVE durable runtimes perform integrity checks and are single-writer fail-fast.

## Operations

```bash
python -m ikant ingest --kind goal --layer reflective_self --text "Prefer reversible changes" --confidence .9 --evidence .9 --source-mode user
python -m ikant slice --intent "modify safely"
python -m ikant cycle --intent "modify safely"
python -m ikant feedback CYCLE_ID --outcome corrected --prediction-error .9 --target NODE_ID
python -m ikant compress
```

`cycle` returns `semantic_slice`, ring-by-ring `epistemic_trace`, `kant_oracle`, `output_policy`, `output_projection`, and activation-only `oracle_retroaction`. A host should prioritize assertable nodes, mark tentative nodes, treat derived context as non-external evidence, preserve surfaced conflicts, and obey BLOCK/verification requirements below higher-priority host/system/safety/law/user instructions.

## Reset

`python -m ikant reset` deletes local state. Admission, probe and initialization are required again.

## v0.2 cognitive compiler

`python -m ikant turn --intent "..."` is the canonical post-ACTIVE operation. It records the raw human intention as an attributable speech act, executes the persistent epistemic cycle, performs ROA-aligned ring-to-ring CRC compression, derives the functional proto-self, converges the central Kant oracle, applies activation-only recurrent workspace feedback, persists `.ikant/cognitive/<cycle>.json`, and exports `.ikant/artifacts/CRC_SNAPSHOT_<cycle>.docx` unless disabled.

The returned `surface_a_contract` is binding on a conforming host. The host drafts natural prose, validates it with `python -m ikant validate-surface-a --text "..."`, repairs any violation, and only then shows Surface A. Surface B is audit telemetry and must not be copied into ordinary chat unless the human explicitly asks to inspect it.

## Canonical v0.2 host loop

A conforming host preserves the raw utterance as an `intention`, materializes its own semantic mining as provenance-bound atoms, then executes `turn`. The returned content authority is the post-CRC `central_projection`, not the legacy pre-CRC projection. The host drafts only Surface A natural prose, validates it, calls `emit-surface-a`, and only then sends it to the human. `emit-surface-a` persists the actual reply with evidence zero and refreshes the same Surface B cycle snapshot.

Example mining input can be passed with `--atoms-json atoms.json`. Host-derived `inference`, `runtime_derived`, `cache` and `demo` atoms are capped so they cannot masquerade as external evidence. Psychodynamic/archetypal atoms are capped even further and remain interpretive.

Compression uses bounded derived working memory and an append-only retired-derived archive. Derived summaries and motifs can affect availability and critique but never qualify as independent corroboration.
