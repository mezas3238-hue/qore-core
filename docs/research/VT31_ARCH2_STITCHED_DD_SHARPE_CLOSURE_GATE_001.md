# VT31 NAS100 — Stitched DD + Sharpe Closure Gate 001

**Status:** PREDECLARED PRE-HOLDOUT DEVELOPMENT REOPENING GATE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Why development is reopened

Comparator 009 closes the previously known per-partition observed-DD blocker,
but the frozen final pre-holdout metric pack exposed two certification blockers
that were not visible in isolated fold adjudication.

### Blocker 1 — stitched observed drawdown

When the immutable consumed partitions are ordered by actual `signal_at`
chronology and evaluated as one continuous equal-R trader path, baseline
friction 0.05R/trade produces:

- combined sample: 109 trades;
- combined PF: ~4.5979;
- combined expectancy: ~+2.1310R/trade;
- **stitched observed maximum drawdown: ~10.1497R**.

The sovereign observed-DD gate is:

`<=6R`.

Partition boundaries may not be used as artificial equity resets to hide a
drawdown that exists in the chronological trader path.

The currently identified stitched peak-to-trough spans:

- peak trade: 2022-02-08;
- trough trade: 2023-05-01.

This interval is observation-only forensic scope. Dates may never become
runtime authority.

### Blocker 2 — frozen Sharpe convention

The already-frozen pre-holdout convention reports on the combined consumed
evidence:

- eligible NY sessions: 2023;
- no-trade eligible sessions: 1914;
- annualized Sharpe: **~1.2767**;
- sovereign gate: **>=1.50**.

The formula may not be changed merely because Comparator 009 fails it.

Combined Sortino, payoff, PF, expectancy, Monte Carlo and degraded-cost PF are
already strongly passing and are not reasons for discretionary optimization.

## Scientific interpretation

Development is reopened only because Comparator 009 is not certification-ready.

No new mechanism may be proposed merely to make already-passing metrics look
better.

The research target is:

> Find a causal market-native edge refinement that reduces the true continuous
> drawdown and improves risk-adjusted return enough to pass the frozen Sharpe
> gate, while preserving the already-demonstrated edge across consumed eras.

## Observation-first requirement

Before defining Comparator 010, perform observation-only reconstruction of:

1. every trade in the exact stitched maximum-DD episode;
2. causal entry state and pre-entry evidence;
3. rapid-invalidation status;
4. post-entry fully closed-M1 cognitive trajectory;
5. first material-adverse observation;
6. management-context evolution;
7. destination / DOL state;
8. path efficiency / overlap / momentum;
9. analogous winners and losses outside the DD episode;
10. daily-R contributions that dominate Sharpe dispersion.

No date/fold lookup may become a decision rule.

No terminal outcome may become runtime authority.

## Allowed mechanism classes

A successor may use only trader-native causal edge:

- admission evidence quality;
- structure/liquidity confirmation;
- regime/context conjunctions;
- confirmation latency states that already exist;
- reclaim states that already exist;
- maximum-cognition post-entry reassessment;
- market-native stop/exit/target management;
- independently justified strategy-native R management.

## Forbidden mechanisms

Still forbidden for certification:

- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation;
- volume engineering;
- equity-based rescue;
- CIBO capital rescue;
- partition-specific logic;
- date/time lookup created from known losing trades;
- future bars;
- terminal-outcome authority;
- a threshold invented solely because it deletes one known loss.

## Success requirements for any Comparator 010 hypothesis

The exact same policy must run unchanged across R5, R6, R8 and recent consumed.

At minimum it must satisfy:

- no causal leakage;
- no fold/date identity authority;
- pure edge only;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- OOS/era PF >=1.50 in every consumed partition;
- combined PF >=1.70;
- combined expectancy >0R/trade;
- payoff >=1.20;
- all consumed partitions observed DD <=6R;
- **stitched chronological observed DD <=6R**;
- **combined annualized Sharpe >=1.50 under the already-frozen convention**;
- combined annualized Sortino >=2.00;
- MC positive terminals >=90%;
- MC p95 DD <=15R;
- degraded 0.10R all-in friction PF >1.0;
- temporal/regime robustness review survives;
- maximum applicable cognition remains fully accounted.

No candidate may be promoted from a single favorable partition.

## Stop rule

If no market-native, cross-fold mechanism can close both blockers without
damaging generalization, report that VT31 does not currently certify.

Do not relax:

- the 6R gate;
- the Sharpe gate;
- the frozen metric formula;
- pure-edge governance;

to manufacture certification.

## Governance

Fresh Holdout remains sealed.

Comparator 009 remains the baseline until a separately predeclared,
cross-fold-tested Comparator 010 actually survives this gate.

This document grants no LIVE, real-capital or production authority.
