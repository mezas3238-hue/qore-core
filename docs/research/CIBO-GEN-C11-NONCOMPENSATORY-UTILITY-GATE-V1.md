# CIBO GEN-C11 Non-Compensatory Utility Gate V1

Status: **PREREGISTERED BEFORE REAL GEN-C11 OOS OUTCOMES**

Policy under evaluation:

`CIBO_GENC11_ROBUST_MULTI_PERIOD_CAPITAL_MPC_V1`

## Preconditions

GEN-C11 cannot enter economic evaluation unless:

1. the GEN-C10 chronological twin population is real and causally bound;
2. GEN-C10 transition uncertainty is calibrated without future leakage;
3. the same frozen comparison population is used for control and treatment;
4. provider-valid USD economics are complete;
5. no market probability or oracle arrival is introduced.

## Control

The primary economic control is the sealed current-generation identity:

`CIBO_GENERATION_CURRENT_CONTROL_V1`

The control and GEN-C11 treatment must be replayed on the same causal
population. Outcome inspection cannot change either identity.

## Gate law

GEN-C11 reuses the frozen non-compensatory GEN-C9 economic law instead of
inventing a weighted MPC score.

A treatment is ineligible if any material safety dimension worsens, including:

- ruin / insolvency incidence;
- capacity or capital-conservation breaches;
- maximum or tail drawdown;
- peak plausible loss;
- minimum realized capital;
- underwater duration / recovery;
- provider, Risk or concentration violations;
- loss of required optionality or reserve coverage.

If safety is non-worse, the treatment must strictly improve at least one
predeclared economic dimension, such as:

- ending or minimum realized capital;
- capital productivity per unit of plausible loss;
- capital productivity per risk-minute;
- optionality preservation;
- reserve efficiency;
- robust deployable capacity without safety deterioration.

No weighted score may compensate a failed safety dimension.

## Temporal law

Economic replication is not aggregate-only.

The treatment must pass the same non-compensatory gate independently in:

`WF1 / WF2 / WF3 / WF4`

using:

`CIBO_COMPOUND_TEMPORAL_ECONOMIC_REPLICATION_CRITERION_V1`

Anything below 4/4 is not replicated.

## Stress

GEN-C11 must also remain non-worse under the preregistered Compound adversarial
stress families. A favorable base case cannot compensate a stress regression.

## Authority

This gate produces research eligibility only.

It never:

- selects a production policy;
- grants sizing, Risk, execution, LIVE or real-capital authority;
- certifies CIBO by itself.

## Result status

The criterion is frozen now. The result remains unknown until real GEN-C10/11
populations exist.
