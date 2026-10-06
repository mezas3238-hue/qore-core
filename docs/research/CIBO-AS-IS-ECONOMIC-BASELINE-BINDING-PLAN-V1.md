# CIBO AS-IS Economic Baseline Binding Plan V1

Status: **PREREGISTERED / CONTROL SEALED / REAL POPULATION REQUIRED**

Control:

`CIBO_GENERATION_CURRENT_CONTROL_V1`

Exact sealed control Git SHA:

`87d98ced8d56b275823c4472392923ba6a11d769`

## Finding

No new AS-IS economic-baseline engine is required.

The existing frozen Phase20D qualification runner already computes the
provider-valid forward metrics required for the current-policy baseline:

`run_phase20d_full_surface_qualification()`

Canonical implementation:

`src/qore/infrastructure/cibo_ce2i_phase20_qualification.py`

Frozen protocol:

`CIBO_PHASE20D_FULL_SURFACE_FORWARD_QUALIFICATION_PLAN_V4`

## Reused current-policy measurements

The canonical report already exposes:

- policy and fixed-baseline realized net delta USD;
- terminal-settlement cash-path drawdown;
- capital productivity in USD per risk-minute;
- policy/baseline acceptance rate;
- selected and candidate outcome coverage;
- capital utilization;
- capital starvation;
- MPC reserve efficiency;
- optionality preservation;
- concentration utilization;
- provider failure incidence;
- evidence missingness;
- advanced CE2I apply / abstain / fail-closed rates;
- four contiguous temporal folds.

The frozen runner also reconstructs the predeclared fixed minimal-seed baseline
from the same decision-time population. No separate hindsight baseline may be
introduced.

## Compound-layer measurements

For the Compound / GEN-C portion of the sealed current generation, Architect A
will bind only the same legal forward population through:

`src/qore/infrastructure/cibo_compound_real_population_binding.py`

and then reuse:

- dependency-aware Compound Monte Carlo;
- GEN-C9 non-compensatory economic gate;
- adversarial stress matrix;
- temporal replication harness;
- profit-preservation / protected-floor evidence where causally identified.

## Population identity law

The baseline and every N+1 treatment comparison must bind to the same causal
population lineage. At minimum the final evidence package must prove:

1. exact frozen Phase20 V3 candidate identity;
2. exact current-control identity;
3. exact Phase20D qualification-plan SHA;
4. exact decision/outcome population manifest SHA;
5. no pre-freeze decisions;
6. no synthetic or burned evidence;
7. complete selected and baseline-selected outcome coverage;
8. provider-valid realized USD economics;
9. identical causal comparison population for control and treatment;
10. no policy/control selection after outcome inspection.

## Non-claim

This document closes architecture ambiguity only.

It does not close `AS_IS_ECONOMIC_BASELINE`.

That workstream remains open until the real fresh population exists and the
measurements above are materialized, hashed and reconciled.
