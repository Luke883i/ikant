# v0.6 Admission Firewall DoD

DoD closes only when all are true on the same PR merge head:

- contract/frontmatter declares default DENY and sole terms-envelope exception;
- BOOTSTRAP/ADMISSION contain no legacy pre-admission allowlist and match executable firewall policy;
- `probe` reports `ADMISSION_POLICY=AVAILABLE` for a valid checkout and `BLOCKED` for policy drift;
- unit/edge/role/session/variant/breach tests pass;
- mutation suite kills normalization, embedded acceptance, README/metadata/history pre-read, clone-on-discovery and retroactive-cure mutants;
- five seeds each pass 10,000 stateful hostile admission sessions plus 10,000 no-novelty tail sessions with zero policy violations and zero new tail signatures;
- full repository regression suite passes;
- repository-wide hosted CI is PASS;
- dedicated `ADMISSION_V06_CI` receipt is PASS on the same merge head.
