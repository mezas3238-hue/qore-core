# VT08 CRT PURE — R2-CK SIX-START H4 TIME ATTRIBUTION — FREEZE 001

**Date:** 2026-10-13 · PR #626 · Research only · No automatic scheduling/filter selection

## Motivation

R2-CJ verified >240 trades/year in AUDUSD and USDJPY on the original R2-AQ older + R2-AO recent rolling H4 fixed 1.5R population; those broad populations FAIL even very small per-trade modeled costs. Determine descriptively whether the weak edge is dispersed over the **six predefined rolling-H4 parent starts** versus concentrated by structural H4 position. This is **not a strategy search or an executable gate**; six comparisons on reused historical development data do not grant a winner.

## Frozen categories before looking at their economics

Exactly six `timing_triplet` ledger labels `ROLLING_H4:1`, `:2`, `:3`, `:4`, `:5`, `:6`, corresponding to original NY starts 01,05,09,13,17,21. No label will be excluded. Do NOT guess year-specific best hours. Confirm each event carries exactly one of six labels, original H4 parent and M15 source.

Evidence: identical archived R2-AQ original older ledgers/run `35865028789` and R2-AO recent target-arm `FIXED_1_5R` run `35863768335`, separate AUDUSD and USDJPY, same SHA256 as R2-CJ.

## Fixed diagnostics

1. First rerun R2-CJ independent original-source checks and full pooled gross/cost checks. Fail closed on source drift, unsupported timing label or missing values.
2. For each of six labels in BOTH older and recent periods and their combined history, measure n, annual normalized frequency, gross PF/R/mean/DD, **0.02R** per-entry stress R/PF/DD, positive year fraction, and the difference of mean R between older/recent.
3. Reconcile six categories exactly to each full period and pooled R2-CJ trade counts and gross R. No six-bucket winner, no threshold change, no adaptive gating.
4. Report potential overlapping source/entry timestamp counts as identification concerns but do not infer concurrent positions without exit timestamps and exposure evidence.
5. **No multiple-hypothesis p-values or claim of significance** from reused history. If some label looks positive in sample, classify `EXPLORATORY_ONLY` and require a newly preregistered out-of-sample replication with realistic friction, high-retention density and governance gates before consideration.

## Hard boundaries

No external market downloads; no cTrader trading permission; no leverage, lot sizing, order volume, CIBO capital allocation, entry instructions, merge, VPS, DEMO/LIVE or production. BTCUSD remains frozen. R2-CK cannot rehabilitate failed R2-CF by simply choosing profitable H4 starts.
