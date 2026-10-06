# VT31 NAS100 — Stitched-DD Rapid Invalidation Forensics 001

**Status:** OBSERVATION-ONLY / CONSUMED EVIDENCE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Purpose

Identify why the already-validated Comparator-009 post-entry cognition cannot
close the stitched 10.149655R drawdown and the frozen 1.276669 annualized
Sharpe blocker.

No finding in this document is runtime authority.

## Breaker population

Across R8, R6, R5 and recent consumed, Comparator 009 contains:

- Breaker trades: 85;
- stressed winners: 27;
- stressed losses: 58.

The existing cognitive stack is highly selective once material adversity is
actually observable on a fully closed M1.

### Closed-M1 material adversity at -0.50R

Among the 58 Breaker losses:

- 19 expose at least one fully closed M1 with `current_open_r <= -0.50R`;
- 39 never expose such a closed-M1 state before terminal resolution.

Among the 27 Breaker winners:

- 7 expose a fully closed M1 with `current_open_r <= -0.50R`.

At the first <=-0.50R observation:

- 15 of the 19 eventual losses are already authorized to exit by the frozen
  Comparator-009 adverse stack;
- 0 of the 7 eventual winners are authorized to exit.

Therefore the current adverse-exit intelligence is not primarily suffering
from false positives. Its key limitation is **observability latency**: most
Breaker losses reach structural invalidation without first giving the
next-M1-open manager a closed -0.50R observation.

## Sudden-invalidation class

Of the 39 Breaker losses with no fully closed M1 <=-0.50R before terminal:

- 37 finish at raw -1.0R;
- one finishes at raw -0.333333R;
- one is a raw flat that is negative after friction;
- support spans all four consumed partitions:
  - R6: 13;
  - R5: 10;
  - recent consumed: 9;
  - R8: 7.

Six of these sudden invalidations occur inside the exact stitched maximum-DD
episode:

- 2022-03-24 Breaker SHORT;
- 2022-05-13 Breaker SHORT;
- 2022-08-04 Breaker LONG;
- 2022-11-14 Breaker SHORT;
- 2023-04-17 Breaker LONG;
- 2023-05-01 Breaker LONG.

Dates are forensic labels only and are forbidden runtime authority.

## Winner recovery overlap

A blind earlier adverse threshold is unsafe:

- 11 of 27 Breaker winners close at or below -0.25R at least once;
- 7 of 27 Breaker winners close at or below -0.50R at least once;
- 0 of 27 Breaker winners close at or below -0.75R.

Therefore simply moving every Breaker stop or exiting every Breaker at a fixed
earlier R level would not be a causal solution and would risk destroying the
winner tail.

Comparator 011 independently confirmed the same point from the favorable side:
deep giveback can occur inside legitimate large runners.

## Observation-only Sharpe feasibility bound

Using the already-frozen eligible-session daily-R series, an oracle
counterfactual was computed only to estimate the scale of improvement needed.
Terminal outcome is used here **only for diagnosis** and is forbidden policy
authority.

If all losing Breaker trade-days were hypothetically floored at -0.50R while
all winners were untouched:

- stitched DD would be approximately 5.43485R;
- annualized Sharpe would still be only approximately 1.42424.

If all losing Breaker trade-days were hypothetically floored at -0.25R:

- stitched DD would be approximately 3.45419R;
- annualized Sharpe would be approximately 1.50499.

This is not a proposal to install a -0.25R stop. It shows that the Sharpe gate
requires a **broad reduction in Breaker loss mass**, not one or two rescued
trades.

For reference, setting every Breaker loss to zero in the same oracle
counterfactual would produce Sharpe approximately 1.58562.

## Implication

The current blocker is now decomposed:

1. **Observable adverse journeys:** mostly already handled precisely by
   Comparator 009.
2. **Deep-giveback protection:** Comparator 011 proved unsafe because the same
   pattern occurs in future large runners.
3. **Sudden structural invalidations:** 39 Breaker losses, including six inside
   the stitched max-DD episode, are the largest unresolved loss mass.
4. **Sharpe density:** reducing only a few known losses cannot reach >=1.50;
   the solution must generalize across a materially larger part of the Breaker
   loss distribution or add genuinely positive independent edge.

## Next research target

The next observation phase must study the 39 sudden-invalidating Breaker trades
against matched Breaker winners using only entry-time causal evidence and
pre-existing categorical states.

Priority dimensions are:

- side;
- H4/H1/M15 state;
- prior-day / premarket / cash-open state;
- prior-range location;
- volatility/compression state;
- confirmation-latency bucket;
- reclaim/evidence freshness bucket;
- structure-event family/age;
- destination geometry available at entry;
- maximum-cognition contradictions/uncertainty available at entry.

No rule may be promoted from a same-date identity or a newly invented numeric
threshold.

## Governance

- pure edge only;
- no sizing, leverage, compounding, portfolio or capital engineering;
- no fold/date/outcome authority;
- Fresh Holdout remains sealed;
- Comparator 009 remains the frozen baseline;
- VT31 is not certified;
- no LIVE, real-capital or production authorization.
