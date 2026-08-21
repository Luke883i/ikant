# S10bis hotfix2 — runtime wiring correction

A post-merge bootstrap journal proved that the original hotfix2 kernel was not wired into the canonical process path. `ENGINE_PROCESS_RUNNING -> ENGINE_READINESS_WAIT -> ENGINE_EXITED_EARLY` still ended with only `ManagedRuntimeError -> EngineSupervisorError`, with no return code, signal, or stderr evidence.

## Concrete survivors

Two real journals are the seed cases. The first process died about 8.165 s after readiness wait began; the second about 6.031 s later. Both verified the engine and model first and both discarded all OS-level exit evidence. This falsifies kernel-only convergence.

The runtime losses were independent: `EngineSupervisor` sent stderr to `DEVNULL` and called `stop()` before constructing the early-exit error; `bootstrap_observability` then reduced every cause entry to `type/message`, discarding structured attributes even if a supervisor supplied them.

## Minimal runtime lattice

`Popen(stderr=PIPE) -> concurrent bounded drain -> poll detects death -> EngineExitDiagnostic -> EngineSupervisorError.process_exit -> ManagedRuntime __cause__ -> exception_chain -> hash-chained journal -> status/UI diagnostics`

The collector retains at most 64 KiB raw stderr and publishes at most 4096 UTF-8 bytes after redaction. Return status and POSIX signal are recorded only as directly observed/mechanically derived facts. Stderr text never changes the stable failure code and creates no epistemic or execution authority.

## Falsification

Executable validation used 17 concrete OS process fixtures plus the two real-journal shapes. Fixtures cover exit statuses including 126/127/137, SIGTERM/SIGKILL, malformed UTF-8, credentials, and stderr larger than pipe/capture bounds.

A first 10,000,000-trajectory e2e matrix found one survivor: `DROP_STDERR`. The invariant checked bounds and redaction but did not require preservation of an emitted tail. The invariant was strengthened to exact bounded/redacted-tail preservation and the full matrix was rerun against the final candidate.

Final receipt: 10,000,000 trajectories, 32/32 mutant classes killed, minimum 13,141 kills per mutant, zero baseline failures, zero survivors, 48 semantic signatures, and +1,000 tail cases with zero novelty.

## Boundary

This remains S10bis hotfix2 corrective work, not S11. It adds no retry authority, no new product surface, no semantic stderr classifier, and no new evidence source. The goal is narrower: when the local engine dies, preserve enough bounded zero-authority process evidence to diagnose the actual cause rather than merely locating the failing gate.
