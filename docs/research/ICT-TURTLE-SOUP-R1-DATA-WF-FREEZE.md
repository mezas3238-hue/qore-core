# ICT Turtle Soup R1 — Consumed Data / Walk-Forward Freeze

Issue: #572
Identity: `ICT_TURTLE_SOUP_R1_CISD_SESSION`

This document is frozen before any R1 economic outcome is opened.

## Evidence classification

The index interval previously accessed elsewhere in QORE is **not fresh** for this research, even though ICT Turtle Soup has never been replayed on it.

R1 may use the following interval only as consumed research evidence:

`[2024-08-13T00:00:00 America/New_York, 2026-09-01T00:00:00 America/New_York)`

Markets: `NAS100`, `SP500`, `US30`.

Required execution evidence: provider-native M5, timezone-aware, immutable provenance. No M15 interpolation is allowed.

## Temporal split

Development / implementation-characterization interval:

`[2024-08-13, 2025-03-01)` New York dates.

Walk-Forward is frozen as six sequential non-overlapping folds:

- `WF1`: `[2025-03-01, 2025-06-01)`
- `WF2`: `[2025-06-01, 2025-09-01)`
- `WF3`: `[2025-09-01, 2025-12-01)`
- `WF4`: `[2025-12-01, 2026-03-01)`
- `WF5`: `[2026-03-01, 2026-06-01)`
- `WF6`: `[2026-06-01, 2026-09-01)`

No fold boundary may move after economics are observed.

## Cost formalization

Until exact funded-account execution costs are bound, QORE R1 uses normalized friction purely as a research stress model:

- gross: `0.00R/trade` friction;
- primary research friction: `0.05R/trade`;
- stress friction: `0.10R/trade`.

These are QORE research formalizations, not claims about cTrader, FundedNext, FTMO, NQ, ES, or YM transaction costs. Promotion would require provider/account-specific execution feasibility and cost binding.

## Walk-Forward advancement gate

All conditions must pass on the unchanged R1 contract:

1. forward closed trades `>= 30`;
2. primary-friction forward mean R `> 0`;
3. primary-friction forward profit factor `> 1`;
4. at least `4/6` folds have positive total R;
5. stress-friction forward mean R `>= 0`;
6. leave-one-market-out total R is positive for all three exclusions;
7. LONG forward mean R `> 0` and SHORT forward mean R `> 0` when each side has at least 10 trades; if either side has fewer than 10 trades, R1 fails for insufficient directional evidence rather than deleting that side;
8. positive-gain concentration maximum share across market, side, and calendar quarter `<= 50%`;
9. causal/data-integrity gate is true with zero unresolved session discontinuities among executed trades.

There is no market, side, weekday, date, or fold selection after results.

## Prospective OOS

No historical interval already accessed by QORE will be relabeled as globally fresh for ICT Turtle Soup R1.

If and only if the consumed Walk-Forward gate passes, a later candidate/config freeze may authorize **prospective** final OOS beginning no earlier than:

`2026-09-16T00:00:00 America/New_York`.

The prospective OOS must remain unopened for candidate development. Its minimum duration/sample requirement must be frozen in the later candidate freeze before it can be consumed.

## Failure rule

If R1 fails any frozen Walk-Forward gate, verdict is `ICT_TURTLE_SOUP_R1_REJECTED_FOR_ADVANCEMENT` and no retrospective R1 parameter modification is allowed. Any materially different liquidity pool, session, CISD definition, entry family, FVG/Breaker addition, stop, target, or management requires a new research identity.

## Authority

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
