# CIBO GEN-C3..GEN-C6 — Non-Compensatory Economic Gate V1

Status: **PREREGISTERED / FROZEN / RESEARCH-ONLY**

Gate identity:

`CIBO_GENC3_GENC6_NONCOMPENSATORY_ECONOMIC_GATE_V1`

Frozen at:

`2026-09-30T20:05:00Z`

Semantic digest:

`sha256:6d77b29b321d1dfc36f92adf7a81cdf62cf2221ece3e4631d23daf999c8819af`

## Why this gate exists

GEN-C3, GEN-C4, GEN-C5 and GEN-C6 already had engines, evidence contracts,
causal binders and CI. Those layers intentionally did **not** claim economic
utility.

This gate closes that evaluation gap without changing any engine or reading a
sealed holdout.

## Covered workstreams

- GEN-C3 — Core Compound Portfolio;
- GEN-C4 — Marginal Capital Utility;
- GEN-C5 — Sequential Compounding;
- GEN-C6 — Internal Capital Market.

Each workstream must satisfy its own mechanism condition:

- GEN-C3: complete end-to-end portfolio cycle;
- GEN-C4: the marginal capital unit is identified;
- GEN-C5: chronological sequence is preserved;
- GEN-C6: true scarcity is actually observed.

## Causal surface

Control and treatment must share, independently in each fold:

- the same frozen population SHA;
- the same provider-economic surface SHA;
- the same causal horizon SHA;
- the same protocol binding;
- causal-effect identification;
- treatment preregistered before outcomes.

Future outcome use, weighted scoring, productive authority and certification
claims are forbidden.

## Non-compensatory safety

A treatment fails a fold if it worsens any of:

- maximum drawdown;
- p99 drawdown;
- peak plausible loss;
- peak margin occupancy;
- provider cost;
- realized net delta;
- ending realized capital;
- minimum liquid reserve;
- minimum optionality.

Higher return cannot compensate for deterioration in another mandatory
dimension.

## 4/4 law

Every treatment is evaluated separately against one frozen control in:

`WF1 / WF2 / WF3 / WF4`

All four folds must be safety-no-worse **and** show at least one strict
improvement in that fold.

There is no pooled rescue and no 3/4 acceptance.

Strict improvement may come from:

- realized net delta;
- ending realized capital;
- capital-risk-time productivity;
- lower capital minutes;
- higher liquid reserve;
- higher optionality;
- lower p95 recovery time.

A passing treatment receives only:

`ELIGIBLE_FOR_FURTHER_RESEARCH`

It is not a winner, production promotion or certification.

## Remaining scientific work

This gate does not create the real population. Architect A still requires
provider-valid causal outcomes, fresh OOS, adversarial stress and the frozen
4/4 temporal replication evidence before any terminal scientific disposition.
