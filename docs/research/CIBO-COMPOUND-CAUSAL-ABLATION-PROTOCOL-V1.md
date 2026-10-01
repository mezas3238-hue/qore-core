# CIBO Compound Causal Ablation Protocol V1

Status: **PREREGISTERED BEFORE QUALIFYING ECONOMIC OUTCOMES**

Identity:

`CIBO_COMPOUND_CAUSAL_ABLATION_PROTOCOL_V1`

Freeze boundary:

The Git commit that first introduces this artifact is the protocol freeze. Any decision epoch earlier than that commit timestamp is ineligible for this protocol. The sealed 2017H1 holdout is excluded from development and may not be used to define, tune, rescue, or rank any treatment.

## Purpose

Freeze the N vs N+1 comparison law before Architect A receives the provider-valid fresh population from Architect B.

The protocol exists to prevent:

- multi-mechanism bundling;
- outcome-selected treatments;
- unequal control/treatment populations;
- provider-economics drift;
- causal-horizon drift;
- rescue by aggregate return;
- post-hoc threshold changes;
- opening the sealed holdout during development.

## Root control

The root AS-IS identity remains:

`CIBO_GENERATION_CURRENT_CONTROL_V1`

Git SHA:

`87d98ced8d56b275823c4472392923ba6a11d769`

Local control policies already frozen inside individual GEN-C engines remain valid, but every final economic comparison must retain a traceable lineage back to the same sealed AS-IS control generation.

## One-mechanism law

Each causal ablation may change exactly one declared mechanism.

A treatment that changes two or more of the following at once is invalid for first-pass attribution:

- profit graduation;
- marginal-capital utility eligibility;
- sequential-compounding eligibility;
- scarcity clearing / Internal Capital Market allocation;
- profit preservation / giveback handling;
- adaptive compound speed;
- growth/ruin/capacity rule;
- transition-model use;
- MPC planning;
- crisis-capital intelligence use;
- memory-conditioned hypothesis use.

Integrated stacks may be evaluated only after their component mechanisms have separately received a terminal scientific disposition.

## Canonical first-pass comparison families

### GEN-C2

Control:
current realized-profit handling under the sealed AS-IS generation.

Treatment:
one preregistered profit-graduation rule.

Changed mechanism:
classification / protection / reserve / compound admission of already-realized profit only.

Must not change:
Trader decision, Risk, execution, provider economics, stop geometry, treatment population.

### GEN-C4

Control:
current capital-use evidence path.

Treatment:
one preregistered marginal-capital eligibility rule.

Changed mechanism:
whether the next marginal unit is economically eligible.

Must not:
invent size, use a weighted utility score as a substitute for causal evidence, or use future outcomes.

### GEN-C5

Treatment identity:

`CIBO_GENC5_PROTECTED_FLOOR_GATED_SEQUENTIAL_COMPOUND_SHADOW_V1`

Changed mechanism:
sequential compound eligibility only.

Treatment amount remains the exact upstream GEN-C4 amount; GEN-C5 may not resize it.

### GEN-C6

Treatment identity:

`CIBO_GENC6_ROBUST_PARETO_MARGINAL_CAPITAL_MARKET_SHADOW_V1`

Changed mechanism:
scarcity clearing between one legal marginal deployment and `RESERVE_NO_DEPLOYMENT`.

True scarcity is mandatory for economic proof. Capital abundance alone cannot close GEN-C6.

### GEN-C7

Treatment identity:

`CIBO_GENC7_PROFIT_PRESERVATION_GIVEBACK_SHADOW_V1`

Changed mechanism:
profit preservation / harvest / reserve / compound action only.

The treatment cannot resize an upstream proposal or treat accounting protection as a broker guarantee.

### GEN-C8

Changed mechanism:
compound-speed posture / timing only.

Forbidden interpretation:
posture-to-lot or confidence-to-size conversion.

### GEN-C9

Changed mechanism:
one preregistered growth/ruin/capacity family at a time.

Economic verdict:
use only the already-frozen
`CIBO_GENC9_NONCOMPENSATORY_ECONOMIC_GATE_V1`.

Higher return may not compensate safety deterioration.

### GEN-C10

GEN-C10 is first a calibrated descriptive transition model, not an allocation winner.

No GEN-C11 economic claim is admissible until GEN-C10 transition uncertainty is calibrated on legal chronological evidence.

### GEN-C11

Changed mechanism:
multi-period planning using already-calibrated GEN-C10 causal worlds.

Must use identical known-option sets and provider constraints between control and treatment. Future opportunity identities are forbidden.

### GEN-C12

Changed mechanism:
use of crisis-capital intelligence under the same crisis population.

Risk remains independent and authoritative. Crisis intelligence may not waive provider, Risk, margin, or execution constraints.

### GEN-C13

GEN-C13 is post-outcome memory only.

A memory episode may influence only a later chronological hypothesis or decision. It may never be fed backward into the episode that created it.

### GEN-C14

GEN-C14 is governance, not an economic treatment.

It evaluates preregistered hypotheses through the frozen pipeline and cannot rescue a failed hypothesis by changing its gate.

## Population equality law

For every valid control/treatment pair, Architect A must prove:

1. identical causal decision population;
2. identical provider constraint surface;
3. identical provider-economics semantics;
4. identical causal horizon;
5. identical qualification fold;
6. identical outcome coverage requirements;
7. no pre-freeze decision epochs;
8. no synthetic replacement of missing fields;
9. no holdout data in development;
10. no treatment choice after outcome inspection.

If any item differs, the pair is invalid rather than merely lower quality.

## Non-compensatory economic law

Safety is evaluated before upside.

A treatment cannot be eligible if it worsens any mandatory safety dimension under the frozen GEN-C9 gate, including ruin/capacity fragility, drawdown, plausible loss, minimum capital, underwater duration, or recovery.

Only after safety is no worse may strict economic improvement be considered.

No weighted score may make a safety failure pass.

## Replication law

The already-preregistered temporal rule applies:

`WF1 / WF2 / WF3 / WF4`

All four folds must independently pass the same frozen economic gate.

There is no 3/4 rescue and no pooled-outcome override.

## Falsification

If a preregistered treatment fails its frozen causal/economic gate, its proper disposition is falsification or continued external-dependency blocking where evidence is legally unavailable.

The treatment may not be silently retuned against the same qualifying outcomes.

## Non-claims

This protocol does not claim that:

- a qualifying real population already exists;
- any treatment adds economic value;
- fresh OOS has passed;
- stress has passed;
- temporal replication has passed;
- any GEN-C workstream is terminal;
- CIBO is certified.

It freezes comparison law only so later real-data results can be interpreted without hindsight.
