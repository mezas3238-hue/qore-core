# CIBO Protected Base — Non-Compensatory Numeric Policy Gate V1

Status: **PREREGISTERED / FROZEN / RESEARCH-ONLY**

Gate:

`CIBO_PROTECTED_BASE_NONCOMPENSATORY_POLICY_GATE_V1`

Frozen at:

`2026-09-30T19:10:00Z`

Semantic digest:

`sha256:05fa878b3e6f824851d559550fe7137bf457dd589eb46192547b51d0eb91ebc0`

## Purpose

The Protected Base semantics were already frozen, but a numeric policy still
needed an executable pre-outcome registration and evaluation contract.

This gate does **not** choose a protected amount from outcomes.

Every treatment must register its exact numeric protected-base amount, policy
identity and digest before the evaluation horizon starts.

Frozen Phase20 V3 remains unchanged.

## Protection truth

`ACCOUNTING_PROTECTED`, `ECONOMICALLY_RESERVED`, `POLICY_PROTECTED` and
`BROKER_GUARANTEED` remain distinct.

A broker guarantee requires explicit immutable provider evidence. Accounting or
policy protection can never be relabeled as a provider guarantee.

## Identical comparison surface

Control and treatment require the same:

- causal population SHA;
- provider-economic surface SHA;
- WF1..WF4 fold identities;
- chronological horizon.

No hindsight retuning or weighted score is allowed.

## Non-compensatory gate

A treatment is rejected if it worsens:

- ending realized capital;
- minimum original base;
- maximum drawdown;
- p99 drawdown;
- peak plausible loss;
- peak margin occupancy;
- p95 recovery;
- minimum optionality;
- provider-failure incidence.

After all no-worse conditions pass, at least one strict improvement is required
in base preservation, drawdown/tail loss, recovery, optionality or
capital-risk-time productivity.

Passing means only `ELIGIBLE_FOR_FURTHER_RESEARCH`.

Real provider-valid calibration, fresh OOS, adversarial stress and independent
WF1..WF4 replication remain mandatory before terminal closure.
