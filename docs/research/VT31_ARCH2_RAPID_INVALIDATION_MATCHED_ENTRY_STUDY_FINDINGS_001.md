# VT31 NAS100 — Rapid-Invalidation Matched Entry Study Findings 001

**Status:** CLOSED / NO ADMISSION RULE PROMOTED  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Population

The predeclared observation-only study used the current consumed Comparator-009
Breaker population:

- 85 Breaker trades;
- 39 sudden-invalidation losses;
- 27 stressed winners;
- 19 other losing/flat journeys.

A sudden invalidation is diagnostic only: an eventual losing Breaker trade that
never exposes a fully closed M1 with `current_open_r <= -0.50R` before
terminal resolution.

## Method

Only already-existing entry-time categorical states and frozen buckets were
examined. Single states and two-state conjunctions were allowed. A reported
loss-only candidate had to contain at least three sudden invalidations spanning
at least three consumed partitions.

No new numeric threshold was searched.

## Strongest zero-winner two-state observations

The loss-only pairs with qualifying cross-partition support were:

1. `H4 bearish + H1 bearish`
   - total current sample: 6;
   - sudden invalidations: 5;
   - winners: 0;
   - sudden support: 3 partitions.

2. `prior-range upper-third + reference volatility normal`
   - total sample: 6;
   - sudden invalidations: 4;
   - winners: 0;
   - sudden support: 3 partitions.

3. `reference volatility normal + entry-evidence STALE_8_14`
   - total sample: 5;
   - sudden invalidations: 4;
   - winners: 0;
   - sudden support: 3 partitions.

4. `M15 bullish + prior-range middle-third`
   - total sample: 3;
   - sudden invalidations: 3;
   - winners: 0;
   - sudden support: 3 partitions.

5. `prior-range above + reclaim 15M_PLUS`
   - total sample: 4;
   - sudden invalidations: 3;
   - winners: 0;
   - sudden support: 3 partitions.

These are observation-only correlations. None is promoted.

## Deliberately generous union upper bound

As an upper-bound diagnostic, all five loss-only pair observations were unioned
without granting them runtime authority.

The union removes:

- 20 current Comparator-009 trades;
- 0 current winners;
- support from all four consumed partitions.

Even this deliberately generous loss-only union would produce only:

- stitched DD: approximately **6.31906R — FAIL**;
- annualized Sharpe: approximately **1.38478 — FAIL**.

Combined PF and expectancy improve, but those are not the blockers.

Therefore even a cherry-picked union of the strongest existing loss-only entry
pairs does not close the two hard remaining economic gates.

## Adjudication

Do not promote any of the five pairs and do not stack them into a new
Comparator.

The study shows that further pruning with the already-observed categorical
entry states is not sufficient. Continuing to combine losing cohorts would add
degrees of freedom without a realistic path to the frozen Sharpe requirement.

## Consequence

The remaining closure problem cannot be solved by:

- Comparator-010 neutral-destination exit: proven no-op;
- Comparator-011 old DGR transfer: proven destructive;
- a small set of existing loss-only admission vetoes: mathematically
  insufficient.

The next pure-edge research direction should investigate whether the structural
candidate pool contains **genuinely additional, independently positive setups**
that Comparator 009 currently rejects and that full cognition can distinguish
causally.

Increasing valid positive opportunity density can improve daily-R Sharpe
without forcing blind early exits on recoverable winners.

## Governance

- observation only;
- no terminal label may enter runtime;
- no date/fold identity;
- no sizing/leverage/compounding/portfolio/capital engineering;
- no certification gate relaxed;
- Fresh Holdout remains sealed;
- Comparator 009 remains the baseline;
- VT31 remains not certified.
