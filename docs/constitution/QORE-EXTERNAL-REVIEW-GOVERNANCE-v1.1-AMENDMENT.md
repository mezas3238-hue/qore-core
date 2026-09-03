# QORE External Review Governance v1.1 Amendment

## Status

**CEO-DIRECTED CONSTITUTIONAL AMENDMENT — CLAUDE RETIRED FROM QORE REVIEW GOVERNANCE**

Parent constitution: `docs/constitution/QORE-EXTERNAL-REVIEW-GOVERNANCE-v1.0.md`.
Master roadmap authority: GitHub issue #303.
Effective repository authority: this amendment becomes binding for new and in-flight gates once merged to `qore-core/main`; the executive directive is additionally recorded in the canonical GitHub roadmap/issues so no new Claude work is dispatched while formalization is in flight.

## 1. Executive decision

Claude is excluded from the QORE project as an active reviewer, implementation agent, gate, dependency, required manual review, or required provider.

No future QORE delivery may be blocked waiting for Claude, dispatched to Claude, require a Claude prompt/report, or infer missing quality merely because a Claude stage is absent.

Historical commits, reviews, audit documents and findings that mention Claude remain immutable historical evidence. They are not deleted or rewritten and they do not create future Claude authority.

## 2. Supersession of v1.0 review chain

This section supersedes section 3 of `QORE-EXTERNAL-REVIEW-GOVERNANCE-v1.0.md` wherever that section requires Claude.

The mandatory serial chain is now:

1. implementation + normal and adversarial tests + required documentation;
2. canonical FULL Quality Gate green;
3. exact freeze of BASE / HEAD / SYNTHETIC / TREE / delta / CI;
4. DeepSeek Expert against the exact frozen candidate;
5. independent Integration Authority adjudication of Expert findings;
6. DeepSeek Coder against the same exact frozen candidate after Expert closure;
7. independent Integration Authority adjudication of Coder findings;
8. IA FINAL root-family exhaustion and integration decision;
9. Ready for Review;
10. protected merge with exact expected HEAD;
11. post-merge verification of `main`, merge/tree/parents/signature where applicable, CI and trackers;
12. automatic continuation to the next roadmap work item.

Canonical shorthand:

`HARNESS -> FULL QG -> FREEZE -> EXPERT -> IA -> CODER -> IA -> FINAL IA -> EXPECTED-HEAD MERGE -> POST-MERGE QG`

The absence of Claude is intentional and is not `EVIDENCE INSUFICIENTE`.

## 3. Quality non-regression

Claude retirement does not relax QORE quality.

The following remain mandatory:

- GitHub live state as source of truth;
- exact candidate binding and anti-duplication;
- `ruff check .`;
- `mypy src tests`;
- `pytest --cov=src/qore --cov-report=term-missing`;
- normal + adversarial tests;
- semantic LSP where required by the work package;
- fail-closed evidence handling;
- independent adjudication after each external reviewer;
- no self-certification by Harness, Expert or Coder;
- candidate change invalidates prior external reviews and requires a fresh freeze/review chain;
- expected-head protected merge and post-merge verification.

A clean external reviewer result remains evidence, not integration authority. Integration Authority retains final technical adjudication.

## 4. DeepSeek reviewer profile

This amendment does not by itself change the active DeepSeek technical profile in v1.0 section 8. `QORE-DEEPSEEK-V2.1.1-STABLE` remains the active external reviewer profile unless separately changed through governed profile evolution.

Expert and Coder remain separate serial review stages. One may not substitute for the other.

## 5. Supersession of reviewer-profile change gate

Any clause in v1.0 section 11 that specifically requires a manual Claude review for reviewer-profile evolution is superseded.

A reviewer-profile change must instead receive independent technical validation that is not self-certified by the component being changed, plus Integration Authority adjudication. Where DeepSeek infrastructure itself is the subject of change, its own benchmark can provide evidence but cannot be the sole approving authority.

## 6. No hidden replacement

Claude retirement does not authorize silently replacing Claude with an ungoverned external provider or adding a new mandatory reviewer by convention.

Any future external reviewer must be explicitly introduced by a versioned constitutional amendment and must preserve or improve evidence coverage, exact binding, fail-closed behavior, independence and reproducibility.

## 7. In-flight deliveries

For candidates already in Harness, Expert or Coder when this amendment is adopted:

- preserve all completed work and durable artifacts;
- do not restart merely because the review chain changed;
- do not create or wait for a Claude stage;
- continue from the exact next valid gate under this amendment;
- if the candidate changes, obey the normal refreeze/review invalidation rule.

Existing historical Claude PASS/findings remain usable historical evidence only for the exact candidates they reviewed.

## 8. Authority limits

This amendment changes review governance only. It does not authorize Production, real capital, productive credentials, deposits/withdrawals, real-money orders, Risk bypass, automatic corrective trading, or inference of Production readiness from DEMO evidence.

`QUALITY NON-REGRESSION` remains mandatory.
