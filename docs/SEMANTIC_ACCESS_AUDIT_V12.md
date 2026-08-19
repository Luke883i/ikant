# iKant v0.12 semantic-access audit

Date: 19 August 2026. Scope: product architecture, owner authorization, public-repository access, TDM/AI rights signals and iKant conformance. This is an engineering/legal-context audit, not legal advice.

## External normative findings

1. **EU TDM reservation is real but scoped.** Article 4(3) of Directive (EU) 2019/790 allows rightsholders to reserve TDM rights; Italy implemented the general TDM rule in Article 70-quater L. 633/1941. For publicly available online content, EU materials emphasize appropriate machine-readable reservation. The reservation concerns copyright/TDM acts, not ownership of abstract "inferences".
2. **GPAI providers have a copyright-compliance duty.** Article 53(1)(c) of Regulation (EU) 2024/1689 requires GPAI providers to maintain a Union-copyright compliance policy, in particular to identify and comply with Article 4(3) reservations. Recitals 105–106 connect this directly to TDM used in model development.
3. **No single opt-out protocol is final or exclusive as of this audit.** The European Commission's 2025–2026 process is identifying generally agreed machine-readable protocols. Rightsholders remain responsible for an appropriate reservation; candidates include robots.txt, TDMRep and other protocols.
4. **A GitHub repository cannot control the GitHub origin.** Repository files cannot set `github.com/robots.txt`, HTTP response headers or `github.com/.well-known/tdmrep.json`. iKant therefore uses a repository-level machine-readable policy and recommends an additional origin-level signal where the rightsholder controls the serving origin.
5. **GitHub public visibility carries direct platform licences.** Current GitHub Terms grant GitHub/Affiliates and other GitHub users specific platform rights. Repository-owner terms must not pretend to revoke direct grants made through the platform contract.
6. **Software-specific mandatory rules matter.** Directive 2009/24/EC Article 5(3) protects certain observation/study/testing by a person entitled to use a program. iKant therefore does not classify every external study as unlawful; it classifies only the owner's affirmative permission and technical conformance.
7. **Scientific-research TDM remains a distinct exception regime.** The iKant owner policy does not collapse it into the general opt-out rule; claims of such a basis are marked external/not-adjudicated.

## Product defect in v0.11

v0.11 correctly hardened admission and transport, but still compressed three distinct questions into one lifecycle: whether the host may materialize after acceptance, whether the owner has authorized substantive AI study, and whether the resulting experience is official/conforming iKant. That compression allowed an over-broad interpretation in which acceptance opened repository capability even when the host could never satisfy official transport semantics, and left model training/external legal bases underspecified.

## v0.12 model

The product now uses a rights-control slice with **zero epistemic authority**.

| Capability | Owner-policy result |
| --- | --- |
| Manual human review | Outside iKant AI gate; no additional licence implied |
| Materialization after current clean acceptance | Allowed only to establish/verify conformance |
| Substantive AI-assisted study | Owner-authorized only with current acceptance + clean admission + technical conformance |
| Automated repository analysis | Same as substantive AI-assisted study |
| Model training / dataset construction | Separate owner licence required |
| Claimed platform/statutory/separate-licence basis | External basis not adjudicated; never self-promotes to iKant conformance |

The hierarchy is monotone: law/platform scope can limit what the owner may condition; owner authorization can be narrower than public visibility; runtime conformance can be narrower again; audit projections can never widen any higher layer.

## Machine-readable strategy

`RIGHTS.json` is the canonical repository-level policy and is digest-bound by the current access contract. `PROBE` fails if it drifts. When content is served from a rightsholder-controlled origin, deploy an appropriate origin-level machine-readable reservation in addition to the repository signal. TDMRep is treated as an implementation candidate, not as a W3C Recommendation.

## Validation model

v0.12 adds rights-policy unit tests, contract/manifest/probe drift validation, 100,000 generated semantic mutation instances per seed across dangerous authorization relaxations, a no-novelty tail, retention of v0.11 reticular saturation and historical regressions, and a version-neutral reticular boundary workflow.

Local convergence before publication used seeds `1,17,97,883,2026`: 500,000 semantic scenarios plus 500,000 mutation instances, each family with an additional 10,000-case no-novelty tail per seed. All local runs reported zero violations/survivors and zero tail novelty.

## Primary references

- Directive (EU) 2019/790: https://eur-lex.europa.eu/eli/dir/2019/790/oj
- Regulation (EU) 2024/1689: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Italian Legislative Decree 8 November 2021 no. 177: https://www.normattiva.it/eli/id/2021/11/27/21G00192/ORIGINAL
- Directive 2009/24/EC: https://eur-lex.europa.eu/eli/dir/2009/24/oj
- European Commission AI/copyright materials: https://digital-strategy.ec.europa.eu/
- GitHub Terms of Service: https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
- TDMRep Community Group report: https://www.w3.org/community/reports/tdmrep/
