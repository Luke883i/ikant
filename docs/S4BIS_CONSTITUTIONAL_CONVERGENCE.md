# S4bis - v0.22 Constitutional Convergence

S4bis adds no new material authority. It makes the product constitution match the already-merged S1-S4 runtime.

## Canonical product boundary

`PRODUCT_CONTRACT.json` declares the materialized agency slices and their machine-test, stress, mutation and edge harnesses. `ikant.invariants` remains the canonical cross-cutting invariant registry. A future material slice is not constitutional merely because code exists: it must be registered in both surfaces and exercised by the version-neutral product boundary.

The preserved non-collapse chain is:

`evidence != permission != approval != grant != lease != execution != reported outcome/world truth`.

S1 HumanFrame presentation is not authorization. Grants are exact and session-bound. Leases are one-shot and handoff-bound. S2 model/voice/browser projections are zero-authority. S3 web content is hostile observation and execution requires host conformance plus a fresh S1 lease. S4 native filesystem execution remains workspace-bound and excludes overwrite/delete/process/shell/secrets.

## Product identity

Product version is `0.22.0a1`; repository access contract remains `0.12.0`. Historical subsystem schemas retain their own versions. Product version is not permission and does not alter the rightsholder contract.

## DevOps

`.github/workflows/product-boundary.yml` is deliberately version-neutral. It compiles the constitutional surface, verifies registry/manifests, runs the S4bis convergence tests and executes every S1-S4 registered stress/mutation/edge harness. Future slices extend `PRODUCT_CONTRACT.json` and the invariant registry rather than adding release-specific workflows.

PR gate uses 100k cases plus 10k tail for each registered harness over three seeds. A dedicated 100k no-novelty tail runs at seed 883. Larger release saturation may increase these numbers without changing the constitutional interface.

## DoD

- Product/version/README agree on v0.22.
- `ADMISSION.json` and `BOOTSTRAP.json` declare S1-S4 and the v0.22 registry.
- AGY/EMB/WEB/NAT invariants are CRITICAL and machine-tested.
- S1-S4 harnesses are discovered from one product contract.
- No S4bis code changes an execution commit point or expands capability scope.
- Existing v0.12 rights/admission and dashboard-only ACTIVE egress remain unchanged.
