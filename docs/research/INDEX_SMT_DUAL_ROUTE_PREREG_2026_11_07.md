# SMT dual-route indices — preregistered research prototype (2026-11-07)

Status: **RESEARCH ONLY / NO LIVE / NO MERGE / NO VPS / NO ORDERS**.

## Owner mandate
Investigate SMT divergence across **SPX500, NDX100 and US30** both as:
- **Route A** CRT H4 + SMT divergence + closed MSS (confirmation of an existing CRT).
- **Route B** independently qualified liquidity sweep + SMT divergence + closed MSS (no valid CRT).

This module deliberately DOES NOT change CRT RADAR V34.12X, CRT seven-family
detection, VT08 CRT PURE, indicator Pine, funded accounts, QORE Risk or
production connectors. Source candle parity remains independently unapproved
under [PR #1005](https://github.com/mezas3238-hue/qore-core/pull/1005).

## Exact R0 hypothesis (QORE engineering, NOT an author-certified ICT rule)
Input: three separate, same-feed, closed M15 OHLC streams with exact common UTC
timestamps. No missing bars in the last lookback+1 sample, no cross-feed mixing.
Default prior-window lookback: 8 completed bars (120 minutes); tune only in
new, explicitly versioned research after a new preregistration.

For each pair, at end t:
- **Bearish**: one index high(t) strictly exceeds max(highs t-8..t-1)
  and closes strictly below that previous maximum (sweep + reclaim);
  the other index's high(t) does NOT exceed its own corresponding maximum.
- **Bullish**: one index low(t) strictly falls below min(lows t-8..t-1)
  and closes strictly above that previous minimum; the other index's
  low(t) does NOT fall below its own corresponding minimum.
- Exact highs/lows ties do not constitute breaks.
- This rolling-window operationalization is NOT a synchronized swing-pivot
  detector. The next phase must contrast with causal confirmed-swing SMT and
  sensitivity to feed, candle phase and clock alignment.
- Pairs in priority order: SPX500/NDX100, SPX500/US30, NDX100/US30.
  Multiple paired divergences of the same direction deduplicate to at most
  one research opportunity per instrument/direction at evaluation time.

## Evidence-based dual-route qualification
Output: `ResearchOpportunity(status="RESEARCH_ONLY")`, **not** an alert or order.

At observation clock t:
1. A candidate SMT must already exist, closed at or before t, age <=60m.
2. Closed MSS evidence for the instrument must be direction-aligned; its
   confirming close must cross its specified protected swing by price,
   with time at or before t. The event and MSS timestamps must be within 60m.
3. Default research evaluation window is 09:30 inclusive to 11:30 exclusive
   **America/New_York**, with zone-aware DST and weekdays only.
4. Existing **valid, direction-aligned CRT** selects Route A.
5. No valid CRT selects Route B. An active CRT in the opposing direction
   explicitly **blocks**, rather than being mislabeled "no CRT".
6. Opposite simultaneous SMT directions for one index abstain.
7. If one data/feed/time/MSS requirement is absent, the engine abstains.

CRT and MSS evidences are presently **independent input contracts** supplied by
a future verified adapter. They are not invented or rebuilt from this module.
The `MSS` verifier checks timestamp/direction/price-vs-protected-level only;
actual source M5 candles, true protected-swing ownership and feed/phase parity
MUST be cross-checked by the integration gate before any external notification.

## Research evaluation plan (not yet run)
- Freeze event definitions **before** inspecting historical outcomes.
- Three years, full chronological replay; strictly separated development vs
  untouched holdout, with market-day grouping for correlated indices.
- Compare A: CRT+MSS, B: CRT+SMT+MSS, C: SMT+sweep+MSS without CRT,
  D: baseline A plus independent C.
- Report candidates, abstentions, per-symbol and per-pair density, average R,
  PF, MAE/MFE, transaction costs, MAXDD, opportunity concentration, and
  walk-forward + post-freeze OOS tests. Include spread/commission/slippage and
  funded-account volume/margin constraints.
- No synthetic bars, future-swings, lookahead or after-the-fact reassignment.
- Trades on correlated indices must be grouped by the same underlying event
  to avoid hidden double/triple exposure. Metrics after costs decide promotion.
- Validate that historical cTrader/ICMarkets sources match the actual execution
  symbol semantics before making financial claims.

## Gates and known blockers
- G0: standalone deterministic candidate algorithm — implemented, local test
  definitions committed; CI must confirm.
- G1: actual synchronized historical cTrader M15 feed for all three indices,
  broker symbol metadata and schedule — **missing**.
- G2: CRT seven-family authoritative validated event adapter — **missing**.
- G3: audited M5/M15 MSS causal detector / protected-swing evidence — **missing**.
- G4: real broker cost model, futures/CFD parity and news calendar — **missing**.
- G5: preregistered historical replay, OOS and independent review — **NOT DONE**.
- G6: Owner explicit approval for any alerts, account, demo or LIVE — **NOT GIVEN**.

**No real SMT signal is asserted for the November 5 screenshots**; the price
axis visual estimates and unsynchronized chart layouts cannot certify SMT.
