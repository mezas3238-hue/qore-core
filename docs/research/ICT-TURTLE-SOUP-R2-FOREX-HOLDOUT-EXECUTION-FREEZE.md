# ICT Turtle Soup R2 — Forex Holdout Execution Freeze

Status: PRE-RESULT / ONE-SHOT
Identity: `ICT_TURTLE_SOUP_R2_ALL_SESSION_MULTI_ASSET`
Carrier: `agent/ict-turtle-soup-r2-forex-holdout-001`
Holdout source: retained Core evidence from run `34759027136`
Holdout evaluation: `[2020-07-01T00:00:00Z, 2022-07-01T00:00:00Z)`

This document closes execution ambiguities before any ICT Turtle Soup R2 holdout P&L is opened. No rule below may be changed after result access under this identity.

## Available retained Forex cohort

The retained Core holdout contains exactly these seven symbols for this replay:

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- GBPJPY
- AUDJPY

This is a Forex-only holdout slice. It does not adjudicate indices or metals.

## Evidence policy

- Reuse retained artifacts only; do not recollect the protected holdout.
- Native M5 is the decision and replay timeframe.
- M1 is not used to improve ordering after results; unresolved same-M5 stop/target ordering is STOP-first.
- The 30-day pre-evaluation acquisition interval is warm-up only and cannot contribute economic trades.
- All timestamps are interpreted with `America/New_York` DST-aware session construction.

## Frozen objective liquidity families

1. Previous New-York calendar trading-day high/low: `[00:00, 24:00)` New York; becomes known at the next New-York midnight.
2. Previous completed New-York week high/low: Monday `00:00` through next Monday `00:00`; becomes known at the next Monday midnight.
3. Completed Asia range: `[20:00, 00:00)` New York, ending at New-York midnight.
4. Completed London range: `[02:00, 05:00)` New York.
5. Completed New-York AM range: `[08:30, 11:00)` New York.
6. Completed New-York PM range: `[13:30, 16:00)` New York.

Only pools fully completed before an event are causal. No equal-high clustering, discretionary swings, FVG, breaker, order block or NWOG are admitted in this holdout.

## Event selection

- Time-of-day is not an eligibility filter.
- Scan events chronologically on M5.
- A same M5 bar that sweeps more than one currently eligible same-side pool is `AMBIGUOUS_MULTI_POOL_SWEEP` and abstains; no hindsight priority is invented.
- An event must satisfy the frozen R2 causal sequence: qualified pool -> sweep -> reclaim -> CISD -> next-M5-open entry.
- The target is the nearest positive-reward opposing qualified pool known before entry.
- Minimum projected geometry remains `1.5R`.
- One open position maximum per symbol. Events while a position is open are ignored. New events after a flat exit are allowed.
- LONG and SHORT remain enabled.

## Risk and lifecycle

- Stop: one native minimum-price increment beyond the adverse sweep/CISD extreme, as frozen in the R2 core.
- Target: frozen opposing-liquidity target carried by the signal.
- No trailing, break-even, partials, scaling or re-entry.
- This Trader Library program is intraday: every position is flattened before the New-York calendar date changes.
- If an M5 opens through the adverse stop, exit at that M5 open (gap loss may exceed `-1R`).
- If an M5 opens favorably beyond the target, credit only the frozen target price; no positive gap slippage.
- If stop and target are both touched inside the same M5 without finer frozen chronology, STOP wins.
- Otherwise the first single-sided touch exits at stop or target.
- If neither is reached, exit at the final available M5 close before New-York midnight (`time-exit`).

## Friction

Primary normalized friction: `0.05R` per closed trade.
Stress friction: `0.10R` per closed trade.

Report gross R, primary-net R and stressed-net R. No symbol-specific post-result cost tuning is permitted.

## One-shot reporting

Report at minimum:

- signal / abstain funnel;
- closed-trade count;
- gross and net total/mean R;
- profit factor;
- win/loss/flat counts;
- max drawdown and longest losing streak;
- LONG vs SHORT;
- each symbol;
- leave-one-symbol-out totals;
- year and quarter;
- session/hour-of-entry diagnostics;
- target / stop / gap-stop / time-exit counts;
- positive-gain concentration;
- stress result.

The holdout is diagnostic/economic evidence only. No rule changes after reading it. Any forensic-derived change requires a new research identity.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
