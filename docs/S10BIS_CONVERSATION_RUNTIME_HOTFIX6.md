# S10bis hotfix6 — structured conversation projection, fast local inference, voiced round-trip

## Real survivor

The post-PR38 screenshot proved that model generation and HSPv2 validation could succeed while the primary chat still displayed the static PENDING marker. The canonical frame contained a validated reply such as `Ciao! How can I help you today?`, but `primary_text` remained pending.

The cause is a layering collision. `ChatLog` intentionally sanitizes terminal-looking lines by rendering a legitimate `> iKant:` line as `[prompt-like text] > iKant:`. The old web projection then reparsed the ASCII dashboard and accepted only cells beginning exactly with `> iKant:`. A validated reply was therefore made invisible by one safety layer and then misclassified by the next.

## Minimal correction

The normal live TURN no longer derives semantic output by parsing ASCII presentation.

`validated Surface A -> ChatLog/hash-chain -> HSPv2 canonical disclosure`

and independently:

`validated Surface A -> structured zero-authority primary_text -> primary chat -> post-ACK local TTS`

The HSPv2 frame remains canonical for exact ACK and progressive disclosure. ASCII parsing is compatibility-only. Crash/reload recovery obtains the iKant reply from the verified ChatLog row bound to the receipt cycle id. A compatibility parser recognizes the historical `[prompt-like text] > iKant:` form so already-sealed frames can recover.

## Latency finding

A GitHub-hosted Ubuntu 22.04 benchmark used the exact pinned llama.cpp b10344 CPU artifact and exact Qwen3.5-0.8B-Q4_0 model. Moving the single-writer product to `--ctx-size 4096 --parallel 1 --cache-prompt` reduced measured startup from 3737.7 ms to 1515.8 ms and mean short-turn server latency from 744.4 ms to 700.1 ms. This proves the server profile is useful, especially for startup, but also proves that severe user-visible delay is not explained by llama-server alone.

Hotfix6 therefore also removes the redundant per-turn `/v1/models` health request, compresses the generation contract before sending it to the 0.8B model, caps a turn to one repair, reduces the prediction budget, and emits bounded per-generation timing/token telemetry. It does not stream raw model tokens to the human: validation remains before Surface A egress.

## Voice design

The voice circuit remains authority-equivalent to typed input:

`local speech capability -> transcript candidate -> explicit human Send -> same TURN -> validated structured Surface A -> exact ACK -> localService TTS`

The browser path requires on-device SpeechRecognition when available and never silently falls back to prefixed potentially remote recognition. Recorder fallback remains a configured loopback STT endpoint. TTS remains post-ACK and requires a browser voice declared `localService=true`.

External comparison found the same architectural split in Open WebUI: browser speech is one frontend option while local Whisper is a backend STT option. whisper.cpp is a strong future managed-STT candidate, but official releases still do not provide the same pinned Linux binary supply chain as llama.cpp; upstream users explicitly request such Linux binaries. Hotfix6 therefore does not import an unproved third-party speech binary merely to make the microphone appear functional.

## Falsification

The hotfix6 lattice covers structured projection, cycle recovery, hash-chain preservation, compatibility parsing, canonical exact ACK, language intent, server bounds, compact prompt, repair budget, local-only voice, transcript-to-same-TURN binding, post-ACK local TTS, immediate PENDING, explicit failure and runtime diagnostics.

The executed matrix contains 10,000,000 trajectories / mutation trials across 64 kill classes. All 64 classes are killed, minimum 156,250 instances per class, zero baseline failures, zero survivors and M+1000 novelty zero. The reproducible harness additionally fails unless the candidate source contains the required runtime bindings.

## Boundary

This slice improves text interaction deterministically. Voice input is deterministic only when an attested browser-local recognizer or explicitly configured loopback STT exists. A truly portable managed voice input is a separate supply-chain component and must receive the same pin/digest/sandbox/readiness treatment as the LLM runtime before it can be called guaranteed.
