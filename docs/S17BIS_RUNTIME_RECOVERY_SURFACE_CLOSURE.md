# S17bis — Runtime Recovery & Surface Closure

S17bis adds no new user faculty. It closes restart and semantic-surface ambiguity before durable cognitive state is allowed to grow.

The canonical recovery inputs are existing durable runtime/session and epoch state, the append-only egress journal plus pending frame, and already-validated Surface A/chat state. `WorkStore`, `AdvancedWebShellController` sequencing and the Surface stable cache remain process-local derivatives; none becomes a second durable runtime.

A restart has three recoverable delivery classes. An already-sealed frame is replayed byte-identically. A TURN interrupted before validated Surface A produces a zero-authority `RECOVERY` frame and the pending cognitive marker is removed only after exact ACK. A validated Surface A interrupted before frame sealing is reconstructed from verified chat or its validated zero-evidence RESPONSE node; one missing chat reply may be reconciled, but a second RESPONSE may never be created. Contradictory or unverifiable state fails closed.

Recovery never invokes the model, cognitive planner or material driver. It grants no authority. The browser may replace its ephemeral shell writer and begin with `SYNC`; canonical continuity comes from the durable egress/frame protocol, not persisted browser sequencing.

S17bis also independently censuses production HTTP routes, composed assets and DOM controls without using the declarative Surface manifest as its source of truth. Lifecycle projection explicitly distinguishes `PRE_ACTIVE_BOOTSTRAP`, `RECOVERY_REQUIRED` and `ACTIVE_CANONICAL`.

## Falsification boundary

The S17bis modeled harness uses a seed-bound modular permutation to cover the finite 12,288-signature semantic lattice, while SplitMix64 continues to randomize simultaneous 2–4 fault co-occurrence and domain pairing. This separates two concerns that were previously conflated: finite vocabulary coverage is deterministic and reproducible; interaction pressure remains randomized.

At the declared 10,000,000-case scale with seed `5106034144745002672`, all 12,288 semantic signatures and all 78 unordered domain pairs are covered, family hits are 104,166–104,167, and the 100,000-case tail observes zero new signatures. Because one full lattice cycle is sufficient for vocabulary coverage, the version-neutral Product Boundary can also truthfully test no-novelty at its smaller registered-slice scale instead of depending on coupon-collector luck.

This is declared-vocabulary saturation only. It is not a production reliability estimate, formal verification, process execution evidence or browser execution evidence. Repository CI separately executes real subprocess restart, exact-frame recovery, independent source census and real Chromium recovery/DOM census.

## Promotion state

`main` remains constitutionally S17 until PR54 is merged. The PR branch is a `REGISTERED_CANDIDATE`: its Product Contract registers S17bis and exercises its machine test plus stress/mutation/edge harnesses, but that branch-level constitutional registration is not evidence that main has already advanced.

S17bis is merge-ready only when one exact synthetic merge proves full-unit, Hosted, Reticular, Product Boundary and physical recovery/browser gates without weakening T&C, exact ACK, runtime provenance or zero-authority boundaries.
