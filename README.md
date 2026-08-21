# iKant v0.29-test

iKant is a governed local epistemic agent runtime. Product v0.29 preserves S1-S10 and adds **S10bis Bootstrap Transparency / Runtime Observability** before the deliberative S11 work.

## S10bis bootstrap contract

`./ikant.sh` serves the local product first, then exposes one auditable bootstrap journey:

`WEB_APP -> MANIFEST -> ENGINE_COMPONENT -> MODEL_COMPONENT -> ENGINE_PROCESS -> ENGINE_READINESS -> PRODUCT_SERVICE -> READY`

Every failing side-effect boundary is preceded by a causal marker. The raw source is the bounded, SHA-256 chained `.ikant/bootstrap-events.jsonl`; the landing page compresses the same evidence into success/failure/progress gates with stable error codes and remediation. No bootstrap diagnostic has epistemic or execution authority, no browser state can manufacture READY, and `/api/v5/bootstrap/*` remains authenticated GET-only diagnostics. Retry remains the existing S9 setup mutation path.

The v0.12 access contract and same-session chat-study erratum remain unchanged. Official local iKant still requires clean admission plus technical conformance; S10bis observes that path but does not weaken it.

`diagnostics != evidence != permission != approval != grant != lease != execution != world truth`

S10bis is registered with `BOS-001..004`, 10M stress, 10M semantic mutations, 10M edges, +1000 no-novelty and exhaustive 1,048,576-architecture minimality. See `docs/S10BIS_BOOTSTRAP_OBSERVABILITY.md`.
