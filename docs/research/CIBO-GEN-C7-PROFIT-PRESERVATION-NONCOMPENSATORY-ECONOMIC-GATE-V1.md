# CIBO GEN-C7 — Non-Compensatory Causal Economic Gate V1

Status: **PREREGISTERED / FROZEN / RESEARCH-ONLY**

Gate identity:

`CIBO_GENC7_PROFIT_PRESERVATION_NONCOMPENSATORY_ECONOMIC_GATE_V1`

Frozen at:

`2026-09-30T19:25:00Z`

Semantic digest:

`sha256:68d5e74113c51f8724a50e795e7f24df9f1bebab17ab405d82b492595f107063`

## Critical identification law

The existing GEN-C7 OOS binder describes the realized path at a preregistered
horizon. It explicitly does not identify a counterfactual treatment effect.

Therefore:

`OBSERVED_PATH != CAUSAL_TREATMENT_EFFECT`

This economic gate accepts only summaries where causal treatment-effect
identification has already been established on a frozen equal population.

## Comparison surface

Every control/treatment comparison requires the same:

- frozen GEN-C7 policy digest;
- causal population SHA;
- provider-economic surface SHA;
- WF1..WF4 folds;
- chronological horizon.

Control is exactly `HOLD_CURRENT_CAPITAL_STATE`.

Treatments are separately evaluated PROTECT / HARVEST / RESERVE / COMPOUND
proposals. Multiple treatments may survive; the gate never chooses a winner.

## Non-compensatory safety

Higher profit cannot compensate for deterioration in:

- realized-capital delta;
- protected floor;
- minimum base capital;
- minimum compound capital;
- maximum drawdown;
- p99 drawdown;
- peak plausible loss;
- provider cost;
- minimum optionality;
- profit-retention ratio;
- giveback.

Only after all safety/economic-preservation dimensions are no worse may strict
improvement be recognized in realized capital/profit, floor, retention,
giveback, optionality or capital-risk-time productivity.

Passing means only `ELIGIBLE_FOR_FURTHER_RESEARCH`.

Fresh OOS causal evidence, adversarial stress and 4/4 temporal replication are
still required. This gate grants no sizing, Risk, execution or production
authority.
