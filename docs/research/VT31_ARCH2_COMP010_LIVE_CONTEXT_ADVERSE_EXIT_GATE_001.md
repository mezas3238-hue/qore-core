# VT31 NAS100 — Comparator 010 Live-Context Adverse Exit Gate 001

**Owner / CEO:** Sergio Meza  
**Status:** PREDECLARED CONSUMED-EVIDENCE DEVELOPMENT GATE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Objective

Close the two remaining pre-holdout certification blockers without sizing,
leverage, compounding, capital rescue or metric retuning:

1. stitched chronological observed DD: ~10.1497R -> <=6R;
2. frozen combined annualized Sharpe: ~1.2767 -> >=1.50.

Comparator 009 remains the control.

## Observation supporting this gate

Observation-only reconstruction of the frozen Comparator-009 rows found two
live post-entry conflict families after the existing material-adverse boundary
`current_open_r <= -0.50R`.

These families were identified only from consumed evidence and are not
authorized until cross-fold falsification completes.

### Hypothesis A — FVG loses H1 sponsorship

After a fully closed M1, authorize next-M1-open exit only when all are true:

- trade is still eligible for pretarget cognitive exit;
- maximum cognition is verified;
- `current_open_r <= -0.50R` (pre-existing material-adverse threshold);
- entry family is `fair-value-gap`;
- current H1 state is `mixed`;
- management context is `MIXED` or `CAUTIOUS`.

Causal thesis: an FVG position that is already materially adverse and no longer
has directional H1 sponsorship should not be held merely because the broader
structure has not yet printed terminal invalidation.

### Hypothesis B — long position conflicts with bearish M15

After a fully closed M1, authorize next-M1-open exit only when all are true:

- trade is still eligible for pretarget cognitive exit;
- maximum cognition is verified;
- `current_open_r <= -0.50R`;
- side is `LONG`;
- current M15 state is `bearish`;
- management context is `MIXED`.

Causal thesis: a materially adverse long position with bearish M15 and mixed
management support is an active timeframe conflict, not merely a losing
outcome.

### Hypothesis C — union

Authorize the existing Comparator-009 exits plus Hypothesis A OR Hypothesis B.

No new numeric threshold is introduced.

## Variants to run in one GitHub Trader Lab replay

1. `COMP009_CONTROL`;
2. `COMP010_FVG_H1_MIXED_ADVERSE_EXIT`;
3. `COMP010_LONG_M15_BEARISH_ADVERSE_EXIT`;
4. `COMP010_FVG_H1_OR_LONG_M15_ADVERSE_EXIT`.

The exact same policy must run unchanged across R5, R6, R8 and recent consumed.

## Execution causality

Decision information must come only from the fully closed M1 observation.

When an exit is authorized, execution occurs at the **next M1 open**.

Forbidden:

- same-bar close execution;
- future-bar access;
- terminal outcome authority;
- date/fold identity authority.

## Required cross-fold gates

For promotion to a Comparator-010 survivor:

- PF non-degrade versus Comparator 009: 4/4;
- mean-R non-degrade: 4/4;
- DD non-degrade: 4/4;
- density >=75%: 4/4;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year non-degrade;
- era PF >=1.50 in every partition;
- each partition observed DD <=6R;
- recent MC positive >=90%;
- recent MC p95 DD <=15R.

## Required stitched gates

The same variant must also satisfy on the chronologically stitched equal-R path:

- observed DD <=6R;
- combined PF >=1.70;
- combined expectancy >0R/trade and >=+0.15R direction;
- payoff >=1.20;
- annualized Sharpe >=1.50 under the already-frozen convention;
- annualized Sortino >=2.00;
- MC positive >=90%;
- MC p95 DD <=15R;
- degraded 0.10R friction PF >1.0.

## Governance

This is PURE EDGE research.

Forbidden for certification:

- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation;
- equity-dependent rescue;
- CIBO capital rescue;
- formula retuning after results.

Fresh Holdout stays sealed.

A green GitHub Trader Lab result is a development survivor only. It is not
certification, LIVE authorization, real-capital authorization or production
authorization.
