# VT31 NAS100 — Breaker Mixed Weak-Efficiency Adverse Exit Gate 001

**Status:** PREDECLARED DEVELOPMENT GATE  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Hypothesis ID

`COMP007_PLUS_BREAKER_MIXED_WEAK_EFFICIENCY_ADVERSE_EXIT`

## Fixed base

All Comparator-007 admission and position logic remains frozen.

The candidate adds exactly one post-entry degree of freedom.

## Additional exit authorization

For a still-pre-DOL1 Breaker, after a fully closed M1, authorize EXIT at the
**next M1 open** only when all are true:

1. maximum cognition verified;
2. `current_open_r <= -0.50R`;
3. `management_context == MIXED`;
4. `recent_path_efficiency` is available;
5. `recent_path_efficiency <= 0.30`.

The existing Comparator-007 exits remain unchanged and retain precedence.

## Threshold provenance

No new numeric threshold is introduced.

- `-0.50R` is the existing MATERIAL_ADVERSE threshold.
- `0.30` is the existing weak-path efficiency threshold in live cognition.

The new degree of freedom is the causal conjunction of those already-existing
states for Breakers.

## Causality

The decision may use only the fully closed M1 that has just completed and
state reconstructable at that time.

Execution must occur at the next M1 open.

Forbidden:

- same-bar exit;
- future bars;
- outcome labels;
- trade/date/fold identity;
- sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital rescue;
- CIBO rescue.

## Cross-fold gate

The exact same policy must run on R5, R6, R8 and recent consumed.

Development survivor requires:

- PF non-degrade 4/4;
- mean-R non-degrade 4/4;
- observed DD non-degrade 4/4;
- density >=75% 4/4;
- winner-count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrade;
- real economic actuation in at least two consumed partitions;
- R5 DD <=6R;
- R6 DD <=6R;
- R8 DD <=6R;
- recent DD <=6R;
- recent PF >=1.70;
- recent mean >=+0.15R;
- recent MC positive >=90%;
- recent MC p95 DD <=15R.

## Governance

Consumed evidence only.

Passing this gate would create a new development survivor, not a frozen
certification candidate.

Fresh holdout remains sealed.
