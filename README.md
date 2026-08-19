# iKant v0.11-test

iKant is a repository-local reticular cognitive runtime for conforming AI session-chat hosts. v0.11 is a consolidation release: it does not add a new cognitive faculty; it closes the holistic audit by hardening transport/egress integrity and reducing version archaeology in the canonical runtime path.

After digest-bound `I ACCEPT`, `PROBE` and `INITIALIZE`, the human channel remains dashboard-only. The egress guard is now non-recreatable after activation: deletion/loss fails closed. Recovery from `EGRESS_BREACHED` requires runtime integrity plus a host/transport attestation. ACTIVE machine JSON is file-only and may not use stdout/stderr.

Canonical execution is `python -m ikant`; the entrypoint is `ikant.app_cli:main`. Current cognitive, host and human-dashboard orchestration use version-neutral modules. Historical version modules remain thin compatibility shims so old tests/imports continue to work without retaining duplicate runtime logic.

The invariant registry lives in `ikant/invariants.py`. Release validation uses repository-wide CI plus one reticular boundary workflow. The v0.11 DoD requires M=100,000 behavioral scenarios plus M+10,000 no-novelty on independent seeds, and an exhaustive N=32,768 architecture-compression lattice plus N+10,000 no-better-compression tail.

See `IKANT_ACCESS_CONTRACT.md` and `docs/RETICULAR_CONSOLIDATION_V11.md`.
