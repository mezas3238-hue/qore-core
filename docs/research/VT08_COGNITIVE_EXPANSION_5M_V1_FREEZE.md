# VT08 COGNITIVE EXPANSION 5M V1 — Research Freeze

Status: **STARTED / RESEARCH-ONLY / STACKED ON VT08 COGNITIVE V1**

## Frozen five-market program

- EURJPY — new research market
- USDCHF — new research market
- NZDUSD — new research market
- CADJPY — new research market
- USDCAD — existing VT08 market used as control

Owner anchors remain **01:00 / 05:00 / 09:00 America/New_York**.

The four new markets are not added to the certified VT08 runtime. The current
VT08 market authority remains unchanged. This program tests whether the frozen
VT08 methodology transfers before any authority can be considered.

## Why USDCAD is the control

USDCAD already has consumed VT08 R3.15 evidence:

- run 34759027136
- artifact 10318398127
- digest sha256:ca9c81bff7e7559c6ace39499a4edd8a019937cf1c20fcb71aec5f05c5dae69e

That makes it possible to distinguish "the new cognitive/research harness is
wrong" from "a genuinely new market behaves differently."

## Existing Core labs reused

This program reuses existing QORE patterns rather than creating an isolated lab:

1. VT08 B01 source mechanics — H4 construction, source-day bias, protected
   swing/CISD semantics.
2. VT08 B01 backtest execution model — new-H4-open entry, PS structural stop,
   conservative 2R target and next-H4 containment.
3. VT08 B01 failure forensics — market/anchor/side/exit decomposition.
4. VT08 Index CIBO stop-protection lab pattern — immutable signal stream with
   management variants.
5. CIBO Market Atlas journey-ledger pattern — causal journey and destination
   evidence.
6. Trader Lab walk-forward pattern — chronological IS/OOS separation.
7. Trader Lab robustness — pre-registered stress and block-bootstrap Monte Carlo.

No Turtle Soup, VT31, or Capitalizer trading rule is imported.

## Pre-registered research gates

Before seeing outcomes for the four new markets:

- minimum 2Y sample: 50 trades per market;
- PF >= 1.80;
- observed DD <= 6R;
- mean R >= 0;
- MC p95 DD <= 15R;
- MC positive terminal >= 0.90;
- anchor stability required;
- temporal validation required;
- stress required;
- Monte Carlo required.

These are research qualification gates, not claimed results.

## Evidence status

USDCAD: consumed control evidence available.

EURJPY / USDCHF / NZDUSD / CADJPY: **new sanitized DEMO/read-only M15 evidence
is required**. Repository and current CIBO Atlas inspection found no retained
corpus for these symbols. The replay harness is now ready to consume the same
market-evidence shape already used by VT08.

Minimum evidence contract:

- >= 730 chronological days;
- complete M15 OHLC;
- timezone-aware timestamps;
- DEMO / read-only;
- account_is_live=false;
- exact software SHA and account fingerprint;
- no duplicate M15 opens.

## Authority boundary

- research_only = true
- demo_eligible = false
- new_market_execution_authority = false
- live_authorized = false
- production_authorized = false
- real_capital_authorized = false

No result from this consumed/development program may silently expand the live
VT08 market list.
