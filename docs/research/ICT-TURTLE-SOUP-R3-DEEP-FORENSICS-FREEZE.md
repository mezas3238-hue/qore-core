# ICT Turtle Soup R3 — Deep Winner/Loser Forensics Freeze

Date: 2026-09-15
Parent candidate: `ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD`
Parent run: `35038587031`
Parent artifact: `10424038795`
Parent executed HEAD: `9ddb92dfa9090b39fa43d7b7dff298f1d20d736c`
Evidence status: consumed development only.
Tracks: #584

## Purpose

Perform a full post-result autopsy of every R3 winner, loser and flat without changing the frozen R3 rules and without selecting a new candidate from this consumed evidence.

The objective is to localize the dominant causal failure mechanisms before any R4 source-bound candidate is frozen.

## Required analyses

The analyzer must reconcile exactly the immutable parent trade ledger and use only retained read-only M5 evidence from the same parent evidence source.

### 1. Winner / loser cohort anatomy

For gross and primary-net outcome cohorts measure:

- count / mean / median / total / PF;
- initial risk in bps;
- projected R;
- target distance and stop distance;
- C1 range geometry;
- entry position inside/relative to the C1 range;
- sweep penetration beyond the relevant level;
- C2 reclaim depth;
- C2 body fraction and rejection-wick fraction;
- CISD threshold geometry;
- protected-swing distance / overshoot;
- sweep-to-CISD, CISD-to-entry, sweep-to-entry, entry-to-exit latency;
- MFE and MAE in R before exit;
- time to MFE / MAE.

### 2. Stop-path forensics

For `stop`, `gap-stop`, and `stop-first` trades measure:

- pre-stop MFE;
- share reaching +0.25R / +0.50R / +1.00R before stop;
- stop latency distribution;
- same-C3 post-stop recovery;
- next-H4 post-stop recovery;
- next-8h post-stop recovery;
- share recovering entry / +0.25R / +0.50R / +1R / original target;
- final C3 and next-H4 close R.

These diagnostics must NOT authorize stop widening, BE changes or re-entry.

### 3. Target-path / Draw-on-Liquidity forensics

For target winners measure:

- target R distribution;
- adverse excursion before target;
- time to target;
- favorable continuation after target within the rest of C3;
- favorable continuation through the next H4;
- favorable continuation through the next 8 hours;
- additional R beyond the frozen target;
- share reaching target+0.25R / +0.50R / +1R after the target.

This diagnoses whether the frozen opposite-C1 target truncates a source-valid higher-timeframe Draw on Liquidity. It does NOT select a replacement target.

### 4. Time-exit forensics

For C3 time exits measure MFE, MAE, terminal R, fraction that were positive/negative at close, and post-C3 next-H4 continuation/reversal.

### 5. Structural / context features

Using only pre-entry information compute:

- C1 range and C1 body fraction;
- C2 range, body fraction, rejection wick, sweep penetration and reclaim depth;
- previous 3/6/12 H4 median-range regime ratios;
- C1 relevant-swing separation from prior H4 extrema;
- prior-H4 body direction relative to trade side;
- protected-swing / C1-range ratio;
- entry-to-protected-swing / C1-range ratio;
- target-distance / C1-range ratio;
- CISD threshold location within C1 range;
- number of M15 bars from sweep to CISD;
- session and NY clock hour as diagnostics only.

### 6. Stability / breadth / interaction diagnostics

Produce:

- symbol, side, session, NY hour, quarter, half-year and year summaries;
- symbol x side and session x side matrices;
- leave-one-symbol-out reconciliation;
- rolling 90d and 180d outcome summaries;
- simultaneous-entry H4 cluster analysis across pairs;
- losing-streak / drawdown-cluster composition;
- top winner and top loss concentration;
- gross-to-primary friction attribution, including gross winners flipped to non-positive after 0.05R friction.

### 7. Distributional diagnostics, not filters

For every numeric pre-entry feature:

- winner vs loser quantiles;
- median difference;
- Cliff's delta / rank-order effect size;
- fixed decile summaries over the full consumed sample.

No decile boundary or threshold may become a future rule from this result. These outputs are hypothesis generators only.

## Root-cause families to adjudicate

The final report must explicitly grade evidence for, against, or underdetermined for at least:

1. `TARGET_DOL_TOO_LOCAL_OR_TRUNCATED`
2. `PROTECTED_SWING_INVALIDATION_MISMATCH`
3. `CISD_CONFIRMATION_LACKS_PERSISTENCE`
4. `C2_REJECTION_QUALITY_INSUFFICIENT`
5. `RELEVANT_SWING_CONTEXT_TOO_SHALLOW`
6. `ENTRY_TIMING_C3_OPEN_MISMATCH`
7. `FRICTION_DOMINATES_NEAR_BREAK_EVEN_GROSS_EDGE`
8. `MARKET_SIDE_OR_SESSION_NONSTATIONARITY`
9. `CROSS_PAIR_CLUSTER_REGIME_FAILURE`
10. `RIGHT_TAIL_OR_OUTLIER_DEPENDENCE`

## Governance

- parent R3 remains rejected and immutable;
- no fresh OOS may be opened;
- no pair, side, hour or session may be removed based on this analysis;
- no target/stop/entry/confirmation threshold may be selected from consumed outcomes;
- no candidate promotion;
- no merge;
- no DEMO/LIVE/real-capital/production authority.

Any economic correction requires a new R4 identity frozen from ICT/TTrades source rationale before another replay.
