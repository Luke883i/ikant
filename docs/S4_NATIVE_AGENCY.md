# S4 Native Agency

S4 introduces the minimum local-native sensor/actuator boundary on top of merged S1 Agency Kernel, S2 Local Embodiment and S3 Web Agency. It does not create a second authorization path.

## Semantic chain

`NativeTargetSnapshot -> NativeAction -> handoff-bound S1 HumanFrame/Grant -> S1 one-shot ExecutionLease -> v0.18 host revalidation -> native filesystem commit -> v0.17 execution receipt`

Every edge is conjunctive. A local path, model proposal, host capability or readable file does not create authority.

## Deliberate effect surface

S4 supports exactly two material filesystem capabilities:

- `native.fs.read`: read one existing regular UTF-8 text file from one configured workspace;
- `native.fs.create`: create one previously absent UTF-8 text file with exact human-visible content, bounded to 16 KiB.

S4 deliberately does **not** expose generic file replacement, delete, rename, chmod, arbitrary process execution, shell commands, inherited environments, app launch, credentials, secret stores, device access or filesystem-root scopes.

Generic process execution was rejected during falsification because an arbitrary child process inherits the ambient OS authority of the user and would collapse granular S1 capability semantics into a de facto god-mode. Existing-file replacement was also rejected: portable POSIX primitives cannot provide a path-level compare-and-swap that proves the target inode did not change in the final check-to-rename interval. Those effects require a later OS-specific sandbox/CAS adapter rather than weaker semantics in S4.

## Path and workspace binding

Native paths use a canonical workspace-relative POSIX form. Absolute paths, backslashes, drive prefixes, empty/dot/traversal components and control bytes fail closed. Hidden/known credential/key/token paths are excluded from the generic file capability and require a future dedicated secret capability.

The reference real driver is `PosixWorkspaceAdapter`. It requires `dir_fd` plus `O_NOFOLLOW`, rejects filesystem root as a workspace, opens each parent directory component without following symlinks and seals the workspace-root fingerprint, parent stat identity and leaf stat identity into `NativeTargetSnapshot`. Platforms that cannot demonstrate equivalent strong binding fail closed instead of falling back to string `resolve()` logic.

## READ commit

READ opens the exact leaf with `O_NOFOLLOW`, verifies its device/inode/mode/size/mtime identity, reads at most 128 KiB, rechecks identity after the read, requires exact size consistency and UTF-8 decoding, and returns content only as an `UNTRUSTED` native observation. Native content has epistemic authority `0.0`; it may contain adversarial instructions and never grants authority.

## CREATE commit

CREATE is absent-target only. The exact plaintext is present in the authorization HumanFrame and its SHA-256 is action-bound. The driver writes and fsyncs a hidden temporary file, then uses an atomic hard-link into the authorized absent target. The link operation refuses to clobber a target created concurrently. The temporary file is removed on success or failure, and the parent directory is fsynced after publication.

## Admission and commit point

`build_native_agency_runtime(..., active=True)` must receive ACTIVE explicitly. With `active=False` it fails before constructing the filesystem driver or opening the workspace.

The execution sequence is:

`snapshot recheck -> native preflight -> exact S1 lease + v0.18 host revalidation -> snapshot recheck -> consume one-shot lease -> native commit`

Failure after lease consumption records FAILED and requires fresh authority for retry. No recovery path auto-executes a pending native action.

## Falsification findings closed

- symlink leaf/parent escape;
- absolute/traversal/drive/backslash path confusion;
- filesystem root configured as a workspace;
- workspace identity missing from an otherwise exact relative-path action;
- stale leaf or parent identity reuse;
- target swap between preflight and READ;
- READ mutation during I/O;
- CREATE clobber race;
- partial temp-file leakage;
- binary/unbounded create content that cannot be human reviewed;
- generic secret/key/token path inheritance;
- process/shell/environment escalation;
- pre-admission construction touching an arbitrary workspace;
- handoff/fingerprint/idempotency drift reusing a native grant.

## Saturation

Final pre-publication candidate:

- targeted local boundary tests: 22/22 PASS; repository integration adds S1/v0.18/v0.17/admission tests;
- semantic stress: 100,000 + 10,000 tail, all 65,536 explicit configurations covered, 9 consequence signatures, 0 violations, 0 tail novelty;
- edge saturation: 100,000 + 10,000 tail, all 32,768 explicit configurations covered, 408 signatures, 0 violations, 0 tail novelty;
- semantic/adversarial mutation campaign: 100,000 + 10,000 tail, 106/106 families covered, 0 survivors, 0 tail-new families.

These are executable semantic/adversarial campaigns, not formal verification and not a claim of resistance to a kernel-compromised or same-user malicious process that can mutate filesystem namespace outside iKant's trust boundary.
