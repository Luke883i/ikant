# Enterprise-Candidate Workbook v1 — repository handoff

This document binds the session artifact `iKant_Enterprise_Candidate_Workbook_v1.xlsx` to repository truth without committing the binary workbook itself.

## Evidence boundary

The workbook is a control/evidence artifact, not runtime proof. Repository/Git/CI facts outrank workbook snapshots. `REPO`, `PROPOSED`, `STANDARD`, `MODELED`, and `PHYSICAL_ORACLE` must remain distinct evidence classes. Modeled saturation and design-space enumeration never imply production reliability, standards compliance, browser/OS/provider execution, or enterprise readiness.

## Live state verified before this handoff

- `main` = `c46db91c968edbf2203a27de9f0f17de46c38108` (merged PR57 / S21).
- `PRODUCT_CONTRACT.json` converges constitutionally at S21, contract version `0.22.0`.
- no open pull requests were observed during this audit.
- `main` is not materially protected by branch protection/required checks.
- `IKANT_DEVELOPMENT_BUNDLE.json` is stale after PR57: it still describes merged PR56/S20 as baseline and S21 as a registered candidate.
- `ikant/surface_contract.py` still labels the canonical surface projection and asset revision as S20, and the existing Surface Contract test asserts S20.

These conflicts are repository-backed anti-entropy findings; they must be closed before capability expansion.

## Workbook architectural compression

The workbook proposes an enterprise-candidate target at S35. It uses one compression rule: create a distinct slice only when **authority, trust, persistence, or physical-oracle boundary changes**; otherwise fuse the work.

The proposed post-S21 lattice is:

`C0 anti-entropy -> G0 repository governance -> S22 enterprise context/policy -> S23 external trust/adapter supply -> {S24 provider assist, S25 connector fabric} -> S26 ingress quarantine -> S27 epistemic revision -> S28 enterprise authority/delegation -> S29 transaction -> S30 world reconciliation -> S31 native/multi-surface -> S32 enterprise audit -> S33 release/data lifecycle -> S34 fleet/software supply -> S35 assurance/E2E convergence`

C0 and G0 are gates rather than runtime faculties. S24 and S25 are commutable siblings after S23. All S22-S35 identifiers and meanings remain **PROPOSED** until constitutionally materialized and registered.

## Next minimum RLA unit: C0

Do not start S22 yet. First converge repository truth after merged S21.

C0 must:

1. advance the Development Bundle baseline from merged PR56/S20 to merged PR57/S21;
2. remove the false state in which S21 is represented as a registered-but-unmerged candidate;
3. make the bundle gate describe the next candidate rather than re-proving an already merged candidate;
4. update the canonical Surface Contract projection/asset lineage so it no longer claims S20 while the Product Contract is S21;
5. preserve single-writer, zero-authority surface semantics and all S16-S21 runtime invariants;
6. leave G0's GitHub ruleset enforcement as an explicit external/admin requirement rather than simulating protection in code.

The minimum acceptance surface is exact Git census + Development Bundle gate + existing Surface Contract unit/HTTP/browser regressions. C0 adds no user-facing capability and must not advance the Product Contract beyond S21.

## Next iteration after C0

Only after C0 is exact-green should the session decide whether G0 can be materially enforced with available repository administration rights. Runtime S22 must not be activated before the repository control plane is truthfully converged and the enterprise identity/policy boundary is specified against the real current code.
