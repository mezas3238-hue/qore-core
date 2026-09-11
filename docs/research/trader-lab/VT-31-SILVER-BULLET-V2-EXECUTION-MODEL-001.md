# VT-31 Silver Bullet V2 — Research Execution Model 001

Status: RESEARCH ONLY — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY

## Purpose

This document freezes the historical execution semantics used to test the
source-bound VT-31 V2 methodology without importing the legacy V1 M5 model or
inventing trade-management rules not present in the source.

## Decision-time contract

- Authorized research market: `NAS100` only for this exact source-derived variant.
- Timezone: `America/New_York`, DST-aware.
- Reference range: exact 09:00-10:00 New York hour, derived from 60 closed M1 bars.
- Entry window: `[10:00, 11:00)` New York.
- Decision resolution: M1 only.
- Required sequence: reference-range raid -> post-raid structure shift ->
  source-configured entry model.
- Current frozen entry model: post-confirmation FVG consequent encroachment.
- Stop: raid extreme.
- Target: opposite side of the frozen 09:00-10:00 range.

## Pending-order lifecycle

A setup becomes actionable only after the confirming M1 candle has closed.
Therefore the backtest never permits a fill inside a candle that was already
needed to create the decision.

The limit order may fill on a later M1 bar while the New York wall clock remains
strictly before 11:00. If it has not filled by 11:00, it is cancelled and cannot
fill later.

## Filled-trade lifecycle

The source provides fixed invalidation and target geometry. It does not provide
a source-authoritative time exit in the supplied video. The research model
therefore does not manufacture one.

After fill:

- stop and target remain frozen;
- first terminal touch ends the trade;
- if stop and target are both touched inside one OHLC bar, stop wins
  conservatively;
- if retained M1 evidence becomes discontinuous before terminal resolution, the
  trade is `gap_censored` and excluded from terminal economic metrics;
- if the retained dataset ends before terminal resolution, the trade is
  `data_end_censored` and excluded from terminal economic metrics.

This separation preserves the distinction between source methodology and the
limitations of OHLC historical execution evidence.

## 11-market matrix semantics

The canonical campaign matrix remains:

`EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, XAUUSD, NAS100, SP500, GBPJPY, AUDJPY, US30`

For this exact VT-31 V2 candidate, only `NAS100` is source-authorized. The other
ten rows are reported as `unsupported-method-market`; they are not backtested as
invented trades and they do not count as failures of the methodology.

## Authority

Outputs are historical research evidence only. They do not create Trader Lab
promotion, Risk authorization, broker submission, DEMO_ELIGIBLE, LIVE,
Production, or real-capital authority.
