# iKant v0.4-test Definition of Done

A v0.4 candidate may be proposed only when all of the following are true.

## Functional

- `> iKant:` is rendered as shell chrome outside Surface A.
- Visible chat is persisted locally and bound to one runtime session.
- Transcript reopen verifies contiguous sequence, predecessor hash, record digest and reply linkage.
- One user record has at most one iKant reply.
- Pending Surface A blocks a new chat input before transcript append.
- Dashboard JSON/TXT is produced from runtime + latest Surface B and remains read-only.
- DOCX backlog projection is bounded and explicitly non-evidential.
- Reset semantics continue to delete all `.ikant/` chat/dashboard state.

## Safety / epistemic

- No private chain-of-thought is persisted.
- Dashboard and backlog signals cannot alter evidence, central authority or action authorization.
- Missing/corrupt telemetry never becomes a healthy/fabricated state.
- Terminal control/bidi/prompt spoof inputs cannot impersonate shell identity when rendered.
- Symlink, malformed ZIP/XML, oversize DOCX and entity/DTD inputs fail boundedly.

## Validation

- Unit + negative controls pass.
- Existing v0.3 interaction tests remain green.
- Real host/runtime chat integration passes under durable reopen.
- At least 10,000 executable session-chat cases pass.
- Scenario-signature saturation is observed and a no-novelty tail adds zero genuine failure classes.
- Dashboard fixture is visually inspected at normal terminal width.
- v0.4 DOCX runtime overview renders cleanly on every page.
- Full hosted repository CI passes on the exact PR head before release readiness.

## Confidence language

The >95% confidence threshold is an engineering confidence judgment over tested invariants and scenario coverage. It is not a statistical proof, neuroscientific confidence interval or claim that all possible host/user interactions have been enumerated.
