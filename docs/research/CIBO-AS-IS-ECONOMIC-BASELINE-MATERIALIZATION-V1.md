# CIBO AS-IS Economic Baseline Materialization V1

Status: **IMPLEMENTED / CI PENDING / REAL FORWARD POPULATION STILL REQUIRED**

Identity:

`CIBO_AS_IS_ECONOMIC_BASELINE_MATERIALIZATION_V1`

Control identity:

`CIBO_GENERATION_CURRENT_CONTROL_V1`

Control Git SHA:

`87d98ced8d56b275823c4472392923ba6a11d769`

## Purpose

Materialize the economic behavior of the current frozen CIBO generation from the
same legal provider-valid forward population that later treatments must use.

This implementation does not create a second baseline, retune the existing
control, synthesize missing economics, or inspect the sealed 2017H1 holdout.

Canonical implementation:

`src/qore/infrastructure/cibo_as_is_economic_baseline.py`

Tests:

`tests/infrastructure/test_cibo_as_is_economic_baseline.py`

Workflow:

`.github/workflows/cibo-as-is-economic-baseline.yml`

## Inputs

Only two canonical surfaces are accepted:

1. `Phase20QualificationReport` from the frozen Phase20D qualification path.
2. `ForwardCompoundEconomicRecord` population accepted by the strict Compound
   real-population binding.

The adapter is read-only over Provider/Risk/CMA/Forward evidence owned by
Architect B.

## Qualification semantics

Economic `PASS` and economic `FAIL` are both measurable AS-IS states when
the causal population is complete and valid.

A `FAIL` economic verdict is preserved. It is not relabelled as invalid data.

The following fail closed and cannot produce an AS-IS measurement:

- `NOT_READY`;
- `INVALID`;
- readiness false;
- frozen plan/candidate drift;
- any pre-freeze decision;
- missing policy decisions;
- insufficient frozen thresholds;
- coverage below the frozen thresholds;
- inconsistent readiness summaries;
- inconsistent report aggregates.

## Independent threshold revalidation

The materializer does not trust `readiness.ready=True` by itself.

It independently requires at least the frozen Phase20D thresholds:

- 80 decision epochs;
- 200 candidate outcomes;
- 60 selected outcomes;
- 28 calendar days;
- 20 distinct trading days;
- 7 represented lineages;
- 8 outcomes per lineage;
- 40 candidate outcomes per fold;
- 4 lineages per fold;
- candidate outcome coverage >= 95%;
- selected outcome coverage = 100%;
- baseline-selected outcome coverage = 100%.

It also reconciles candidate/selected counts, dates, lineages, acceptance rates,
coverage, realized net deltas, terminal cash-path drawdown and capital
productivity against the underlying rows.

## Compound binding

The Compound population must first pass:

`bind_forward_compound_population()`

Therefore the AS-IS materialization inherits:

- `FORWARD_OBSERVED` only;
- exact frozen V3 identity;
- no pre-freeze decisions;
- unique decision/deployment/market/episode identities;
- all four canonical folds `WF1/WF2/WF3/WF4`;
- non-overlapping temporal folds;
- immutable Provider/Risk/CMA/settlement/release/source-manifest hashes;
- no future leakage;
- no missing floor evidence when floor graduation is non-zero.

The AS-IS adapter additionally requires one account-identity fingerprint and one
source-manifest SHA for the bound Compound population.

## Cross-surface reconciliation

Every Compound deployment must map to one exact Phase20D policy-selected row
with the same:

- decision epoch;
- signal fingerprint;
- decision timestamp;
- Trader lineage;
- stop-risk USD;
- margin USD;
- realized terminal net PnL;
- frozen candidate identity.

A mismatch is invalid evidence, not a value judgment.

## Materialized metrics

The measurement persists the canonical Phase20D current-policy metrics plus:

- Compound episode count;
- gross deployed Compound capital;
- realized Compound net PnL;
- protected-floor graduation;
- capital-minutes;
- stop-risk-minutes;
- margin-minutes;
- highest observed source generation;
- exact Phase20 population SHA-256;
- exact Compound population SHA-256;
- source-manifest SHA-256;
- account-identity fingerprint.

The entire measurement has a deterministic SHA-256 digest.

## Non-claims

Implementation and CI success do not mean that:

- the real Phase20D qualification population already exists;
- the AS-IS baseline workstream is terminal;
- any N+1 treatment adds value;
- fresh OOS has passed;
- stress has passed;
- temporal replication has passed;
- the 2017H1 holdout may be opened;
- CIBO is certified.

`AS_IS_ECONOMIC_BASELINE` remains open until a legal real forward population
is supplied, the materialization is executed on that population, its evidence
digest is sealed, and the result is reconciled into the final scientific
closure package.
