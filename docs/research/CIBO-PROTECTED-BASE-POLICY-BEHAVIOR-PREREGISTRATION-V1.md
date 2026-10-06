# CIBO Protected Base Policy Behavior Preregistration V1

Status: **SEMANTICS FROZEN / NUMERIC CALIBRATION AND CAUSAL VALUE OPEN**

## Purpose

Freeze what "protected base" is allowed to mean before any numeric protection
policy is calibrated from outcomes.

Canonical implementation:

`src/qore/infrastructure/cibo_protected_base_overlay.py`

## Source law

Protected Base may classify only:

`ORIGINAL_BASE_CAPITAL`

It may not manufacture capital, mutate the source ledger, or convert floating
PnL into protected realized capital.

For every snapshot:

`protected_base_usd <= original_base_available_usd`

## Protection classes

The four classes are distinct and may not be collapsed:

- `ACCOUNTING_PROTECTED`
- `ECONOMICALLY_RESERVED`
- `POLICY_PROTECTED`
- `BROKER_GUARANTEED`

In particular:

`ACCOUNTING_PROTECTED != BROKER_GUARANTEED`

and:

`ECONOMICALLY_RESERVED != PROVIDER_GUARANTEE`

A `POLICY_PROTECTED` state requires immutable policy identity/evidence.

A `BROKER_GUARANTEED` claim requires both policy evidence and explicit
provider guarantee evidence. Missing provider evidence can never be promoted
into a guarantee.

## Authority law

The overlay has no independent:

- runtime authority;
- sizing authority;
- Risk authority;
- execution authority.

It is a research/accounting view until a separately proven policy is admitted
through CIBO governance.

## Numeric-policy law

No numeric graduation, protection or release threshold is selected in this
preregistration.

Any future numeric candidate must:

1. receive a new policy identity and immutable digest;
2. be fixed before its evaluation outcomes are consumed;
3. leave frozen Phase20 V3 unchanged;
4. use reconciled realized-capital evidence only;
5. be compared against the same causal control population;
6. pass the non-compensatory economic gate;
7. pass adversarial stress;
8. replicate independently in WF1..WF4.

If no numeric policy adds robust economic value without safety deterioration,
the correct result is falsification, not threshold retuning on the same
population.

## Non-claim

This closes policy-semantics ambiguity only.

`PROTECTED_BASE_CAPITAL` remains open pending numeric-policy calibration,
fresh causal value proof, stress and temporal replication.
