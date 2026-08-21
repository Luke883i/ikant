# S10bis hotfix2 — causal engine-exit diagnostics

A real S10bis bootstrap journal reaches `ENGINE_PROCESS` and then fails at `ENGINE_READINESS` with `ENGINE_EXITED_EARLY`, but the causal chain preserves only the generic supervisor message. Return status, termination signal, and bounded stderr evidence are lost, so distinct process failures collapse to the same remediation.

Hotfix2 introduces a zero-authority `EngineExitDiagnostic` kernel. It records only directly observable process facts: `EXIT_STATUS`, `SIGNAL`, or `UNKNOWN`; the raw return code; a signal only when derivable from a negative return code; and a redacted stderr tail bounded to 4096 encoded UTF-8 bytes. It deliberately does not infer semantic causes such as OOM, OpenVINO failure, loader incompatibility, or invalid CLI flags from stderr text.

The target runtime composition is:

`engine process -> observed exit facts -> bounded/redacted EngineExitDiagnostic -> EngineSupervisorError -> bootstrap cause_chain -> raw journal/status projection`

The diagnostic has epistemic authority `0.0` and execution authority `0.0`; it does not alter S5 execution authority, S9 retry authority, S10 read-only projection, or READY semantics.

The executable falsifier runs 10,000 simulations, 10,000 semantic mutations, 10,000 kill cases, and a 1,000-case no-novelty tail. The converged model has zero mutation survivors, zero kill survivors, and zero tail novelty. A first model was rejected because malformed UTF-8 could expand under replacement decoding and violate the byte bound; the final kernel truncates after redaction at the encoded-byte layer and decodes the final tail with `errors="ignore"`.
