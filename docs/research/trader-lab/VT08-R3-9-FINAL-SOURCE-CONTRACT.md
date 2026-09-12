# VT-08 R3.9 final source-to-code contract

Status: SOURCE_EXECUTABLE_WITH_EXPLICIT_CONTAINMENTS

This document records the second-pass VT-08-only source adjudication and the QORE implementation boundary that follows from it. It is research-only. It does not grant DEMO eligibility, LIVE authority, or real-capital authority.

## Source-resolved core

- Daily bias: four-case PDH/PDL continuation/reversal logic.
- Forex entry anchors: 01:00, 05:00, 09:00 America/New_York.
- C2/C3 fractal: valid positional entry may follow a completed C2 reversal or C3 continuation.
- CISD level: open of the first opposing candle in the sequence.
- CISD confirmation: close through the CISD level; wick-only is insufficient.
- Opposing series: 1+ opposing candles is retained as a source-supported formalization.
- Protected Swing: structural extreme confirmed after important-level interaction plus CISD.
- Positional entry reference: new HTF open.
- Structural invalidation reference: Protected Swing extreme.

## Explicit QORE containments

The following are not promoted to TTrades source rules:

- 17:00 New York to 17:00 New York source-day reconstruction.
- Exact historical fill at the new H4 OHLC open.
- No broker stop offset beyond the Protected Swing structural level.
- Fixed 2R research replay target.
- Close still-open modeled position at the next H4 boundary.
- Exactly one valid Protected Swing, otherwise abstain.
- Exactly one B01 candidate per market per New York date, otherwise abstain.
- Abstain when direction is not uniquely resolved after both-side sweep evidence.
- Full 01/05/09/13/17/21 H4 reconstruction grid. These hours are a reconstruction grid, not source-authorized entry anchors.

## Fundamentally unresolved

- Exact source-day convention.
- Broker order type for positional entry.
- Broker stop offset.
- Deterministic selection among multiple valid Protected Swings.
- Filled-position H4 lifecycle.
- Both-side-sweep machine rule.
- Re-entry and daily trade cardinality.
- Futures 14:00 construction.
- Deterministic priority among structural target families.

## Target adjudication

VT-08 primary examples use structural liquidity objectives and discuss 2R as viability/generic initial guidance. QORE therefore keeps 2R only as a conservative research replay containment.

The second-pass suggestion `min(2R, next_HTF_liquidity)` is intentionally NOT implemented in this freeze because the adjudication also found no universal source priority for selecting `next_HTF_liquidity`. Adding such a selector would convert unresolved source semantics into a silent code rule.

## Shallow/large adjudication

Shallow versus large/deep opposing run remains qualitative. No ATR, percentage, pips, ticks, wick/body ratio, or candle-count threshold is authorized. The current narrow completed-C2 B01 subset does not add a numerical classifier.

## C3 scope

C3 continuation is source-authorized, but the existing R3.8 executable profile is intentionally narrower and implements completed-C2 reversal only. R3.9 records that gap explicitly rather than silently broadening the frozen economic model. Any C3 implementation requires its own reviewed code delta and pre-registration before unseen evidence is accessed.

## H01 conclusion

H01 is source-adjudicated without a performance-driven methodology mutation. Existing consumed diagnostics do not authorize widening stops, choosing alternate Protected Swings from later price action, inventing CISD latency thresholds, or selecting markets/hours from P&L.

Status: `H01_SOURCE_ADJUDICATED_NO_PERFORMANCE_MUTATION`.

## Holdout governance

Consumed baseline: GitHub Actions run `34693803930`.

Failure-forensics run: `34696371933`.

Forbidden reuse: `run-34693803930` as independent validation.

A newly downloaded 760-day window that materially overlaps the consumed baseline is not an independent holdout. Independent validation remains blocked until an actually unseen interval is reserved before outcome access.

## Execution authority

- Research only: YES.
- DEMO_ELIGIBLE: NO.
- LIVE: NO.
- Real capital: NO.

SOURCE FIRST. CODE SECOND. FRESH HOLDOUT THIRD.
