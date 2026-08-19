# Dashboard egress v0.10

## Problem closed

v0.9 sealed and hash-checked dashboard frames, but its reference adapter acknowledged the candidate before the transport write. It also retained only the frame digest, making a crash after seal but before acknowledgement unrecoverable.

## Minimal mutation

v0.10 keeps cognition untouched and hardens only the human egress boundary:

1. **Prepare** renders, validates, persists and seals one canonical frame.
2. **Pending** state blocks every second frame and every new human turn.
3. **Deliver** is performed by the host transport.
4. **Acknowledge** occurs only after successful transport submission/flush and exact-text comparison.
5. **Recover** replays the persisted pending frame byte-for-byte after crash/restart.
6. **Journal** records each transition in an append-only SHA-256 predecessor chain.

The model is at-least-once: a crash after transport success but before ACK can replay the same frame. This is preferred to inventing or skipping human output.

## Fail-closed cases

Prefix/suffix/wrapper, stale receipt, wrong session/epoch/sequence, release-flag mismatch, missing/tampered pending artifact, malformed/tampered journal, snapshot/journal divergence, frame >128 KiB, CR/NUL/ANSI/bidi controls, duplicate seal and legacy v0.9 pending migration all fail closed.
