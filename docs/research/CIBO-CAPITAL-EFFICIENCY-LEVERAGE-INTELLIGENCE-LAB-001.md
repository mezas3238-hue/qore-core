# CIBO Capital Efficiency / Leverage Intelligence Lab — Slice 001

> **PROGRAM CONTINUITY:** This Slice 001 contract is now governed by the master CE2I roadmap:
> `docs/research/CIBO-CAPITAL-EFFICIENCY-EXPOSURE-INTELLIGENCE-MASTER-ROADMAP-V1.md`
>
> This file remains the authoritative contract for the first static sizing slice. The roadmap is the
> authoritative source for program scope, future phases, capitalization tools and continuity order.
>
Status: **RESEARCH ONLY / DRAFT / NO EXECUTION AUTHORITY**

## Objective

Study whether QORE can obtain materially more economically useful market exposure
from the same bounded loss budget and/or a smaller margin commitment.

The target is **capital efficiency**, not free leverage.

~~~text
MAXIMIZE USEFUL EXPOSURE
SUBJECT TO:
  VERIFIED STRATEGY INVALIDATION
  STOP-RISK BUDGET
  MARGIN BUDGET
  BROKER VOLUME BOUNDS
  BROKER VOLUME STEP
~~~

This slice never creates, submits, changes or closes an order. It cannot issue a
Risk authorization and it cannot alter a Trader stop.

## Source finding

The current QORE source has the ingredients but not one common optimizer:

- broker_risk_sizing.py maps monetary stop risk into broker volume.
- account_wide_risk.py independently constrains an execution request by shared
  stop-risk and margin capacity.
- ctrader_demo_allocation_only.py preserves the requested volume in the free
  cTrader DEMO environment after assigning virtual Trader capital.
- PR #637 proves that requested-volume construction is currently fragmented across
  the seven active DEMO Traders.
- CF-06 CIBO Portfolio / Allocation Intelligence is recommendation-only; it does not
  own Risk or execution authority.

Therefore the first missing research primitive is a deterministic way to measure
the exposure/risk/margin frontier before any integration proposal.

## New research primitive

src/qore/infrastructure/cibo_capital_efficiency_sizing_lab.py

For one frozen geometry the lab consumes:

- assigned capital;
- stop-risk budget;
- margin budget;
- stop loss per volume;
- margin per volume;
- normalized exposure per volume;
- broker minimum/maximum/step;
- optional observed baseline volume;
- explicit geometry provenance;
- explicit structural-stop verification.

It computes the maximum step-aligned research volume bounded by both:

~~~text
volume <= risk_budget / stop_loss_per_volume
volume <= margin_budget / margin_per_volume
volume <= broker_max_volume
~~~

and refuses a result below broker minimum volume.

## Hard anti-cheating invariant

~~~text
TIGHTER STOP FOR MORE SIZE
WITHOUT VERIFIED TRADER STRUCTURE
!= CAPITAL EFFICIENCY
~~~

The lab fails closed unless structural_stop_verified is true.

A future experiment may compare a more precise stop only when that stop is produced
by the frozen Trader methodology or a separately governed Trader research candidate.
CIBO cannot manufacture a tighter invalidation to create apparent leverage.

## Metrics emitted

Each feasible experiment records:

- authorized research volume;
- stop risk in USD;
- margin committed in USD;
- normalized exposure;
- exposure / stop-risk dollar;
- exposure / margin dollar;
- risk-budget utilization;
- margin-budget utilization;
- risk / assigned capital;
- margin / assigned capital;
- baseline exposure;
- exposure gain multiple versus baseline;
- exact binding constraints.

These are research measurements. They are not a recommendation to trade larger.

## Pareto frontier

The lab can reduce multiple experiments to a Pareto frontier.

Experiment A dominates B only when A has:

- at least as much exposure;
- no more stop risk;
- no more margin commitment;
- and a strict improvement in at least one dimension.

This makes it possible to compare provider economics, structural invalidation
precision and sizing policies without collapsing them into a single arbitrary score.

## Research hypotheses

### H1 — Unused-budget inefficiency

Some current fixed/frozen sizing paths may leave meaningful stop-risk or margin
headroom unused after broker step quantization.

Falsification:

- reconstruct actual executed sizes;
- calculate the verified feasible frontier at the same decision timestamp;
- if exposure gain is negligible after costs/constraints, reject H1 for that cell.

### H2 — Margin efficiency can be a distinct edge

Two implementations with the same strategy geometry and stop risk can consume
different margin for equivalent exposure because provider/contract economics differ.

Falsification:

- compare like-for-like economic exposure;
- require the same frozen signal/geometry;
- include actual provider margin terms;
- reject any apparent advantage caused only by inconsistent contract normalization.

### H3 — Structural precision can create exposure efficiency

A genuinely more precise causal invalidation may permit more volume for the same
monetary stop-risk budget.

This is valid only if the narrower invalidation does not destroy the strategy.

Required later validation:

- stop-loss incidence;
- PF;
- total R;
- drawdown;
- MAE/MFE;
- adverse excursion around the new invalidation;
- slippage/spread sensitivity;
- WFO / sealed holdout stability.

If the tighter structural stop increases stop frequency enough to degrade expectancy,
the apparent sizing gain is rejected.

### H4 — Capital recycling

When verified open risk is reduced through partial realization or a valid protective
stop, some previously consumed risk capacity may become reusable.

This is **not implemented in Slice 001**. It requires exact position-state,
reservation and reconciliation semantics so that the same capacity cannot be spent
twice.

## Experimental chain

1. Reconstruct baseline from PR #637 behavior evidence.
2. Normalize broker economics.
3. Run static frontier at the same timestamp and same frozen geometry.
4. Segment by Trader, market, session, side, volatility/spread regime and sizing path.
5. Reject false efficiency caused by contract mismatch, future outcomes or fake stops.
6. Only then study correlation, capital recycling, dynamic de-risking and path-aware sizing.

## Acceptance measurements for the research program

No single metric is sufficient. Later replay must report at minimum:

~~~text
EXPOSURE_GAIN_MULTIPLE
STOP_RISK_USD
MARGIN_COMMITTED_USD
EXPOSURE_PER_STOP_RISK_DOLLAR
EXPOSURE_PER_MARGIN_DOLLAR
RISK_BUDGET_UTILIZATION
MARGIN_BUDGET_UTILIZATION
PEAK_SIMULTANEOUS_MARGIN
PEAK_SIMULTANEOUS_STOP_RISK
NEXT-OPPORTUNITY_CAPACITY
PF
TOTAL_R
DRAWDOWN_R
LOSS_STREAK
PROBABILITY_OF_RUIN / MONTE_CARLO SURVIVABILITY
~~~

Slice 001 only establishes deterministic sizing math and the anti-cheating boundary.

## Authority boundary

~~~text
CIBO CAPITAL-EFFICIENCY RESEARCH
!= RISK AUTHORIZATION
!= EXECUTION AUTHORITY
!= LIVE SIZE CHANGE
~~~

QORE Risk remains sovereign for account/risk/margin admission.
Trader methodology remains sovereign for entry, stop and target geometry.

No VPS, broker, DEMO execution or LIVE configuration is changed by this slice.
