# TURTLE SOUP XAUUSD R3 — CIBO JOURNEY ROUTER FREEZE

Identity: `TURTLE_SOUP_XAUUSD_R3_CIBO_JOURNEY_ROUTER`

Status: research candidate over already-consumed CIBO evidence. This document does **not** authorize demo, live, real-capital or production operation.

## Why R3 exists

R2 incorrectly treated CIBO intelligence as a collection of additive trade filters and then required a positive predicted-R score. That architecture is retired. CIBO is used here as journey intelligence: it helps route **where to enter, where the idea is structurally invalid, which active liquidity destination is the target, and when the journey has no executable route**.

## Frozen setup

Turtle Soup formation remains:

1. Prior-source-candle liquidity reference.
2. Liquidity raid beyond that reference.
3. Exact C2 reversal closure:
   - LONG: `c2.low < c1.low and c2.close > c1.low`
   - SHORT: `c2.high > c1.high and c2.close < c1.high`
4. Causal CISD reproduced from the lower timeframe.
5. H1 and H4 source frames, LONG and SHORT.
6. C3 remains `UNRESOLVED_NO_FROZEN_C3_CONTRACT` and is not invented in R3.

## CIBO execution routing

CIBO is not a binary score filter.

### Entry routes

The router may choose one of two causal entry mechanisms:

- `NEXT_SOURCE_OPEN`: the next source open after completed C2/CISD.
- `CISD_THRESHOLD_RETEST`: after C2 has closed, wait up to one source period for a retracement to the causal CISD threshold. If the Protected Swing is invalidated first or price never retraces, there is no fill. There is no hindsight fallback to another entry after observing the no-fill.

### Stop / invalidation

Stop is always the exact causal CISD Protected Swing, with no arbitrary pip, ATR or percentage offset.

### Target / DOL routes

At the causal decision point R3 may route to an active, directionally-ahead, still-untouched CIBO Target Destination V2 family:

- `SOURCE_OPPOSITE`
- `PRIOR_H1`
- `PRIOR_H4`
- `PRIOR_D1`
- `SWING_H1`
- `SWING_H4`
- `SWING_D1`

Within a selected family the nearest still-active candidate is used. Target Destination V2 is explicitly a bounded supported reference universe, not a claim that all possible ICT DOLs have been enumerated.

If a retest entry fills after the originally visible DOL in the selected family has already been consumed, the route is a structural no-trade unless another candidate in the **same frozen family** remains active. The router does not switch target families after seeing what happened.

### Abstention

R3 abstains only for structural/execution reasons in this contract, including:

- no exact causal CIBO episode match;
- no causally available DOL route;
- invalid entry/Protected-Swing geometry;
- Protected Swing invalidated before a retest fill;
- no CISD-threshold retest within the allowed source period;
- selected DOL family consumed before fill with no same-family replacement;
- existing R3 position still active under the one-position replay rule.

There is **no `predicted_primary_r > 0` trade filter**.

## What is not an entry filter

Session, weekday, FVG presence, exact equal liquidity and similar CIBO descriptive fields remain diagnostic unless separately promoted through causal evidence. They do not independently veto or authorize a Turtle Soup setup in R3.

The route state used for this research router is limited to pre-entry structural context:

- source timeframe;
- side;
- prior-body alignment;
- CISD progress bucket within the source candle;
- source-range-state bucket.

These fields choose among available execution actions; they do not decide whether a setup exists.

## Causal / leakage rules

The following are forbidden as routing inputs:

- MFE;
- MAE;
- whether a target was ultimately hit;
- target touch time that had not yet occurred at the simulated decision time;
- exit reason;
- future price path.

Target V2's stored touch timestamp may only be used to determine whether a destination had **already** been consumed by the simulated decision/fill timestamp.

## 10Y research protocol

Source XAUUSD M5 corpus:

- run `35166210458`
- retained bars `707716`
- interval `[2016-09-17, 2026-09-17)`

Source CIBO Target Destination V2:

- run `35204892665`
- XAUUSD artifact `10489343458`
- digest `sha256:61f60ee5df2507c3f7eca02fef1bc9252f0eaae0a428b47a6027882a7b74bfff`

The 10-year corpus is **consumed development evidence and is not a fresh holdout**.

Temporal split frozen before R3 replay:

- route-model development: `[2016-09-17, 2022-09-17)`
- internal temporal validation: `[2022-09-17, 2026-09-17)`

The validation block is not used to fit route means.

Route choice uses a shrinkage map over available actions. It always chooses the highest expected route among causally available actions; it does not require that expected value to be positive. This is a routing model, not R2's trade-acceptance filter.

## Replay mechanics

- friction: `0.05R` primary and `0.10R` stress;
- stop/target touched in the same M5 bar: `STOP_FIRST`;
- maximum lifecycle: 24 hours, aligned with Target Destination V2's supported outcome horizon;
- one active R3 position at a time;
- no automatic promotion from this replay.

## Governance

`fresh_holdout = false`

`automatic_promotion_allowed = false`

`demo_eligible = false`

`live_authorized = false`

`real_capital_authorized = false`

`production_authorized = false`

A successful CI run or favorable consumed-corpus result is not certification. A genuinely independent sealed holdout remains required after a final candidate is frozen.
