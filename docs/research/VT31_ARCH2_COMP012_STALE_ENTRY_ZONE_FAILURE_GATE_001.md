# VT31 NAS100 — Comparator 012 STALE Entry-Zone Failure Gate 001

**Status:** PREDECLARED CONSUMED-EVIDENCE DEVELOPMENT GATE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Execution venue:** independent GitHub Trader Lab  
**Fresh Holdout:** SEALED

## Discovery provenance

The observation-only post-entry causal fact audit on consumed evidence identified
one zero-winner cross-partition conjunction:

`closed_through_entry_zone_against_thesis && reclaim_bucket=STALE_8_14M`

The audit was explicitly observation-only. It granted no trading authority.

Across the retained consumed partitions, the conjunction was observed on
actionable Comparator-009 trades with:

- support across R5, R6, R8 and recent consumed;
- 10 eventual losses;
- 0 eventual winners;
- no new numeric-threshold search;
- no date/fold identity authority.

This gate freezes the hypothesis **before** economic replay.

## Comparator ID

Research variant:

`COMP012_STALE_ENTRY_ZONE_FAILURE_EXIT`

A surviving result may later be frozen as:

`VT31_AB_COMP012_STALE_ENTRY_ZONE_FAILURE_SURVIVOR`

It is not a candidate freeze at this stage.

## Exact causal action

Keep Comparator 009 unchanged except for one additional post-entry exit authority.

For an admitted Comparator-009 trade, inspect only fully closed M1 observations
already available to the post-entry cognition.

Authorize the new exit only at the first observation where all are true:

1. `closed_through_entry_zone_against_thesis == true`;
2. the pre-existing reclaim-age bucket is exactly `STALE_8_14M`;
3. the existing Comparator-009 cognitive exit is **not already authorized** at
   that observation;
4. a causally valid next M1 open exists.

The decision is made at the closed M1 observation.

Execution is at the **next M1 open**.

The next-open R is an execution consequence only. It is never decision
authority.

## Frozen semantics

`closed_through_entry_zone_against_thesis` means:

- LONG: the fully closed M1 close is below the lower bound of the selected
  frozen entry-evidence zone;
- SHORT: the fully closed M1 close is above the upper bound of the selected
  frozen entry-evidence zone.

`STALE_8_14M` is the already-existing reclaim bucket:

- reclaim age >=8 minutes;
- reclaim age <=14 minutes.

No new threshold is introduced.

## Forbidden information

The action may not use:

- terminal trade result;
- future M1 high/low/close;
- partition identity;
- calendar date as an oracle;
- stitched-DD episode membership;
- equity state;
- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation;
- CIBO rescue.

## Evaluation order

Use the prepared causal ledger in the independent GitHub Trader Lab.

First run cheap deterministic gates:

1. unchanged policy across all four retained folds;
2. per-fold PF >=1.50;
3. per-fold observed DD <=6R;
4. density >=75%;
5. winner count preservation >=80%;
6. winner-R preservation >=90%;
7. combined PF >=1.70;
8. combined expectancy >=+0.15R/trade;
9. payoff >=1.20;
10. **stitched chronological observed DD <=6R**;
11. **annualized Sharpe >=1.50 under the already-frozen convention**;
12. annualized Sortino >=2.00;
13. degraded 0.10R PF >1.0.

Only if the core DD + Sharpe gate survives may the canonical 10,000-path Monte
Carlo be executed.

Monte Carlo requirements:

- positive terminal >=90%;
- p95 maximum DD <=15R.

## Winner and actuation accounting

The report must expose:

- changed trade count by fold;
- each changed trade's control R;
- next-open candidate R;
- delta R;
- causal observation timestamp;
- winner preservation;
- whether the action occurred inside the stitched maximum-DD episode.

A no-op survivor is not an economic improvement.

## Success condition

A research survivor requires the **same exact rule** to pass the full consumed
cross-fold and stitched gate without relaxing any sovereign threshold.

If stitched DD remains >6R or frozen Sharpe remains <1.50, the hypothesis is
rejected even if PF improves.

## Governance

- consumed evidence only;
- pure edge only;
- no sizing or capital engineering;
- no metric retuning;
- no Fresh Holdout access;
- no candidate certification;
- no LIVE, real-capital or production authorization.
