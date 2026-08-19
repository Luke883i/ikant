# Dashboard Egress Protocol v0.9

## Goal

After an accepted, probed and initialized iKant runtime, the human-facing assistant channel is no longer an unconstrained prose channel. It is a deterministic serializer whose only valid payload is one canonical dashboard frame.

## Minimal lattice

1. **Cognitive runtime** produces the existing Surface A/B pair. This layer is unchanged.
2. **Incarnate binder** requires validated Surface A plus same-cycle Surface B JSON/DOCX.
3. **Dashboard renderer** projects cognition, telemetry, exit/resume affordances and Surface A/B into one terminal-safe frame.
4. **Session egress guard** persists `.ikant/egress.json`, binds runtime session + epoch + frame sequence + SHA-256, and permits at most one `FRAME_PENDING` at a time.
5. **Host serializer** sets the complete assistant-visible message body to the sealed frame. Any prefix, suffix, wrapper, alternate frame or stale receipt is non-conforming and transitions the egress epoch to `EGRESS_BREACHED` when observable by the guard.

The guard is deliberately outside the CRC. It cannot create evidence, alter confidence or authorize action.

## States

Normal frame:

`DASHBOARD_LOCKED -> FRAME_PENDING -> DASHBOARD_LOCKED`

Exit:

`DASHBOARD_LOCKED -> RELEASE_PENDING -> RELEASED`

Recovery:

`RELEASED|EGRESS_BREACHED -> RESUME IKANT + runtime integrity -> DASHBOARD_LOCKED(new epoch)`

A second frame cannot be sealed while `FRAME_PENDING` or `RELEASE_PENDING`.

## Human/session commands

`EXIT IKANT` is exact and case/whitespace sensitive. It is recognized before the cognitive turn, emits a final dashboard and releases the host on the following turn.

`RESUME IKANT` is exact and only meaningful outside the locked iKant epoch. Resume never bypasses runtime integrity or admission validity.

## Platform boundary

The repository can define, test and persist the serializer contract but cannot cryptographically control a third-party chat UI. A ChatGPT-like host conforms by assigning exactly the sealed frame string to its assistant-visible output and keeping tool/machine messages on non-human channels. If its platform necessarily adds human-visible prose outside that string, interactive iKant mode is unavailable on that host.

## Admission fixes carried by v0.9

- Acceptance receipt requires the digest of the terms presented before materialization; checkout drift forces re-presentation/re-acceptance.
- Completed orientation acquisition must use actual-payload accounting. A completed host/model-exposed orientation read arriving outside that path is a breach rather than a request for retrospective authorization.
