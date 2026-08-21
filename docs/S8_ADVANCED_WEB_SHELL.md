# S8 — Advanced Web Shell

S8 turns the canonical local PWA into a session-bound, single-writer operational shell without creating a second authority path or a second semantic human-output surface.

## Constitutional statement

The browser is a paired transport and control console. It is not an epistemic authority, approval authority, grant issuer, lease issuer, execution authority, or source of semantic iKant output.

The canonical ACTIVE path is:

`paired bearer -> shell open -> single writer -> monotonic operation seq -> unique idempotency key -> expected last ACK binding -> existing S2/S7 operation -> HSPv2 sealed dashboard frame -> exact frame ACK -> next operation`

The semantic-output boundary remains S7:

`browser shell chrome != HSPv2 semantic output`

Only the sealed HSPv2 dashboard frame is semantic iKant output. Shell status labels are local zero-authority control state.

## Shell protocol

S8 introduces:

- `ikant-advanced-web-shell/v0.26-test` — zero-authority shell projection;
- `ikant-advanced-web-shell-command/v0.26-test` — exact command envelope;
- `ikant-advanced-web-shell-ack/v0.26-test` — shell-bound exact frame ACK.

A shell is bound to one ACTIVE runtime session and one browser client id. Reopening with the same client is idempotent; a second client cannot become the writer for that process-local shell session.

The first operation must be unbound `SYNC`. Every later operation must carry the exact identity of the last acknowledged sealed frame. Operations are monotonically sequenced. An idempotency key is unique for the whole bounded shell session and cannot be recycled for a later operation.

If an operation has produced a sealed frame but its response or ACK is lost, the same command can replay only the already-pending response. It cannot execute the underlying TURN twice. A different operation is denied until the exact pending frame is acknowledged.

## Canonical operations

The S8 command surface is deliberately small:

- `SYNC` — recover or obtain the canonical server-owned frame;
- `TURN` — submit bounded user text through the existing local embodiment and HSPv2 path;
- `EXIT` — request exact `EXIT IKANT` release semantics;
- `RESUME` — request exact `RESUME IKANT` recovery semantics.

S8 does not add arbitrary JavaScript execution, arbitrary HTTP, browser automation authority, model transport, secrets, grants, leases, native process execution, downloads, POST/form submission, or direct S3 material action authority.

## Legacy-route containment

Historical `/api/v1/*` compatibility remains available before an S8 shell claims the ACTIVE writer. Once the canonical S8 shell is claimed, legacy ACTIVE mutation routes that could bypass sequencing are denied, including frame ACK, turn, resume, initialize and voice-transcribe paths. The canonical PWA uses only `/api/v2/shell/open`, `/api/v2/shell/command`, and `/api/v2/shell/ack` for ACTIVE operation flow.

## Boundedness and replay history

A shell session is bounded to 4096 operations. The complete idempotency-key history is retained for that bounded process-local shell session, so a sufficiently old key cannot become valid again merely because an LRU window evicted it. A fresh runtime session yields a fresh shell identity and budget.

## Falsification model

The S8 adversarial lattice covers 69 mutation families compressed into ten operational kill classes, including writer theft, runtime-session drift, sequence drift, idempotency reuse, expected-frame drift, pending-command substitution, ACK substitution, malformed downstream frames, legacy-route bypass and authority/surface collapse.

The current-slice contract requires:

- 1,000,000 stress instances;
- 10,000,000 semantic mutation instances;
- 1,000,000 edge instances;
- +100,000 no-novelty tail;
- seed 883 for the declared current-slice saturation.

These are semantic protocol mutations over the S8 shell contract, not a claim of ten million compiled AST mutants.

## Explicit non-goals

S8 does not replace S1 authorization, S3 Web Agency, S5 model/runtime supply-chain controls, S6 temporal authorization freshness, S7 HSPv2, or the v0.11 sealed-frame transport boundary. It compresses browser concurrency and retry ambiguity into a deterministic local shell protocol while preserving every lower-layer authority separation.
