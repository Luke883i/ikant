# iKant v0.10-test

iKant is a repository-local cognitive runtime and interaction protocol for conforming AI session-chat hosts. v0.10 hardens the exclusive dashboard channel without changing the cognitive lattice: delivery becomes two-phase, pending frames are crash-recoverable, and egress transitions are hash-journaled.

## Canonical admission

The v0.9 bounded orientation firewall remains unchanged. Present the digest-bound T&C, receive exact current-session `I ACCEPT`, then materialize and run:

```bash
python -m ikant accept "I ACCEPT" --presented-terms-sha256 <presented-contract-sha256>
python -m ikant probe
python -m ikant initialize
```

The v0.10 contract changes the accepted runtime persistence/egress semantics, so an older receipt does not silently authorize the new contract.

## Crash-recoverable exclusive dashboard

After initialize, the human channel is dashboard-only. Normal delivery is:

`DASHBOARD_LOCKED -> seal/persist -> FRAME_PENDING -> transport write+flush -> exact acknowledgement -> DASHBOARD_LOCKED`

Exit is:

`DASHBOARD_LOCKED -> RELEASE_PENDING -> transport -> acknowledgement -> RELEASED`

A frame is not considered delivered merely because it was rendered. If the process or transport fails before acknowledgement, the exact sealed bytes are recovered from `.ikant/egress-frames/` and replayed before any new human turn. `.ikant/egress-events.jsonl` is append-only/hash-chained and must agree with `.ikant/egress.json`.

`EXIT IKANT` remains exact. `RESUME IKANT` opens a new epoch only after runtime integrity. Legacy v0.9 pending states migrate fail-closed because v0.9 did not persist the sealed frame bytes needed for deterministic replay.

## Boundaries

Dashboard/transcript/egress journals and Surface B are control/audit projections, not evidence. The nine-ring CRC, proto-self, functional psyche, Kant regulation and evidence model are unchanged by this hardening.

No connector or Node.js runtime is required after materialization. Python 3.11+ and writable local `.ikant/` persistence are sufficient.

See `IKANT_ACCESS_CONTRACT.md`, `AGENTS.md`, `docs/DASHBOARD_EGRESS_V10.md` and `docs/V10_DOD.md`.
