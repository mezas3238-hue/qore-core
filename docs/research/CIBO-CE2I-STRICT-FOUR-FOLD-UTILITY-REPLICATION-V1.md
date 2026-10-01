# CIBO CE2I — STRICT FOUR-FOLD UTILITY REPLICATION V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL EVIDENCE REQUIRED**

Identity:

`CIBO_CE2I_STRICT_FOUR_FOLD_UTILITY_REPLICATION_V1`

## Scope

This contract closes an Architect-A engineering gap for:

- T06 Profit-Funded Expansion;
- T07 Protected-Capacity Expansion;
- T14 Dynamic De-Risking;
- T15 Capital Optionality.

Their existing economic gates judge one legal population. Ordinary scientific
closure also requires the same frozen treatment to survive the canonical
temporal replication law independently.

T08 Factor Neutralization already constructs temporal folds internally; this
change hardens its contract so the fold count is exactly four and cannot be
relaxed by configuration.

## Canonical law

The only accepted temporal replication surface is:

```text
WF1 PASS
WF2 PASS
WF3 PASS
WF4 PASS
---------
REPLICATED
```

Anything else is `FALSIFIED` for the frozen replication claim.

No 3/4 rule, pooled rescue, weighted rescue, cross-fold compensation or
post-outcome winner selection is permitted.

## Distinct populations

WF1..WF4 must bind four distinct population digests.

Reusing the same outcome population under multiple fold labels is invalid.

## Frozen treatment

Across all four folds:

- control candidate identity is unchanged;
- treatment candidate identity is unchanged;
- workstream/kind is unchanged;
- protocol-binding SHA-256 is unchanged.

Changing the treatment after observing an earlier fold is protocol drift, not
replication.

## T06/T07

Each fold must independently receive
`ELIGIBLE_FOR_FURTHER_RESEARCH` from the existing frozen
`CIBO_T06_T07_NONCOMPENSATORY_EXPANSION_UTILITY_GATE_V1`.

The temporal wrapper does not weaken any safety dimension in that gate.

## T14/T15

Each fold must independently receive
`ELIGIBLE_FOR_FURTHER_RESEARCH` from
`CIBO_T14_T15_CAUSAL_PARETO_UTILITY_GATE_V1`.

T15 causal-identification requirements remain inside the underlying gate and
cannot be bypassed by temporal replication.

## T08 hardening

`assess_t08_fresh_oos_netting_ablation` keeps the API parameter for
compatibility but now accepts only:

`required_folds = 4`.

Any other value is a contract violation.

## Non-claims

This contract does not claim fresh OOS success, stress success, temporal
replication success, scientific completion, production authority, governed
DEMO authority, LIVE authority or certification.

The sealed 2017H1 holdout remains untouched.
