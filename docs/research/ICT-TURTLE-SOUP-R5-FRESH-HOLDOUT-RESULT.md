# ICT Turtle Soup R5 — fresh holdout result

Date: 2026-09-16

## Identity

`ICT_TURTLE_SOUP_R5_D1_AUTHENTIC_IDEAL_C2__H4_AUTHENTIC_IDEAL_C2__POSITIONAL_DAILY_DOL`

## Frozen evidence

- holdout: `ICT_TS_R5_FRESH_2016_2018`
- evaluation: `[2016-05-01T21:00:00Z, 2018-05-01T21:00:00Z)`
- warm-up acquisition start: `2016-03-01T22:00:00Z`
- symbols: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY
- evidence status: `FRESH_RELATIVE_TO_DOCUMENTED_REPO_EVIDENCE`
- source: cTrader DEMO read-only M5

This evidence is now consumed and must never be represented as fresh again.

## Authoritative execution

- workflow: `QORE ICT Turtle Soup R5 Fresh Holdout 2016-2018`
- run: `35118222306`
- run conclusion: `SUCCESS`
- executed SHA: `9beb2f8147db2b9fb780bc4cc28e2cdb05b7851e`
- aggregate artifact: `10456151873`
- aggregate artifact digest: `sha256:eac25b64ae2edc555f674aefcbfb3ed69f2324b5c829811eaf2671deaa236272`
- quality gate: PASS
- preregistration: PASS
- all 7 symbol replays: PASS
- aggregate: PASS

## Aggregate economics

- trades: **12**
- gross wins: **5**
- gross losses: **7**
- gross total: **-2.729591923847292340308868588R**
- gross mean: **-0.2274659936539410283590723823R/trade**
- gross PF: **0.3565976737198141168589958446**
- primary friction: **0.05R/trade**
- primary total: **-3.329591923847292340308868588R**
- primary mean: **-0.2774659936539410283590723823R/trade**
- primary PF: **0.2871293722778321804090907008**
- primary max drawdown: **3.661757528942833741582753938R**
- stress friction: **0.10R/trade**
- stress total: **-3.929591923847292340308868588R**
- stress PF: **0.2326037789963570374396588729**

## By symbol

- AUDJPY: 2 trades, gross +0.7862705190R, primary +0.6862705190R
- AUDUSD: 0 trades
- EURUSD: 2 trades, gross -0.1183453747R, primary -0.2183453747R
- GBPJPY: 5 trades, gross -3.3074622922R, primary -3.5574622922R
- GBPUSD: 2 trades, gross +0.3987631155R, primary +0.2987631155R
- USDCAD: 1 trade, gross -0.4888178914R, primary -0.5388178914R
- USDJPY: 0 trades

No symbol selection or deletion is authorized from these consumed results.

## Decision

`ICT_TURTLE_SOUP_R5_D1_AUTHENTIC_IDEAL_C2__H4_AUTHENTIC_IDEAL_C2__POSITIONAL_DAILY_DOL = REJECTED_FOR_ADVANCEMENT`

The authentic same-timeframe Ideal Formation materially narrows signal frequency but does not demonstrate positive expectancy in this fresh holdout. The 12-trade sample is also too small to support promotion even aside from the negative economics.

Do not tune R5 in place from these results. Any new economic mechanics require a new candidate identity and must be source-derived or preregistered before accessing new evidence.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
