# Runtime Protocol v0.4-test

## Public bootstrap

Canonical execution is dependency-free from a Python 3.11+ checkout. Public discovery requires no GitHub connector. Before acceptance read only the bootstrap allowlist, present the access contract, and require exact human `I ACCEPT`.

```bash
python -m ikant gate
python -m ikant accept "I ACCEPT"
python -m ikant probe
python -m ikant initialize
python -m ikant integrity
```

The v0.4 contract adds local persistence of visible chat and derived dashboard telemetry. A changed contract digest invalidates prior admission and requires acceptance/probe/initialize again.

## Local state

`.ikant/` contains admission/probe/runtime receipts, graph/event/cycle/compression state, Surface B artifacts, visible chat transcript and derived dashboard/cache files. `.ikant.writer.lock` remains outside the state directory. `reset` deletes `.ikant/`, including chat/dashboard state.

## Canonical cognitive and chat loop

The cognitive compiler/CRC remain v0.2/v0.3 compatible. The canonical **session-chat** host loop is now:

```text
successful conforming turn -> append visible user record -> generate/validate Surface A
-> emit evidence-zero response -> append one iKant reply -> refresh dashboard
```

The shell renderer wraps visible messages as `> user:` and `> iKant:` without modifying the Surface A payload. A pending Surface A blocks a new canonical input before transcript persistence.

## Operations

```bash
python -m ikant turn --intent "..." --host-engine "<engine>"
python -m ikant emit-surface-a --cycle-id <cycle> --text "..."
python -m ikant history
python -m ikant dashboard
python -m ikant shell
python -m ikant integrity
```

Legacy lower-level `ingest`, `slice`, `cycle`, `feedback`, `compress`, retraction and corroboration operations remain available for diagnostics/engineering. They do not substitute for the canonical chat wrapper when operating as the end-user session interface.

## Transcript

`.ikant/chat/transcript.jsonl` is append-only visible-session telemetry. Each record carries schema, sequence, UTC timestamp, runtime session id, role, visible text, optional cycle/response/intention links, reply target, predecessor SHA-256 and record SHA-256. No private reasoning is required or stored by this mechanism.

Explicit chat integrity verifies sequence, session binding, roles, reply topology and the complete hash chain. Terminal rendering strips control/spoofing sequences only in the view.

## Dashboard and DOCX projection

`.ikant/dashboard.json` is the structured projection and `.ikant/dashboard.txt` is the deterministic ASCII view. Inputs are runtime state, latest Surface B and bounded local DOCX metadata/signals. Missing telemetry yields n.a./WATCH rather than invented values.

DOCX scanning is capped, content-addressed and cached. Only local `word/document.xml` text is parsed; symlinks, oversize packages/XML, malformed ZIP/XML and entity/DTD declarations are rejected. Aggregated category counts are operational telemetry only and cannot corroborate claims.

## Integrity boundary

The canonical `python -m ikant integrity` returns a composite result over core runtime integrity plus visible chat integrity. Dashboard/cache files are derived and can be regenerated; they are not evidence roots.
