# S10bis hotfix5 — interactive liveness pre-product

## Runtime evidence

The managed LLM bootstrap is already healthy and reaches 7/7 READY. The next concrete product failure was human-visible: pressing Voice could activate and immediately deactivate the microphone, a submitted turn could appear inert, the primary iKant message could fail to appear, and the UI exposed no useful causal runtime diagnostics.

This is not a model-bootstrap defect. It is an interaction-liveness defect across browser capability negotiation, HTTP error transport, shell recovery and progressive human feedback.

## Causal findings

1. The native speech path treated `SpeechRecognition.start()` as a successful terminal capability decision. A later `onerror` / `onend` only cleared the button; it did not fall back and did not tell the user what happened.
2. ACTIVE shell and voice failures could return HTTP 409 with an empty JSON body. The browser attempted `response.json()` anyway, turning the useful HTTP status into a `SyntaxError`; catch blocks then discarded that error.
3. TURN and voice handlers used silent `_e` catches, so transport recovery could fail without a human message or diagnostic event.
4. Loopback STT is optional. When it is not configured the product must not prompt for a microphone recording it cannot transcribe.
5. Browser speech recognition is not a portable local guarantee. On-device recognition is accepted only when `processLocally`, `available()` and the required language-pack state are explicitly attestable. Vendor-prefixed recognition is never used as a remote fallback.
6. MediaRecorder containers differ across browsers. The client must negotiate a recorder MIME type that the local STT broker already accepts rather than assuming WebM.
7. Local TTS voices can appear asynchronously. `voiceschanged` must close the race instead of treating an initially empty `getVoices()` list as permanent.
8. User edits during dictation/recording must win. A late speech result may not overwrite text the human changed after voice capture began.
9. A slow but healthy local model needs liveness signals. PENDING remains the only primary chat state, while 4 s / 20 s watchdog events and concise composer hints expose progress through progressive disclosure.

## Web-mined edge families

The implementation was cross-checked against current browser documentation and upstream behavior:

- MDN documents Web Speech recognition as limited availability and normally server-backed unless `processLocally=true`; on-device mode requires `SpeechRecognition.available()` and possibly `install()` language packs.
- MDN explicitly notes that the on-device implementation does not require the legacy vendor-prefix handling used by older server-backed examples.
- MediaRecorder provides `isTypeSupported()` for container negotiation. WebKit historically emitted MP4 and newer Safari versions additionally support WebM/Opus.
- `SpeechSynthesisVoice.localService` distinguishes local from remote voices; `voiceschanged` reports asynchronous voice-list changes.
- WebKit has documented audio-capture failure modes where a browser reload can be required after an iOS media-service reset, so recovery guidance is explicit instead of silent.
- `whisper.cpp` was evaluated as a future managed loopback STT fallback. Its local server exposes multipart `/inference`, but upstream explicitly recommends sandboxing and upload validation. It is intentionally not added to this hotfix without its own pinned supply-chain proof.

## Minimal runtime reticulum

Text path:

`human text -> immediate PENDING -> one idempotent S8 TURN -> local model/fallback -> sealed HSPv2 frame -> primary Surface A projection -> exact ACK -> visible iKant reply`

Failure path:

`browser/server failure -> bounded structured transport diagnostic -> browser liveness ring -> concise human hint -> shell recovery -> response or explicit blocked state`

Voice path:

`Voice -> attest on-device recognition OR configured loopback STT -> explicit transcript candidate -> human presses Send -> exact same text TURN -> visible Surface A -> optional post-ACK localService TTS`

Voice remains input observation only. It never auto-submits and never creates approval, capability, grant, lease, evidence or execution authority. No remote speech recognition is silently substituted for a missing local capability.

## Runtime changes

- empty/non-JSON HTTP error bodies no longer destroy the real HTTP status;
- semantic 4xx failures are not blindly retried; retry remains bounded to transport/transient classes;
- `/api/v2/shell/*` and `/api/v3/voice/transcribe` return bounded/redacted zero-authority diagnostics on failure;
- browser runtime events are bounded to 48 entries and rendered only under System/Voice progressive disclosure;
- TURN displays exact PENDING immediately and emits 4 s / 20 s liveness watchdog events while waiting;
- on-device speech checks availability, install state and post-install readiness;
- `webkitSpeechRecognition` is not accepted as an unverified remote-capable fallback;
- loopback recording starts only when STT is configured;
- MediaRecorder negotiates `audio/webm`, `audio/mp4` or `audio/ogg` variants already accepted by the broker;
- microphone/device/recorder/transcription errors become visible, typed events;
- late voice results cannot overwrite a composer edited after capture began;
- TTS remains post-ACK and `localService===true`; asynchronous local voices are handled with `voiceschanged`;
- service-worker cache namespace is bumped so the liveness controller cannot be hidden by the hotfix4 cache.

## Falsification

The final source-bound harness first checks 13 byte-level candidate gates. It then executes:

- 10,000,000 semantic interaction trajectories;
- 20,000,000 mutation trials (10M more than the preceding interaction matrix);
- 72 kill classes;
- minimum 277,777 hits and kills for every class;
- 0 baseline failures;
- 0 mutation survivors;
- 4,096 semantic signatures;
- M+1000 no-novelty tail with 0 novelty;
- epistemic/execution authority 0.0 / 0.0.

The first source-bound receipt run was rejected because the falsifier serialized a misspelled variable (`novel` vs `novelty`). Runtime code was not changed to make that run pass; the complete matrix was rerun after fixing the falsifier.

## Pre-product acceptance boundary

This hotfix makes interaction failure non-silent and makes the text round-trip deterministic at the UI/transport contract: a submitted non-empty turn produces immediate PENDING and then either a visible iKant frame or a visible causal blocked/recovery state.

Voice is deterministic and local-only, not universally available by fiat. It works when the browser can attest on-device recognition or when an explicit loopback STT endpoint is configured; otherwise the user receives a precise unavailable/recovery message instead of a dead microphone. A managed STT component is deliberately deferred until it can satisfy the same pinned, bounded, sandboxed supply-chain discipline as the LLM runtime.
