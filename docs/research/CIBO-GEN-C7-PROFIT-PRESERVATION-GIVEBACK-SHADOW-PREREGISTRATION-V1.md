# CIBO GEN-C7 — Profit Preservation / Harvesting / Giveback Shadow V1

## Status

**PREREGISTERED / RESEARCH-ONLY / NO PRODUCTIVE AUTHORITY**

Policy identity:

`CIBO_GENC7_PROFIT_PRESERVATION_GIVEBACK_SHADOW_V1`

Freeze:

`2026-09-29T23:30:00Z`

Frozen policy digest:

`sha256:fc6a9b32da8d6595cffb51a73525a929d976f84960439b8e0c22f90561a406e7`

This generation does not modify frozen GEN-C5 V1, GEN-C6 V1 or the current V3
Phase20 candidate. It does not open the sealed 2017H1 holdout.

## Scientific question

Can CIBO improve realized-profit preservation and reduce avoidable giveback
without degrading base-capital survival, compound-capital survival, tail risk,
optionality or future capital productivity?

## Economic laws

1. Floating PnL is not realized capital.
2. Profit is capital; it is not permission to weaken Risk.
3. "House money" is forbidden as a sizing rationale.
4. Protected capital cannot silently become deployable again.
5. A higher ending balance cannot compensate for unacceptable DD/tail/floor
   violations.
6. C7 may compare PROTECT / HARVEST / RESERVE / COMPOUND proposals, but V1 does
   not invent proposal amounts.
7. Proposal amounts and rationale must arrive pre-outcome from separately
   identified evidence.
8. Control and treatment are sealed before later outcome reconciliation.

## Canonical state metrics

Every pre-outcome state must expose independently:

- current realized capital;
- peak realized capital;
- current base capital;
- peak base capital;
- current compound capital;
- peak compound capital;
- protected profit;
- protected capital floor;
- strategic reserve;
- opportunity reserve;
- compoundable capital;
- realized-profit giveback;
- profit retention ratio;
- base drawdown;
- compound drawdown;
- floor growth rate.

All metrics are descriptive state. None grants capital authority.

## Control

Frozen control:

`HOLD_CURRENT_CAPITAL_STATE`

Amount:

`0 USD`

## Treatment

Treatment may accept exactly one preregistered proposal:

- `PROTECT`
- `HARVEST_TO_STRATEGIC_RESERVE`
- `RESERVE_OPPORTUNITY_CAPACITY`
- `COMPOUND`

V1 never resizes the proposal.

A treatment proposal is eligible only when:

- decision time is post-freeze;
- state and proposal are same-account;
- state is realized-capital only;
- proposal evidence is pre-outcome;
- proposal is calibrated;
- proposal is explicitly capital-eligible;
- proposal amount is finite positive;
- proposal carries a positive evaluation horizon frozen pre-outcome;
- amount is available in the declared source bucket;
- no protected-floor decrease is implied;
- no Risk/Execution authority is embedded.

Otherwise treatment must equal control.

## Source-bucket legality

- PROTECT: amount must be available in realized-but-unprotected profit.
- HARVEST_TO_STRATEGIC_RESERVE: amount must be available in realized-but-
  unprotected profit.
- RESERVE_OPPORTUNITY_CAPACITY: amount must be available in compoundable or
  released compound capacity.
- COMPOUND: amount must be available in compoundable or released compound
  capacity.

C7 cannot source a proposal from protected floor, broker-guaranteed floor,
floating PnL, another account, or fabricated capacity.

## V1 outputs

For every decision seal:

- policy id / SHA / freeze timestamp;
- state SHA;
- proposal SHA;
- preregistered evaluation horizon;
- control action / amount;
- treatment action / amount;
- blocker codes;
- giveback amount;
- profit retention ratio;
- floor growth rate;
- base DD;
- compound DD;
- treatment/control divergence;
- explicit no-outcome/no-authority flags.

## Fresh OOS promotion requirements

Before any economic utility claim, freeze separately:

- minimum post-freeze decision epochs;
- minimum treatment/control divergence epochs;
- minimum realized-profit-path coverage;
- minimum account / Trader representation;
- temporal folds;
- settlement/release coverage;
- stress gates;
- DD/tail non-degradation gates;
- profit-retention gate;
- optionality gate.

Those thresholds are not defined by this engineering preregistration and may not
be chosen after inspecting C7 economic outcomes.

## Stress requirements before promotion

At minimum:

- profit buffer followed by loss cluster;
- rapid giveback sequence;
- simultaneous Trader losses;
- delayed capital release;
- opportunity scarcity;
- opportunity abundance;
- margin shock;
- provider cost degradation;
- correlation convergence;
- rapid regime reversal.

## Terminal scientific states

V1 must eventually end as one of:

- VALIDATED / REPLICATED / CERTIFICATION_READY;
- FALSIFIED;
- REJECTED;
- INELIGIBLE;
- NOT_APPLICABLE.

`ENGINEERING GREEN` is not an economic verdict.

## Governance

```text
runtime authority = FALSE
Risk authority = FALSE
Execution authority = FALSE
DEMO governed mutation = FALSE
LIVE = FALSE
real capital = FALSE
holdout opened = FALSE
GEN-C5 V1 mutated = FALSE
GEN-C6 V1 mutated = FALSE
```

## Causal OOS binding law

Every durable decision seals the initial realized-capital state, the exact
proposal action/source/amount and a positive evaluation horizon before outcome.
The OOS binder may measure the account path observed at that exact horizon, but
it must keep:

```text
treatment_effect_identified = FALSE
counterfactual_treatment_pnl_computed = FALSE
economic_utility_ready = FALSE
certification_ready = FALSE
```

until a separately preregistered causal economic protocol identifies the
control/treatment effect. Coverage or a favorable realized path is not utility.
