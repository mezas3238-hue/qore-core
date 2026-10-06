# VT31 NAS100 — Causal Fill-Time Thesis Revalidation Gate 001

**Status:** PREDECLARED DEVELOPMENT RESEARCH GATE  
**Baseline:** truthful Comparator-009 stack after cognitive-plumbing repair  
**Fresh Holdout:** SEALED

## Observation motivating the gate

The cognitive sensor audit isolated 17 admitted trades with zero post-entry
cognitive calls. Timeline reconstruction shows all 17:

- eventually fill;
- terminate by structural invalidation;
- lose raw -1R;
- hit terminal invalidation exactly one M1 after the actual fill.

The signal-to-fill delay varies, but after fill no fully closed M1 decision
exists early enough for post-entry cognition to intervene.

Therefore this class is an order-lifecycle / fill-observability problem, not a
late position-management problem.

## Hypothesis

VT31 should not blindly accept an executable setup whose market context may
have evolved between the original decision and the actual fill.

Immediately before accepting a fill opportunity, revalidate the **frozen entry
thesis** using the maximum causal intelligence available at that moment.

## Causal timing

For a prospective fill at M1 open T:

- use only bars whose close timestamp is <= T;
- do not use T's high, low or close;
- retain the original source setup, selected family and frozen thesis;
- rebuild the current Situation Model as of T;
- run the canonical position/entry reasoning revalidation;
- accept the fill only if the frozen thesis remains executable under current
  causal evidence.

No future bar may influence the decision.

## Fill-stage intelligence readiness

The fill-time check occurs before a position exists. Therefore the readiness
check must distinguish **entry/fill intelligence** from blockers that only
describe later position-management calibration.

The fill may proceed only when current reasoning is `EXECUTE` and none of
these entry-relevant blockers is present:

- `M15_CONTEXT_UNWIRED`;
- `H4_CONTEXT_UNAVAILABLE`;
- `H1_CONTEXT_UNAVAILABLE`;
- `STRUCTURE_CONTEXT_UNAVAILABLE`;
- `VOLATILITY_CONTEXT_UNAVAILABLE`;
- `ENTRY_INTELLIGENCE_UNAVAILABLE`.

The following blockers may be recorded but are not fill-veto authority because
the position does not yet exist:

- deeper DOL target calibration;
- DOL2/DOL3 target intelligence;
- contextual post-entry position management;
- current-position R state.

This distinction is frozen before economic replay and does not relax
post-entry maximum-cognition certification requirements.

## No time threshold

The mechanism may not introduce a rule such as:

- cancel after N minutes;
- cancel after a mined delay threshold.

Revalidation is event-driven by the actual fill opportunity, regardless of
whether the delay was short or long.

## Research variants

The first frontier must include:

1. CONTROL — current Comparator-009 fill behavior;
2. FILL_REVALIDATE_REASONING — accept prospective fill only if current
   canonical reasoning remains EXECUTE and maximum-intelligence accounting is
   available;
3. optionally a fail-closed diagnostic variant where unavailable mandatory
   intelligence rejects the fill, provided this is reported separately.

No additional market filter may be added in the same experiment.

## Required accounting

Report by fold:

- prospective fill count;
- fills accepted/rejected;
- rejected winners/losses;
- zero-call structural-invalidating losses rejected/preserved;
- winner count/R preservation;
- density;
- PF, expectancy, observed DD;
- half-year stability.

Then stitch chronological consumed folds and test frozen:

- observed DD <=6R;
- Sharpe >=1.50;
- Sortino >=2.00;
- combined PF >=1.70;
- expectancy >=+0.15R;
- payoff >=1.20;
- degraded 0.10R PF >1.

Monte Carlo runs only after deterministic gates survive.

## Governance

Pure edge only. No sizing, leverage, compounding, portfolio weighting, capital
allocation, equity state, fold/date identity or terminal outcome authority.

Fresh Holdout remains sealed. No certification/LIVE authority.
