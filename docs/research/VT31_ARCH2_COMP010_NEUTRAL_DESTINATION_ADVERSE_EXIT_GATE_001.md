# VT31 NAS100 — Comparator 010 Neutral-Destination Adverse Exit Gate 001

**Status:** PREDECLARED PRE-HOLDOUT DEVELOPMENT GATE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Problem being addressed

Comparator 009 passes the sovereign observed-DD gate independently in R5, R6,
R8 and recent consumed, but the chronological stitched equal-R path still has:

- stitched observed DD: approximately `10.1497R`;
- annualized Sharpe under the already-frozen convention: approximately
  `1.2767`.

Required certification gates remain:

- stitched observed DD `<=6R`;
- annualized Sharpe `>=1.50`.

No metric formula, hard gate or capital rule may be relaxed.

## Observation-only forensic finding

The fully closed-M1 cognitive traces of Comparator 009 expose a repeated state
that was not used as runtime authority during the discovery:

1. the position is still in the pre-DOL1 / pretarget cognitive-management path;
2. `maximum_cognition_verified == true`;
3. causal `current_open_r <= -0.50R`, using the already-existing material
   adverse threshold;
4. `management_context == MIXED`;
5. `destination_state == NEUTRAL`;
6. entry family is `breaker` or `fair-value-gap`.

Across the four consumed partitions, the Comparator-009 traces contain
13 such Breaker/FVG materially-adverse NEUTRAL-destination trades:

- losses: 13;
- winners: 0;
- support spans R5, R6, R8 and recent consumed;
- four occur inside the stitched maximum-DD episode.

The only materially-adverse NEUTRAL-destination recovery observed in the
Comparator-009 traces belongs to the separate `order-block` family. Order
Block is therefore explicitly outside this hypothesis; it is not generalized
into Breaker/FVG destination semantics.

This support is discovery evidence only. It does not authorize a policy.

## Predeclared hypothesis

Comparator 010 may add exactly one new position-management authorization on
top of the complete frozen Comparator-009 policy:

`BREAKER_FVG_NEUTRAL_DESTINATION_ADVERSE_EXIT`

Authorize EXIT only when all are true on a fully closed M1:

- entry family is Breaker or FVG;
- maximum cognition is verified;
- current open-R is at or below the existing `-0.50R` material-adverse
  threshold;
- management context is `MIXED`;
- destination state is `NEUTRAL`;
- the normal Comparator-009 exit stack has not already exited.

Execution must occur at the **next M1 open**. Same-bar execution is forbidden.

No new numeric threshold is introduced.

## Causal interpretation

A Breaker/FVG position that is already materially adverse and whose full
cognition no longer identifies a directional destination has lost the
destination evidence that justified continuing to carry adverse inventory.

This is different from:

- an Order Block reclaim/reversion structure;
- a DEEP destination that can still justify holding through adverse excursion;
- a SHALLOW destination, which is not tested by this gate.

The hypothesis is therefore a destination-state risk-management rule, not an
outcome filter.

## Frozen Comparator-009 stack

Comparator 010 must preserve all Comparator-009 mechanisms unchanged:

Admission:

- `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- Breaker SHORT rotation/compressed conflict except bullish recovery;
- FVG SHORT compressed + FRESH_LT8M + FAST_LE5M conflict;
- Breaker SHORT prior-bearish + compressed + H1-bullish conflict;
- Rapid Breaker conflicts A and B;
- bullish-prior/cash-open/H1 Breaker SHORT + MID_6_10M conflict.

Position management:

- H3 full cognition;
- W5 soft DOL1;
- cognition-selected DOL2;
- post-acceptance PS2;
- causal current_open_r;
- Comparator-003 adverse exits;
- Breaker MIXED weak-efficiency adverse exit already present in Comparator 009.

Comparator 010 may change nothing else.

## Required evaluation

Run the exact same policy across:

- R5;
- R6;
- R8;
- recent consumed.

Then stitch all four partitions chronologically by `signal_at` and evaluate
the frozen final metric convention.

### Mandatory gates

- same policy on all partitions;
- no outcome authority;
- no fold identity authority;
- no date identity authority;
- no future bars;
- next-M1-open execution;
- pure edge only;
- no sizing/leverage/compounding/portfolio/capital weighting;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- density >=75% versus Comparator 009;
- era PF >=1.50 in every partition;
- all partition observed DD <=6R;
- combined PF >=1.70;
- combined expectancy >0R/trade;
- payoff >=1.20;
- stitched observed DD <=6R;
- annualized Sharpe >=1.50 under the already-frozen convention;
- annualized Sortino >=2.00;
- MC positive terminal >=90%;
- MC p95 DD <=15R;
- degraded 0.10R friction PF >1.0;
- temporal/regime review survives.

## Adjudication rule

This is a **single-hypothesis** gate.

If the new rule fails either stitched DD or Sharpe, it is not sufficient for
certification and must not be promoted merely because PF or expectancy improve.

If it damages winner preservation or any consumed era, reject it.

If it passes all economic gates, it may become a development survivor subject
to the remaining runtime parity, semantic, no-leakage and exact-freeze audits.

Fresh Holdout remains sealed throughout.
