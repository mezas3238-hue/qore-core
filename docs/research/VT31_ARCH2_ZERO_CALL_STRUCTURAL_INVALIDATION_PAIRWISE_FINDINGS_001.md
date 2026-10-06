# VT31 NAS100 — Zero-Call Structural Invalidation Pairwise Findings 001

**Status:** OBSERVATION CLOSED / NO POLICY PROMOTED  
**Gate:** `VT31_ARCH2_ZERO_CALL_STRUCTURAL_INVALIDATION_PAIRWISE_GATE_001.md`  
**Fresh Holdout:** SEALED

## Frozen scan result

The single-state scan produced no candidate satisfying all frozen requirements.

The pairwise scan produced exactly one conjunction:

`h4_state=bearish && h1_state=bearish`

Across the Comparator-009 consumed population:

- matched trades: 6;
- winners: 0;
- losses: 6;
- zero-call structural-invalidating losses: 3;
- other losses: 3;
- retained partition support: R5, R6, recent consumed.

The matched trades include both LONG and SHORT positions.

## Interpretation

This conjunction is **not promoted** as an admission rule.

Absolute H4/H1 bearishness is not side-relative:

- for LONG it can represent higher-timeframe conflict;
- for SHORT it can represent higher-timeframe alignment.

Therefore a blanket `H4 bearish + H1 bearish` veto would mix two different
market meanings even though the consumed sample contains no winners.

Promoting it directly would be outcome-led overfitting.

## Next scientific question

The correct market-native question is side-relative:

> Is the frozen entry thesis aligned with, opposed by, or split against H4/H1
> directional context?

That taxonomy exists independently of terminal PnL and uses no new numeric
threshold.

A separate predeclared observation gate is required before inspecting its
economics.

## Governance

No policy promoted. No sizing, leverage, compounding or capital engineering.
No fold/date runtime authority. Fresh Holdout remains sealed.
