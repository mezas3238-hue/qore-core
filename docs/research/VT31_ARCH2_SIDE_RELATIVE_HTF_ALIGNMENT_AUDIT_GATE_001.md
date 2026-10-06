# VT31 NAS100 — Side-Relative HTF Alignment Audit Gate 001

**Status:** PREDECLARED OBSERVATION-ONLY GATE  
**Baseline:** truthful Comparator-009 development population  
**Fresh Holdout:** SEALED

## Purpose

Resolve the semantic ambiguity exposed by the zero-call pairwise audit without
adding numeric thresholds or outcome-aware policy.

## Frozen side-relative taxonomy

For each trade, classify H4 and H1 independently relative to the frozen side.

For LONG:

- bullish = ALIGNED;
- bearish = AGAINST;
- mixed/unavailable/other = NEUTRAL.

For SHORT:

- bearish = ALIGNED;
- bullish = AGAINST;
- mixed/unavailable/other = NEUTRAL.

Then assign one fixed joint state:

- `BOTH_ALIGNED`: H4 and H1 both ALIGNED;
- `BOTH_AGAINST`: H4 and H1 both AGAINST;
- `SPLIT`: one ALIGNED and one AGAINST;
- `ONE_DIRECTIONAL`: exactly one is directional and the other NEUTRAL;
- `BOTH_NEUTRAL`: both NEUTRAL.

These definitions are frozen before outcome inspection.

## Report

For every joint state report:

- trade count;
- winners/losses;
- total and mean stressed R;
- zero-call structural-invalidation count;
- partition support;
- half-year support;
- entry-family composition;
- observed DD contribution diagnostics.

This is observation only.

## Candidate floor for later research

A state may justify a separately predeclared economic frontier only if it has:

- support in >=3 consumed partitions;
- at least 3 losses;
- zero winners, or a clearly negative cross-partition expectancy that survives
  matched-winner review;
- coherent market semantics independent of PnL.

No state is authorized merely by passing these discovery criteria.

## Governance

No new numeric threshold. No date/fold identity authority. No outcome runtime
authority. No sizing/leverage/compounding/capital weighting. Fresh Holdout
sealed.
