# VT31 NAS100 — FVG Short Compressed Fresh-Fast Admission Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed integrated base

Position logic:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

Admission logic:

- `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- abstain Breaker + SHORT + prior-day rotation + compressed reference,
  except the predeclared bullish recovery sequence.

That integrated base is a 4/4 development survivor. Recent observed DD is
approximately 8.29R, still above the sovereign <=6R gate.

## Observation-only discovery

Residual entry-quality attribution on the survivor population found:

`FVG + SHORT + compressed reference + FRESH_LT8M reclaim + FAST_LE5M confirmation`

with zero winners in every consumed fold:

- R5: 5 losses / 0 winners;
- R6: 2 losses / 0 winners;
- R8: 2 losses / 0 winners;
- recent: 1 loss / 0 winners.

Total: **10 losses / 0 winners**.

This is discovery evidence only and has zero runtime authority until replayed
as a separately predeclared causal rule.

## Why the state is causal

All fields exist before entry:

- entry family;
- side;
- frozen reference-volatility state;
- reference-reclaim freshness bucket;
- confirmation-latency bucket.

The freshness and confirmation buckets already exist in VT31 causal vocabulary:

- `FRESH_LT8M`;
- `FAST_LE5M`.

No new numeric threshold is invented here.

## Predeclared candidate

`ABSTAIN_FVG_SHORT_COMPRESSED_FRESH_FAST`

Starting from the fixed integrated base, abstain only when all are true:

- entry family = fair-value-gap;
- side = SHORT;
- reference volatility = compressed;
- reclaim sequence = FRESH_LT8M;
- confirmation latency = FAST_LE5M.

No other trade is changed.

## Frozen development gates

Across R5/R6/R8/recent require:

- PF non-degrading 4/4;
- mean-R non-degrading 4/4;
- observed DD non-degrading 4/4;
- density >=75% 4/4;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrading.

Owner direction remains:

- era PF >=1.50;
- recent/combined PF >=1.70;
- expectancy >0R, target >=+0.15R;
- observed DD <=6R hard certification gate;
- MC positive >=90%;
- MC p95 DD <=15R robustness target.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation, capital
weighting, fold/date identity, outcome oracle, fresh holdout, candidate freeze,
LIVE, real capital or production authority is allowed.
