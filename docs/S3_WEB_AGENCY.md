# S3 Web Agency

S3 adds the minimal isolated-web sensor/actuator boundary on top of merged S1 Agency Kernel and S2 Local Embodiment. It does not create a new authorization path.

## Semantic chain

`WebSnapshot -> WebAction -> handoff-bound S1 HumanFrame/Grant -> S1 ExecutionLease -> v0.18 host revalidation -> browser commit -> v0.17 execution receipt`

Every arrow is conjunctive. Web content, a model proposal, a browser capability or a successful host-conformance probe never implies authority to perform the next step.

## WebSnapshot

A snapshot is a bounded observation from one browser/page/navigation epoch. Page text and labels are always untrusted. Cookies, storage and secrets are excluded. Control IDs are reconstructed from canonical control fields during validation; recomputing only the outer snapshot digest cannot retarget an existing control ID.

## WebAction

S3 supports only three effects:

- `NAVIGATE`: one exact canonical HTTP(S) URL;
- `CLICK`: only an explicit `<a href=http(s)>` already present in the exact snapshot; S3 follows the sealed href instead of firing arbitrary page handlers;
- `FILL`: only ordinary `input`/`textarea`; password, file and side-effecting input types are excluded.

No selector, XPath, arbitrary JavaScript, form submission, download, password-manager or filesystem surface exists in S3.

The S1 entitlement is not merely `(web capability, page resource)`. It is bound to the exact WebAction digest plus v0.17 `handoff_id`, action fingerprint and idempotency key. Handoff drift therefore changes the entitlement and invalidates the lease.

## Browser capability sandbox

The optional Playwright context starts at `about:blank` with no startup network request. It is created with page JavaScript disabled, Service Workers blocked and downloads disabled. WebSockets are rejected when supported by the installed Playwright runtime. Extra pages are closed. A deny-by-default request route allows only GET/HEAD during an authorized navigation commit, only on authorized origins, and only the exact top-level destination. Redirects away from the authorized URL, child-frame navigation and non-http(s) requests fail closed. Network is disabled again immediately after the commit.

These restrictions intentionally trade compatibility for a small falsifiable effect surface. Rich scripted sites, form submits, authenticated secrets and attached-human-browser control remain deferred.

## Commit point

`snapshot recheck -> browser preflight -> S1 lease + v0.18 host revalidation -> snapshot recheck -> consume one-shot lease -> external browser commit`

A browser failure after lease consumption records FAILED and does not silently retry. Retry requires fresh authorization. Execution receipts remain control observations with zero epistemic authority and do not establish world truth.

## DOD

S3 is complete only when:

- web content cannot create/extend/revoke/approve authority;
- control retargeting, snapshot drift and navigation epoch drift fail closed;
- the S1 resource binds exact WebAction + exact v0.17 handoff identity;
- browser construction performs no material network action;
- page JS, Service Workers, WebSockets, downloads, extra pages and arbitrary HTTP methods cannot become side channels;
- CLICK cannot execute page handlers or buttons/forms;
- sensitive FILL targets are rejected;
- lease is consumed once at the external commit point and never silently replayed;
- targeted unit/integration tests pass;
- 100,000 stress + 10,000 tail reaches no novelty after explicit-state saturation;
- 100,000 edge + 10,000 tail reaches no novelty;
- 100,000 mutation instances + 10,000 tail cover all mutation families with zero survivors;
- Hosted CI and Reticular CI both PASS on the same current synthetic merge head.

S3 does not yet add an attached-browser extension, native OS agency, scheduler/autonomy, credential handling, arbitrary JavaScript, POST/form submission, downloads or background acquisition.
