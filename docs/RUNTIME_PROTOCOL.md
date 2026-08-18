# Runtime Protocol v0.1

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

`ingest`, `corroborate`, `modulate`, `relate`, `retract`, `reinstate`, `slice`, `cycle`, `feedback` and `compress` are available from `python -m ikant`.

`cycle` returns `semantic_slice`, ring-by-ring `epistemic_trace`, `kant_oracle`, `output_policy`, `output_projection`, and activation-only `oracle_retroaction`. A host should prioritize assertable nodes, mark tentative nodes, treat derived context as non-external evidence, preserve surfaced conflicts, and obey BLOCK/verification requirements below higher-priority host/system/safety/law/user instructions.

## Reset

`python -m ikant reset` deletes local state. Admission, probe and initialization are required again.
