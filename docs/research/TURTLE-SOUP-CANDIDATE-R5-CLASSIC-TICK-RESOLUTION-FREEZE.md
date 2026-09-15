# Turtle Soup Candidate R5 — Classic Tick-Resolution Freeze

Status: **FROZEN BEFORE TICK-RESOLVED ECONOMIC OUTCOMES**

Research identity: `turtle-soup-candidate-r5`

Parent evidence: `turtle-soup-candidate-r1` final Forensics. Canonical trader code: `CODE_UNASSIGNED`.

## 1. Why R5 exists

R1 Classic closed only 14 deterministic trades and left 293 cases as `M1-INTRABAR_PATH_AMBIGUOUS`, plus three separate `M1_DATA_UNAVAILABLE` cases. R5 does not alter the Classic method. It uses provider-native historical BID ticks only to resolve causal ordering that M1 could not establish.

## 2. Wave 1 — immutable evidence

The original R5 Wave 1 manifest contained **291** causally selected minutes. It produced immutable BID-tick evidence in workflow run `34969259616` at software SHA `36bc4a537a907b2a84509c1ab3a1babe033fad9c`; all 291/291 minutes returned tick data.

An independent replay of the governed R1 D1/M15/M1 evidence subsequently reproduced the published R1 census exactly and exposed a manifest-construction defect: two genuine R1 `M1-INTRABAR_PATH_AMBIGUOUS` cases were omitted from Wave 1:

- GBPUSD `2024-04-10T15:45:00+00:00` LONG;
- USDCAD `2025-07-29T12:05:00+00:00` SHORT.

The omission was discovered from causal state only. No P&L, winner/loser state, management policy, market ranking, side ranking, fold result or holdout information participated. Wave 1 is therefore retained **byte-for-byte** rather than rewritten retrospectively.

## 3. Corrective Wave 1B

The two omitted rows form a separate corrective acquisition wave. Combining immutable Wave 1 (291) and Wave 1B (2) restores the complete **293-case** R1 Classic ambiguity census. The three R1 `M1_DATA_UNAVAILABLE` cases remain censored and are not promoted into tick targets.

## 4. Tick evidence contract

For every frozen target minute R5 requests BID ticks only from `minute_opened_at <= tick_timestamp < minute_opened_at + 60 seconds`. The collector must authenticate read-only, resolve the exact symbol, paginate without crossing the minute, reconstruct cumulative timestamp/price deltas, preserve equal-timestamp groups, emit exact software/evidence fingerprints and perform no trading mutation.

Unavailable evidence, irreconcilable M1/tick evidence or decisive equal-timestamp conflicts remain censored. No synthetic tick, interpolation, random intrabar path or favorable OHLC ordering is permitted.

If resolving an earlier ambiguity exposes a later ambiguity in the same source opportunity that R1 could not previously reach, that later minute must be frozen as a **new causal-resolution wave before its economic outcome is evaluated**.

## 5. Economic rules remain frozen

Resolved Classic setups retain the exact R1 source entry, initial stop and four predeclared Classic management policies. Primary cost remains `1.0 bp`, stress remains `2.0 bp`, and the six R1 Walk-Forward folds and absolute advancement gate remain unchanged.

Resolution coverage by itself is not evidence of edge.

## 6. Fresh OOS remains closed

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`.

Every R5 target must be pre-embargo. No post-embargo price data may be requested or consumed. No FTMO/FundedNext/LIVE authority is granted by R5 data resolution.
