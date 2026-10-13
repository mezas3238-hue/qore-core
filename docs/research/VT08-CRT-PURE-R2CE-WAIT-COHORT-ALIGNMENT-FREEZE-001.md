# VT08 CRT PURE — R2-CE WAIT-cohort alignment preregistration

**Date:** 2026-10-13  
**Repository / PR:** mezas3238-hue/qore-core / #626  
**Status:** RESEARCH-ONLY / EXPLORATORY / NO CANDIDATE PROMOTION

## Motivation / code-inspection finding

Both frozen R2-CC (AUDUSD) and R2-CD (USDJPY) fit Journey Experience on **all** viable delayed historical entries in the preceding 4-year training window, but apply the second decision **only** to initial cognitive WAIT opportunities. Thus the training and deployment populations differ. This is not in itself proof of temporal leakage or an incorrect result. It is an unmeasured cohort-alignment risk.

## Frozen research question

How much does cohort alignment alter first-M15 Journey Memory, second cognitive actions, density, normalized-R PF/DD and 0.02R/0.05R stress?

## Exactly two arms — fixed before running

- **CONTROL_ALL:** preserve R2-CC/R2-CD unchanged: initial decision trained on prior 4Y; Journey Memory trained from all viable delayed historical opportunities, then second decision on WAIT only.
- **WAIT_ALIGNED_DIAGNOSTIC:** identical initial model and second sovereign cognitive reasoner, but Journey Memory is fit only to viable delayed rows whose *initial action under that fold's initial model* is WAIT. No other changes. Initial EXECUTE and ABSTAIN remain identical to control. WAIT terminal states stay terminal.

**Critical interpretation:** historical WAIT membership is computed retrospectively from the fold's complete preceding-4Y initial model. This is OOS relative to the *next* year, but not strictly an online historical WAIT journal; it is a diagnostic cohort selection, NOT a causally certified deployable improvement. A later fully nested/past-only inner WFO is required before promotion. No fresh holdout is used here.

## Non-negotiable invariants

1. Markets **separately** AUDUSD and USDJPY; no experience-state transfer.
2. No use of OOS outcomes in either model fit or decisions. First completed M15 may be observed only before the delayed-entry decision.
3. Original stop; 1.5R recomputed at the next M15 open; original C3 expiry; same-M15 STOP_FIRST. AUDUSD BE_CLOSE_075, USDJPY CONTROL.
4. Initial ABSTAIN is terminal; invalidated / destination-consumed WAIT never chased.
5. No extra WAIT stage, no thresholds or model parameters changed.
6. Duplicated hypothesis/entry keys fail closed rather than silently replacing trades.
7. Normalized R only. **No sizing, volume, leverage, balance, risk budget or capital assignment within VT08.**
8. Original R2-CC / R2-CD files and historical report/run identifiers remain unchanged.
9. NO MERGE / VPS / DEMO / LIVE / production / real capital.

## Required outputs / tests

- Per year: initial EXECUTE / WAIT / ABSTAIN, TRAIN WAIT share, viable/terminal training WAIT, Journey cells/support for both arms, second action counts, transitions, WAIT eligible vs noneligible.
- Per market and arm: exact entry count and origins, density/year, gross PF and R, max DD (R), DOA, 0.02R and 0.05R cost stress, positive OOS years, source-state composition.
- Full fold and pooled accounting invariants: initial actions sum to OOS opportunities; WAIT = terminal + second decisions; unique keys preserved; combined portfolio count = initial EXECUTE + second EXECUTE.
- Reproduction reference: CONTROL_ALL should reproduce prior R2-CC/R2-CD metrics within numerical precision; otherwise FAIL and investigate before interpreting other arm.
- If WAIT_ALIGNED yields improvement, classify as exploratory only; no new certified edge until chronological nested training/independent fresh testing.
- If WAIT membership is too sparse for cells (minimum 30, prior 100 unchanged), report UNKNOWN/WAIT rather than silently loosening support.

**Pre-result verdict:** no economic result from R2-CE can be asserted before workflow artifacts are checked.
