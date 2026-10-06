# VT31 NAS100 — Side-Relative HTF Alignment Audit Findings 001

**Status:** OBSERVATION CLOSED / HTF VETO REJECTED  
**Gate:** `VT31_ARCH2_SIDE_RELATIVE_HTF_ALIGNMENT_AUDIT_GATE_001.md`  
**Fresh Holdout:** SEALED

## Result under the frozen taxonomy

### BOTH_AGAINST

- trades: 6;
- winners: 1;
- losses: 5;
- stressed total: approximately +0.87546R;
- stressed mean: approximately +0.14591R/trade;
- zero-call structural invalidations: 2;
- support: R5, R6, recent consumed.

Despite the high loss count, this state retains a winner large enough to keep
the state positive under baseline friction.

### BOTH_ALIGNED

- trades: 3;
- winners: 1;
- losses: 2;
- stressed mean: approximately +1.12749R/trade;
- support: recent consumed only.

### BOTH_NEUTRAL

- trades: 17;
- winners: 4;
- losses: 13;
- stressed mean: approximately +1.65613R/trade.

### ONE_DIRECTIONAL

- trades: 71;
- winners: 24;
- losses: 47;
- stressed mean: approximately +2.23252R/trade.

### SPLIT

- trades: 12;
- winners: 5;
- losses: 7;
- stressed mean: approximately +3.44661R/trade.

## Adjudication

No side-relative H4/H1 state qualifies for an admission veto.

In particular, `BOTH_AGAINST` is **not** promoted despite 5/6 losses because:

- it contains a real winner;
- aggregate stressed expectancy remains positive;
- removing it would discard demonstrated edge;
- the state captures only 2 of the 17 zero-call structural invalidations.

Therefore the earlier absolute `H4 bearish + H1 bearish` zero-winner pattern
is confirmed to be semantically misleading when side is restored.

## Consequence

The zero-call class should not be attacked by broad HTF directional filtering.

The remaining scientific question is narrower:

> Why can structural invalidation occur before the first post-entry cognitive
> observation, and is there a causal entry/first-open observability mechanism
> that can detect the failure without looking into the terminal outcome?

That question requires execution-timeline reconstruction, not another HTF veto.

## Governance

No policy promoted. No numeric threshold added. No sizing, leverage,
compounding or capital engineering. Fresh Holdout remains sealed.
