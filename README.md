# iKant v0.9-test

iKant is a repository-local cognitive runtime and interaction protocol for conforming AI session-chat hosts. v0.9 closes two boundaries: acceptance is carried across repository materialization by the exact digest of the terms shown to the human, and a successful `initialize` locks the human-visible assistant channel to one canonical dashboard frame at a time.

## Admission

Before terms presentation, only bounded orientation is allowed: one limited metadata projection and single-fetch reads of `README.md`, `IKANT_ACCESS_CONTRACT.md`, `BOOTSTRAP.json`, `ADMISSION.json`, `AGENTS.md`, within 256 KiB. Presenting the contract freezes all new repository acquisition.

Only exact current-session `I ACCEPT` opens materialization. Carry the digest of the contract that was actually presented:

```bash
python -m ikant accept "I ACCEPT" --presented-terms-sha256 <presented-contract-sha256>
python -m ikant probe
python -m ikant initialize
```

If the checkout contract differs from the presented digest, acceptance fails closed and the new terms must be shown and accepted again. A completed orientation acquisition that bypasses actual payload accounting is a breach when host-initiated or model-exposed; incidental unexposed provider overfetch is quarantined.

## Exclusive dashboard mode

After successful `initialize`, `.ikant/egress.json` starts in `DASHBOARD_LOCKED`. A conforming ChatGPT-like host must use the returned dashboard frame as the **entire** assistant-visible message: no prose, markdown wrapper, citations, tool summaries or other bytes may exist outside it.

Normal turn path:

`user -> cognitive turn -> Surface B JSON/DOCX -> validate/close Surface A -> dashboard -> FRAME_PENDING -> exact-byte validation -> human -> DASHBOARD_LOCKED`

The exact user command `EXIT IKANT` produces one final release dashboard and changes the egress state to `RELEASED`; from the next turn the local assistant may answer normally outside iKant. Exact `RESUME IKANT` can re-lock a new egress epoch only when the existing ACTIVE runtime passes integrity.

Strings such as `exit ikant`, ` EXIT IKANT`, quoted or embedded `EXIT IKANT` are ordinary user intentions and do not release the lock.

The repository cannot cryptographically control an unrelated platform UI. Therefore a host that cannot guarantee whole-message dashboard serialization must report that conforming interactive iKant mode is unavailable rather than claim compliance.

## Runtime

The existing cognitive path is unchanged:

`semantic slice -> nine-ring CRC -> proto-self -> functional psyche -> monotone Kant regulation -> central projection -> workspace retroaction -> Surface A/B`

The dashboard, transcript, egress guard, hashes and Surface B are control/audit projections, not epistemic evidence. Internal affect/maturation/collapse/emergence may change caution, availability, inhibition and voice, but cannot create evidence or authorize material action.

No GitHub connector or Node.js runtime is required after materialization. Python 3.11+ and writable local `.ikant/` persistence are sufficient.

## v0.9 validation target

- three independent `100,000 + 10,000` dashboard-egress saturation runs;
- 2,000 durable frames plus exact release;
- exact EXIT/RESUME, stale-frame, prefix/suffix/wrapper, concurrency and session-binding anti-regressions;
- presented-digest handoff and completed-orientation accounting anti-regressions;
- full repository regression and inherited chat/psyche/incarnate gates on the same merge head.

See `IKANT_ACCESS_CONTRACT.md`, `AGENTS.md`, `docs/DASHBOARD_EGRESS_V09.md` and `docs/V09_DOD.md`.
