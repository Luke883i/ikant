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

`inizializza iKant <public repository URL>` is discovery intent, not consent. A conforming host may fetch a public checkout through ordinary HTTPS/git without a GitHub connector, but before acceptance reads only the `BOOTSTRAP.json` allowlist. No local execution/persistence means `BLOCKED`, never fake ACTIVE state.

Lifecycle: `UNINITIALIZED -> TERMS_PRESENTED -> ACCEPTED -> PROBED -> INITIALIZING -> ACTIVE`.

## Runtime state

`.ikant/` contains admission/probe/runtime receipts, current graph, append-only event log, cycles, cognitive snapshots, compression state and derived archive. `.ikant.writer.lock` is outside the state directory so reset cannot delete the coordination primitive. ACTIVE durable runtimes perform integrity checks and are single-writer fail-fast.

## Canonical v0.2 cognitive compiler

`python -m ikant turn --intent "..." --atoms-json atoms.json` is the canonical post-ACTIVE operation. It records the raw human intention, ingests provenance-bound mined atoms, executes the persistent epistemic cycle, performs ROA-aligned ring-to-ring CRC compression, derives the functional proto-self, converges the central Kant oracle, compiles a post-CRC response projection, applies activation-only recurrent workspace feedback, persists `.ikant/cognitive/<cycle>.json`, and exports `.ikant/artifacts/CRC_SNAPSHOT_<cycle>.docx` unless disabled.

The host then drafts only from `central_projection` and `surface_a_contract`, validates with `python -m ikant validate-surface-a --text "..."`, repairs until valid, calls `python -m ikant emit-surface-a --cycle-id <cycle> --intention-node-id <node> --text "..."`, and only then sends the response. `emit-surface-a` persists the actual reply with evidence zero and refreshes the same Surface B JSON/DOCX.

Host-derived `inference`, `runtime_derived`, `cache` and `demo` atoms are evidence-capped so they cannot masquerade as external support. Psychodynamic/archetypal atoms are capped further and remain interpretive.

## Lower-level operations

`ingest`, `relate`, `slice`, `cycle`, `feedback`, `compress`, `retract`, `reinstate`, `corroborate` and `modulate` remain available for diagnostics and controlled maintenance. `cycle` is a v0.1-level diagnostic; `turn` is the product-level v0.2 path.

## Derived memory

Compression uses bounded derived working memory and an append-only retired-derived archive. Derived summaries and motifs can affect availability and critique but never qualify as independent corroboration. Compression excludes its own derived assertions from subsequent analytic windows.

## Reset

`python -m ikant reset` deletes local state. Admission, probe and initialization are required again.
