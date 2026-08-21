# S10bis — Bootstrap Transparency / Runtime Observability

S10bis makes the local bootstrap causally observable without creating a new authority path or semantic surface.

Canonical journey:

`WEB_APP -> MANIFEST -> ENGINE_COMPONENT -> MODEL_COMPONENT -> ENGINE_PROCESS -> ENGINE_READINESS -> PRODUCT_SERVICE -> READY`

Every required gate emits durable `START/PROGRESS/PASS/FAIL` evidence before or at the side-effect boundary that can fail. Component cache checks emit pre-side-effect markers, engine process spawn is typed, and readiness is separated from process start.

The canonical raw evidence is `.ikant/bootstrap-events.jsonl`, bounded to 8 MiB for the current raw file, with <=16 KiB events, <=6 cause entries, SHA-256 previous-event chaining, bounded rotations and credential/query redaction. Retries use new attempt identifiers and never rewrite prior attempts.

The local web product deterministically compresses the same evidence chain into seven user-facing gates with exact failure code, cause and remediation. Authenticated `/api/v5/bootstrap/status`, `/events` and `/raw` are GET-only diagnostics. The existing S9 retry action remains the sole setup mutation path.

`diagnostic presentation != evidence != permission != approval != grant != lease != execution != world truth`

S10bis adds `BOS-001..004` and registers 10M stress + 10M semantic mutations + 10M edge cases +1000 no-novelty, with exhaustive 1,048,576-architecture minimality. The minimum has 14 required features and one accepted architecture.
