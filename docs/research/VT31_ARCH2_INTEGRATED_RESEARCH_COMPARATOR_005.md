# VT31 NAS100 — Integrated Research Comparator 005

**Owner:** Sergio Meza  
**Status:** FIXED INTEGRATED RESEARCH COMPARATOR / NOT CANDIDATE FREEZE  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Comparator ID

`VT31_AB_COMP005_BREAKER_RECOVERY_PLUS_FVG_FRESH_FAST`

## Fixed stack

B-side position logic remains:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

Admission logic is:

1. `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
2. abstain Breaker + SHORT + prior-day rotation + compressed reference,
   except the bullish recovery sequence;
3. abstain FVG + SHORT + compressed reference + FRESH_LT8M reclaim +
   FAST_LE5M confirmation.

## Consumed-evidence development result

The FVG fresh-fast addition non-degrades the prior survivor on PF, mean-R,
observed DD and half-year stability in all four folds.

Winner count and winner-R remain 100% preserved.

Current economics:

- R5: PF 4.41436, mean +2.01738R, DD 6.01951R, MC positive 98.07%;
- R6: PF 4.80485, mean +2.54872R, DD 5.39444R, MC positive 98.43%;
- R8: PF 5.53228, mean +2.61260R, DD 6.00502R, MC positive 99.13%;
- recent: PF 1.93380, mean +0.65941R, DD 8.28975R, MC positive 88.83%.

Density versus the prior survivor remains >=87.8% in every fold.

## Interpretation

R6 now clears the sovereign observed-DD gate.

R5 misses by about 0.0195R and R8 by about 0.0050R.

Recent remains the main blocker at 8.29R and still misses the 90% MC positive
gate.

This comparator is consumed-evidence development only. It does not open fresh
holdout and does not certify VT31.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation, capital
weighting or absolute-volume authority is used.
