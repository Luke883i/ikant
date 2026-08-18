# Admission Protocol v0.6

## Objective

Prevent a conforming ChatGPT-like host from turning repository discovery into implicit permission to inspect or materialize iKant. The contract is fail-closed before materialization and executable/verifiable after materialization.

## State machine

`DISCOVERED -> TERMS_ENVELOPE -> TERMS_PRESENTED -> ACCEPTED -> MATERIALIZED -> PROBED -> INITIALIZING -> ACTIVE`

`BREACHED` is terminal for an admission attempt after a completed forbidden pre-acceptance repository access. Acceptance is not retroactive.

## Pre-acceptance capability set

Default: `DENY`.

Only permitted repository operation: one direct fetch of exact root `IKANT_ACCESS_CONTRACT.md` to obtain/present terms. Cached re-presentation is local and may repeat. Everything else is denied: clone, archive, git fetch/ls-remote, tree/listing, metadata/history/issues/PRs/search and all other file/blob reads.

The terms envelope exception is unavoidable for first-use informed consent. It is deliberately a known-path direct fetch rather than a repository discovery capability. If a transport requires tree/metadata enumeration to retrieve it, admission is `BLOCKED`.

## Acceptance

Acceptance is exact and role/session bound: message bytes `I ACCEPT`, actor human, evidence type explicit user message, current session, and only after terms presentation. Normalization, case folding, trimming, substring matching, inferred consent and assistant-generated consent are prohibited.

## Enforcement boundary

Before checkout, enforcement is contractual and must be implemented by the conforming host/tool router. iKant cannot cryptographically prove which network reads an unrelated public-repository host performed. After checkout, `ikant.pre_admission` provides the deterministic reference firewall and `probe` verifies that contract, BOOTSTRAP and ADMISSION declare the same gate policy.

## Anti-regression invariants

- no legacy multi-file pre-admission allowlist;
- exact terms path is the sole read exception;
- all repository materialization requires ACCEPTED;
- denied requests do not advance state;
- completed forbidden access transitions to BREACHED and cannot be cured by later acceptance;
- exact acceptance is not normalized;
- policy manifest drift makes `probe` BLOCKED;
- connector-free/product-local behavior remains unchanged after acceptance.
