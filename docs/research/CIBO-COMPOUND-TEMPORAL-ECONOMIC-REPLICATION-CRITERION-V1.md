# CIBO Compound Temporal Economic Replication Criterion V1

Status: **PREREGISTERED BEFORE REAL QUALIFYING OUTCOMES**

Identity:
`CIBO_COMPOUND_TEMPORAL_ECONOMIC_REPLICATION_CRITERION_V1`

## Purpose

Freeze the economic-replication rule before Architect A receives a real
qualifying population.

This criterion does not create a score and does not allow strong folds to
compensate weak folds.

## Canonical folds

Exactly four contiguous Phase20D folds are required:

`WF1 / WF2 / WF3 / WF4`

Each fold must carry:

- forward-observed evidence;
- its own immutable source-population SHA-256;
- provider-economics SHA-256;
- an independently evaluated GEN-C9 non-compensatory economic-gate report.

Outcomes may not be pooled across folds.

## Replication law

For one preregistered treatment candidate to be called economically replicated:

1. all four folds must use the same control identity;
2. all four folds must use the frozen
   `CIBO_GENC9_NONCOMPENSATORY_ECONOMIC_GATE_V1`;
3. in every fold the treatment status must be
   `ELIGIBLE_FOR_FURTHER_RESEARCH`;
4. in every fold `safety_no_worse = true`;
5. in every fold
   `strict_growth_or_efficiency_improvement = true`;
6. in every fold `failed_dimensions = []`;
7. no weighted score may be used;
8. no production policy may be selected by this gate;
9. no certification-ready claim is emitted by this gate alone.

Therefore:

```text
4 / 4 PASS -> REPLICATED
anything else -> FALSIFIED
```

There is no 3/4 rescue rule and no aggregate-return override.

## Why this criterion

The GEN-C9 gate is already frozen as non-compensatory:

higher return cannot pay for worse ruin, drawdown, plausible loss, recovery,
underwater time or capacity fragility.

Temporal replication extends the same law across time rather than inventing a
new scoring function.

## Implementation

`src/qore/infrastructure/cibo_compound_temporal_replication_gate.py`

Tests:

`tests/infrastructure/test_cibo_compound_temporal_replication_gate.py`

## Non-claim

The criterion is frozen; the result is not known.

`TEMPORAL_REPLICATION` remains open until a provider-valid real population is
available and all four real folds are evaluated without refitting.
