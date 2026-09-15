# Turtle Soup Persistence Candidate P1 — Preregistered causal freeze

## Governance

Research identity: `turtle-soup-persistence-candidate-p1`

This is a materially new research identity created after the closed R1–R6 Turtle Soup line. It is not R7 parameter tuning and it does not reopen any rejected candidate. The protected fresh OOS beginning `2026-03-01T00:00:00Z` remains embargoed and MUST NOT be read or used.

The only evidence permitted for design is the already-consumed R5/R6 development evidence plus post-R6 forensics. No result from this P1 replay may be used to alter P1 parameters after execution.

## Causal hypothesis

The original Turtle Soup event often produces a temporary bounce but not a persistent reversal. P1 treats the original same-session trigger as a **virtual probe**, not as a risk-bearing trade. A trade is allowed only after the reversal survives the source session and remains reclaimed into the next session.

This directly targets the four forensic findings without market/side selection:

1. `REVERSAL_PERSISTENCE_FAILURE`: require close-confirmed persistence before capital entry.
2. `RIGHT_TAIL_INSTABILITY`: use a finite +2R target rather than depending on rare giant runners.
3. `INITIAL_STOP_COST_GEOMETRY`: require actual post-confirmation entry risk >= 4 bps, which caps a 1 bp round-trip cost burden at <= 0.25R.
4. `MARKET_SIDE_NON_STATIONARITY`: retain all seven markets and both sides; strengthen stability gates rather than dropping historically weak pockets.

## Frozen signal source

- Reuse the exact R5 causal Classic fill census and resolver.
- Expected deterministic source fills: 290.
- Universe unchanged: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY.
- Both LONG and SHORT retained.
- Original Classic 5-tick trigger offset remains unchanged.
- No new market data acquisition is authorized.

## Frozen P1 execution mechanics

For each deterministic R5 source fill:

### 1. Virtual probe

The original Classic fill is observed without taking risk.

The probe FAILS if the original structural stop is hit after the virtual fill and before the source D1 session closes.

### 2. Persistence confirmation at source-session close

If the probe survives:

- LONG requires source D1 close `> max(original trigger, original fill price)`.
- SHORT requires source D1 close `< min(original trigger, original fill price)`.

Otherwise abstain.

### 3. Next-session causal entry

Entry occurs at the immediately following provider D1 session OPEN, never at the confirming close.

Fail closed / abstain if:

- next session is unavailable or begins at/after protected OOS;
- complete M15 containment for the entry session is unavailable;
- LONG next open is `<= original trigger`, or SHORT next open is `>= original trigger`;
- next open is already beyond the original structural stop on the adverse side.

Candidate stop = original Classic structural stop.

### 4. Cost geometry gate

At the actual next-session entry:

`risk_bps = abs(entry - stop) / entry * 10000`

Require `risk_bps >= 4.0`.

This value is not optimized: it is derived directly from the fixed 1 bp primary round-trip cost budget so that primary transaction cost is no more than 0.25R.

### 5. Exit contract

- Fixed target: `+2R` from actual P1 entry.
- Fixed maximum holding horizon: 3 provider D1 sessions including the entry session.
- Structural stop remains unchanged for the entire trade.
- No trailing stop.
- No break-even rule.
- No re-entry.
- No partial exit.

Each D1 session is traversed through its exact contained M15 sequence. Within an M15 bar:

- adverse gap through stop => exit at M15 open (`gap-stop`);
- favorable gap through target => conservative fill at target;
- stop only touched => stop;
- target only touched => target;
- both stop and target touched in the same M15 => conservative `stop-first` resolution.

At the end of the third session, an open position exits at that D1 close (`time-exit`).

## Costs

- Primary: 1.0 bp round trip.
- Stress: 2.0 bp round trip.

Costs are expressed in R using the actual P1 entry-to-stop risk.

## Walk Forward

Reuse the exact six frozen folds:

- WF1: 2024-09-01 .. 2024-12-01
- WF2: 2024-12-01 .. 2025-03-01
- WF3: 2025-03-01 .. 2025-06-01
- WF4: 2025-06-01 .. 2025-09-01
- WF5: 2025-09-01 .. 2025-12-01
- WF6: 2025-12-01 .. 2026-03-01

## Frozen advancement gates

All must pass:

1. >= 30 closed Walk-Forward trades.
2. Walk-Forward mean net R > 0.
3. Walk-Forward PF > 1.
4. >= 4/6 positive folds.
5. Stress 2 bp mean R >= 0.
6. Leave-one-market-out total R > 0 for all seven markets.
7. Positive gain concentration <= 50% on existing market/year/side axes.
8. Both LONG and SHORT Walk-Forward total R > 0.
9. At least 5 of 7 markets have positive Walk-Forward total R.
10. Causal integrity fail-closed.

No gate may be relaxed after seeing P1 results.

## Decision

If all gates pass: `P1_DEVELOPMENT_GATE_PASS` and only then a separate candidate/config freeze may be considered before any fresh OOS action.

Otherwise: `P1_PERSISTENCE_CANDIDATE_REJECTED`.

Regardless of result, this P1 run does not itself authorize fresh OOS, candidate promotion, DEMO, LIVE, production, prop-firm execution, or capital deployment.
