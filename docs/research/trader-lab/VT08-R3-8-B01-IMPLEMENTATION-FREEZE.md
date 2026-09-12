# VT-08 Revision 3.8 B01 Implementation Freeze

## Status

This document freezes the first code-executable research subset derived from the
VT-08 source-fidelity reconstruction. It is intentionally narrower than the full
TTrades methodology and narrower than the Revision 3.2 semantic kernel.

The parent foundation is PR #520 at `4251d0a2f310fa497f7edc5ca90c5a2c9b04320e`.
PR #518 remains a frozen pre-R3.2 forensic/economic baseline and is not rewritten.

No merge, READY, DEMO_ELIGIBLE, broker, LIVE, Production, or real-capital
authority is granted by this freeze.

## Profile

The implemented profile is `AUTHOR_CLARIFIED` and is identified as:

`B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1`

It is a historical research replay with explicit QORE operational containments.
It must not be described as a universally source-complete live execution model.

## First replay scope

The first R3.8 replay is deliberately Forex-only:

- AUDJPY
- AUDUSD
- EURUSD
- GBPJPY
- GBPUSD
- USDCAD
- USDJPY

Human Owner entry anchors are 01:00 / 05:00 / 09:00 America/New_York.

Futures are not silently proxied into this first replay. The source uses NQ/ES/YM,
while QORE market evidence presently uses CFD proxies such as NAS100/SP500/US30,
and the Futures 14:00 H4/session-break construction remains fundamentally
unresolved. This first replay therefore fails closed rather than manufacturing a
futures day/H4 construction.

## Source-semantic gates

A B01 historical candidate requires all of the following:

1. a deterministic daily-bias case from the author-clarified PDH/PDL framework;
2. a completed source H4 Candle-2 reversal relative to the prior source H4 range;
3. M15 opposing delivery that sweeps the important reference level;
4. a causal M15 CISD close through the first opposing-series open;
5. exactly one valid protected swing for the positional setup;
6. entry reference equal to the new H4 open;
7. valid directional risk geometry.

If any of those conditions is unresolved, QORE abstains.

## Bias subset

The frozen deterministic subset is:

- close above previous-day high -> LONG continuation bias;
- close below previous-day low -> SHORT continuation bias;
- sweep previous-day low and close back above it -> LONG reversal bias;
- sweep previous-day high and close back below it -> SHORT reversal bias;
- conflicting/other cases -> ABSTAIN.

No voting system or optimization is permitted.

For the Forex replay, source days are reconstructed from complete contiguous M15
bars on the America/New_York 17:00-to-17:00 cycle. Source H4 candles are likewise
reconstructed only from complete contiguous M15 windows at the official Forex H4
anchors. Missing evidence fails closed.

## Explicit operational containments

The following are QORE research policies, not universal TTrades source claims:

1. `historical-fill-at-new-h4-open-broker-order-type-unspecified`
2. `protected-swing-structural-level-no-stop-offset`
3. `conservative-initial-2r-replay-target`
4. `close-modeled-position-at-next-h4-boundary`

These values are fingerprinted into the methodology identity and emitted in the
backtest artifacts. They may not be silently promoted to TTrades source rules.

## Cardinality

The Human Owner contract remains a maximum of one filled trade per market per
America/New_York date.

R3.8 does not invent `FIRST_FOUND`, earliest, best-R, or any other daily priority.
If more than one B01 candidate survives on the same market-day, that market-day
abstains entirely. The artifact must report `daily_cardinality_violations = 0`.

## Replay execution model

The historical replay fills the selected positional candidate at the new H4 open.
Within the following H4 containment interval:

- stop is checked before target when both are touched by the same M15 bar;
- stop uses the protected-swing structural level with no invented offset;
- target is the conservative initial 2R level;
- if neither is touched, the replay closes at the next H4 boundary as an explicit
  containment, not as a source claim.

## Excluded / unresolved

The first replay does not implement:

- Futures 14:00 candle construction;
- futures CFD-proxy equivalence as source identity;
- live broker order type for positional entries;
- protected-swing stop execution offset;
- source-explicit filled-position behavior across an H4 boundary;
- reversal-entry exact price;
- continuation-entry exact price;
- T-Spot execution;
- SMT;
- Failure Swing;
- arbitrary shallow/large numerical thresholds.

## Quality and economic gate

Before any economic result is interpreted, the exact R3.8 SHA must pass:

- `ruff check .`
- `mypy src tests`
- focused adversarial R3.8 tests
- full `pytest --cov=src/qore --cov-report=term-missing`

Only after that gate may fresh 760-day DEMO evidence be collected and the
seven-market Forex replay run. Results are research evidence only and cannot be
used retroactively to change methodology semantics.
