# S10bis runtime compatibility corrective slice

## Observed failure

After causal engine-exit diagnostics were wired end-to-end, the real bootstrap failure became observable instead of generic. The pinned Linux x86_64 OpenVINO build of llama.cpp b10344 aborted with signal 6 while loading the pinned Qwen3.5-0.8B-Q4_0 model. The captured stderr identifies the failing boundary as a pre-allocated `cache_r_l0` tensor in `OPENVINO0` that cannot execute `CPY`.

This is not inferred from timing or a generic exit code. It is direct process evidence preserved by the S10bis journal.

## External evidence

The failure shape matches upstream llama.cpp issue #20562, where Qwen3.5 fails on the OpenVINO CPU backend with the same `cache_r_l0` / `OPENVINO0` / `CPY` abort. Issue #20619 reports the same operation failure on OpenVINO GPU. The upstream release workflow builds Ubuntu x64 CPU separately from OpenVINO, with `GGML_BACKEND_DL=ON`, `GGML_NATIVE=OFF` and `GGML_CPU_ALL_VARIANTS=ON` for the CPU artifact.

Evidence references:

- `ggml-org/llama.cpp#20562` — Qwen3.5 cannot load on OpenVINO CPU.
- `ggml-org/llama.cpp#20619` — OpenVINO `CPY` failure on Qwen3.5.
- `ggml-org/llama.cpp#22333` — later OpenVINO llama-server abort with the same copy boundary.
- `ggml-org/llama.cpp/.github/workflows/release.yml` — distinct Ubuntu x64 CPU and OpenVINO artifacts.

## Minimal reticulum

The corrective lattice is deliberately narrow:

`platform linux-x86_64 -> exact b10344 CPU artifact -> artifact SHA verification -> archive topology verification -> install marker artifact binding -> exact Qwen3.5 model digest -> llama-server spawn -> loopback readiness probe -> READY`

There is no runtime accelerator fallback. iKant does not try OpenVINO, Vulkan or SYCL and then silently choose whichever starts. Backend compatibility remains a pinned supply-chain decision and READY still requires the existing real loopback probe.

The existing `ModelManager` already invalidates a cached engine when `.ikant-install.json.artifact_sha256` differs from the current artifact SHA and verifies the installed tree digest. Therefore changing the Linux x86_64 artifact digest is sufficient to prevent reuse of the old OpenVINO installation; no new cache identity mechanism is needed.

## Hosted executable proof

A GitHub-hosted `ubuntu-22.04` runner downloaded the official b10344 Ubuntu x64 CPU asset and the exact pinned GGUF, then used iKant `safe_extract_tar`, found the unique regular `llama-server`, launched it with the production host/API-key/no-webui contract, and probed `/v1/models`.

Observed receipt:

- engine asset: `llama-b10344-bin-ubuntu-x64.tar.gz`;
- engine SHA-256: `01b90b0764821d0e53b985730eea3837e29a976ee00e783e18837937b93fc3f1`;
- engine size: 16,512,385 bytes;
- installed tree SHA-256: `3ca1b97cb59865453b0d675c47c44d6a23605b8b7e429946a77898c1f7d5804c`;
- model SHA-256: `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`;
- model size: 563,036,064 bytes;
- `/v1/models`: READY;
- process still alive before cleanup;
- authority: 0.0 / 0.0.

The raw proof is committed in `backlog/runtime_compat_proof_b10344_qwen35.json`.

## Falsification

The first 10,000,000-trajectory model was rejected because its M+1000 tail used a different edge-activation grammar and produced 123 apparent new signatures. The falsifier was corrected so M and tail share the exact same edge grammar; the runtime candidate was not relaxed.

The converged rerun executes 10,000,000 trajectories and 10,000,000 mutation trials over 48 mutation classes derived from the real failure and the managed-runtime boundaries. Results: zero baseline failures, zero survivors, every class killed in every applicable trial, minimum 208,333 kills per mutant, 2,300 semantic signatures, and +1,000 no-novelty tail with zero novelty.

Killed families include reintroducing OpenVINO, changing only the OpenVINO device to CPU, floating release tags, digest drift, stale OpenVINO cache reuse, install/tree digest bypass, archive topology escapes, wrong architecture selection, dynamic accelerator fallback, false readiness from component/spawn/browser state, model drift, exit-evidence loss, retry history rewriting, authority escalation and non-pinned mirrors.

## Boundary

This slice does not claim CPU can never fail on another host. It proves that the exact candidate works on the hosted Linux x86_64 proof environment and removes the known-incompatible OpenVINO combination from the pinned manifest. Every real host still reaches READY only through the existing loopback readiness gate. Component presence, diagnostics and runtime readiness remain zero-authority observations.
