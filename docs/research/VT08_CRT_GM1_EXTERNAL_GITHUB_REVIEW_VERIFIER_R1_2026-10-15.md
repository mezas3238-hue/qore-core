# VT08 CRT — G-M1 external GitHub reviewer witness R1 (2026-10-15)

**Security status: implemented, linted and unit-tested; NO actual independent signature.** Scope is G-M1 source/methodology attestation diagnostic only. **Not G-M1 PASS, not G-M5, not Global.** No financial orders, sizing, economic gate, broker/VPS, dataset copying, PR merge or production actions.

## Code and precise scope

- Verifier: `src/qore/infrastructure/traders/crt_pure_gm1_external_review.py`
- Adversarial tests: `tests/infrastructure/traders/test_crt_pure_gm1_external_review.py`
- Source/methodology docket: [G-M1 seven-rule dossier](VT08_CRT_GM1_SEVEN_RULES_REVIEW_DOSSIER_2026-10-15.md)
- Branch: `agent/vt08-crt-pure-source-identity-001`; PR **#626**, base **agent/vt08-crt-cognitive-architecture-freeze-001**, repo **mezas3238-hue/qore-core**.
- Native GitHub HTTPS API read-only GET retrieves PR, paginated reviews, paginated issue comments, paginated PR commits, and exact G-M1 dossier content by HEAD SHA; then refetches PR HEAD to detect changes. Requires token/role IDs from separately protected environment. No GitHub user name is trusted just because typed in a PR.

### How a real witness would be formed — not yet done

1. Owner independently designates a distinct GitHub **reviewer account** with methodology competence, which must not equal Owner or PR author and must not be a linked contributor to **any** PR commit. Do not manufacture a second account, a bot signature or another persona just to satisfy the rule.
2. An *outside-the-PR*, protected execution environment supplies `GITHUB_TOKEN` (read-only), `VT08_TRUSTED_OWNER_ID` and `VT08_TRUSTED_REVIEWER_ID` (GitHub numeric ids). The names in source files, PR comments, editable GitHub Actions jobs or CLI arguments are **not** trust roots. **Do not inject secrets into Actions executing unreviewed PR branch code.** The verification script is only a reference implementation until independently deployed/audited.
3. Pin the **final HEAD SHA** of PR #626 and fetch the G-M1 dossier bytes from that exact SHA. Calculate `DOC_SHA256` over those literal bytes. The qualified reviewer submits a native GitHub **APPROVED pull request review** whose *entire* body (except surrounding whitespace) is the following one-line attestation:

```text
VT08-GM1-REVIEW-V1 HEAD=<full_40_hex_sha> DOC_SHA256=<full_64_hex_sha256>
```

4. After that native review, the Owner account creates a *new*, unedited PR conversation comment whose exact body is:

```text
VT08-GM1-OWNER-V1 HEAD=<full_40_hex_sha> DOC_SHA256=<full_64_hex_sha256>
```

5. A separately governed read-only runner can execute `python -m qore.infrastructure.traders.crt_pure_gm1_external_review --live` with the protected environment. The independent account ids, correct GitHub API review state, exact commit_id, matching doc SHA256, same repo/base/head, review chronology, Owner acceptance and absence of late `CHANGES_REQUESTED` must all hold.
6. A verified witness means only **review evidence matched**. The diagnostic returns `gm1_pass=false`, `gm5_issued=false`, `capital_authorized=false` by design. Production G-M1 issuance requires seven *individually* adjudicated contracts and independent source review; G-M2–G-M4 must also PASS before G-M5; economic Global separate. The live audit must be repeated after any code or document change: a new head SHA invalidates an old review.

## Deny-by-default conditions covered in tests

Untrusted or equal Owner/reviewer IDs; reviewer equals PR author or contributor; missing/unlinked commit author; incorrect PR number, base, branch or head repository; PR commit tip mismatch; stale SHA, mutated dossier; wrong account or free-text body, fake `COMMENTED` state, review revocation; owner signoff prior to reviewer; edited owner comment; later `CHANGES_REQUESTED`; untrusted API errors or head moves during retrieval. Paginated overflow fails closed.

### Limits that still block trusted production use

- R1 has a **pure evaluation function** intentionally exercised by fake unit fixtures; a synthetic green fixture **cannot** be submitted as an independent witness or used by the certifier. Actual authority must only arise from live API collection with trust roots managed outside editable PR content.
- Reviewer competence, seven-rule per-article adjudication, blind G-M2, causality and safe policy implementation are **not inferred** by checking two strings against the GitHub API.
- A GitHub `APPROVED` review is a GitHub-authenticated action, but the environment that verifies it must also be independently controlled/protected, not script run from an attacker-editable PR with elevated secrets.
- Reviewer account must be genuinely independent. The sole current GitHub Owner login cannot act simultaneously as independent methodological reviewer. PR #626 has **zero recorded review submissions** at baseline, so no authenticated witness can yet be claimed.
- This module **does not modify** `crt_pure_methodological_certification.py` nor `crt_pure_three_source_methodology.py` blockers. G-M1…G-M4 remain PARTIAL, G-M5 NOT ISSUED, Global NOT CERTIFIED. No fill/BID-ASK or fresh OOS assessed.
- Github user `id` is platform-authenticated but not cryptographic person identity proof; independent social/organizational verification of reviewer suitability is also required.

## Evidence of this round
The first CI after wiring code and tests was [run #38788976387](https://github.com/mezas3238-hue/qore-core/actions/runs/38788976387) **SUCCESS**: Ruff + strict mypy + pytest (107 tests in the CRT focused suite). Hardening after that run binds base branch, both repos and the commit-list HEAD; inspect the most recent CI for the later commit before claiming its green result.

**Outstanding issue:** [#976](https://github.com/mezas3238-hue/qore-core/issues/976). **Custody issue:** [#837](https://github.com/mezas3238-hue/qore-core/issues/837). BTCUSD remains frozen; Atlas original AUDUSD/USDJPY is historical development data, not genuine OOS. **Sizing is categorically forbidden in VT08; only CIBO/QORE Risk controls patrimonial DD/capital.**
