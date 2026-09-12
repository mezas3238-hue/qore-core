# VT-08 R3.11 Risk-aware economic replay

Status: **RESEARCH ONLY**. This document does not grant `DEMO_ELIGIBLE`, does not
change the VT-08 source methodology, and does not authorize access to the
protected 2020-2022 candidate holdout.

## Evidence boundary

The replay may consume only the already-consumed runs:

- Fresh 2022-2024: run `34707771460`.
- Baseline 2024-2026: run `34693803930`.

The executable fails closed if any trade timestamp is earlier than
`2022-08-13T00:00:00Z`. The protected interval `2020-08-13 -> 2022-08-12`
remains unopened.

## Frozen primary research policy

The policy was selected before this Risk-aware account replay was executed:

- normalized research account: `USD 100,000`;
- desired bounded loss at stop: `50 bps` (`0.50%`) of current equity per trade;
- maximum aggregate open bounded-loss heat: `150 bps` (`1.50%`) of current equity;
- quantity is rounded down to the exact historical cTrader broker volume step;
- quantities below broker minimum are `REJECT`;
- broker maximum or portfolio-heat reductions are `REDUCE`;
- otherwise the research Risk outcome is `ALLOW`;
- the Trader's side, entry, stop, target, anchors, lifecycle, and source
  fingerprint are never mutated by Risk.

The replay uses event-time accounting. Positions that exit at a timestamp are
closed before a new signal at that same timestamp is admitted.

## Currency conversion

P&L and bounded loss are expressed in USD:

- USD-quoted pairs use a factor of `1`;
- USD-base pairs use `1 / instrument_price`;
- JPY crosses use the most recent historical `USDJPY` M15 open at or before the
  event timestamp.

This permits fixed-loss sizing to be compared across the seven Forex markets
without treating raw percentage price movement as account P&L.

## Cost policy

Historical trendbars do not contain a complete realized bid/ask, commission,
and slippage ledger. Therefore R3.11 does **not** invent a cTrader cost.

It reports zero-cost economics plus a preregistered completed-trade price-cost
stress grid in basis points:

`0, 0.1, 0.25, 0.5, 1, 2 bp`.

The cost is converted consistently into USD account P&L and net R after the
fixed-risk quantity has been determined. It is labeled a stress proxy, not an
observed broker cost. The replay also computes the price-cost break-even point
for Candidate A and Candidate B in each consumed window and combined.

## Scopes

The replay reports the already-defined research populations only:

- `broad`: all 809 consumed VT-08 narrow-C2 trades;
- `candidate-a`: `AUDJPY SHORT + GBPUSD SHORT`;
- `candidate-b`: `GBPJPY ALL + AUDJPY SHORT + GBPUSD SHORT`.

Candidate A and B remain post-hoc research hypotheses. Running this replay does
not convert either into an independently validated strategy.

## Risk authority boundary

QORE's formal Risk authority remains downstream of OrderIntent and owns formal
`ALLOW/REDUCE/REJECT` admission and authorization. The existing Risk budget
engine is primarily notional-budget based; it does not yet derive quantity from
an account-loss target and stop distance.

R3.11 therefore provides a deterministic **research sizing and economic replay**
for the missing fixed-loss dimension. It does not manufacture historical
`RiskAuthorization` objects because the historical account-state snapshots
needed for such authorizations do not exist. If fixed-risk economics survive
cost, multiplicity, and fresh validation, the sizing rule must be integrated
into the formal Risk path before DEMO execution qualification.

## Decision rule

No candidate may be promoted from R3.11 results alone. Before opening 2020-2022
we still require a frozen economic/cost model, multiplicity treatment, one
Primary candidate (and at most one explicitly penalized Challenger), and exact
fresh-holdout pass/fail criteria.
