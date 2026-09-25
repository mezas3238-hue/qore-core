# VT08 Cognitive Expansion — M3 Management Attribution Frontier V1

Status: **PRE-RESULT / CONSUMED DEVELOPMENT / ATTRIBUTION ONLY**

## Purpose

On the globally selected high-density `M3_FRACTAL` latest-PS admission,
separate the economic effect of VT08 structural banking from the incremental
effect of the pre-existing aggressive CIBO ratchets.

The admission population is immutable. No trade may be added, removed, ranked,
filtered or reweighted.

## Frozen population

- Markets: EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD.
- Profile: M3_FRACTAL for every market.
- Selector: LATEST_CONFIRMED_PROTECTED_SWING_V1.
- Evidence: same consumed 1095-day corpus and exact-window M3 evidence used by
  run 35942191510.
- Daily bias, C2 admission, anchors, entry, initial stop, fixed 2R target,
  H4 lifecycle and daily cardinality are unchanged.

## Arms

Exactly three already-existing mechanics are compared on identical trades:

1. RAW — original equal-risk terminal R.
2. BANK_ONLY — VT08 reference-H4 EQ50 / opposite-extreme structural banking,
   no CIBO ratchet.
3. CORE_AGGRESSIVE — the same structural banking plus the pre-existing
   aggressive VT08 CIBO ratchets.

No new threshold and no parameter search are permitted.

## Decision use

This is mechanism attribution on consumed evidence. It may identify which
existing management component merits a separately frozen candidate, but it
cannot certify a trader. Any selected management contract requires unseen
temporal validation.

## Authority

research_only=true
freshness_claimed=false
trade_filtering=false
capital_weighting=false
live_authorized=false
production_authorized=false
real_capital_authorized=false
