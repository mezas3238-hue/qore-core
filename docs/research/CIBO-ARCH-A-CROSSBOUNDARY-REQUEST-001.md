# CIBO-ARCH-A-CROSSBOUNDARY-REQUEST-001

- request_id: CIBO-ARCH-A-CROSSBOUNDARY-REQUEST-001
- originating_architect: A
- target_architect: B
- affected_workstreams:
  - AS_IS_ECONOMIC_BASELINE
  - T04
  - T08
  - T09
  - T10
  - T12
  - T13
  - T14
  - T15
  - T18
  - T19
  - GEN-C4
  - GEN-C5
  - GEN-C6
  - GEN-C7
  - GEN-C8
  - GEN-C9
  - GEN-C10
  - GEN-C11
  - GEN-C12
  - COMPOUND_ENGINE
  - COMPOUND_PORTFOLIO
  - INTERNAL_CAPITAL_MARKET
  - CAPITAL_GENERATIONS
  - PROTECTED_BASE_CAPITAL
  - PROFIT_PROTECTION
  - PATH_DEPENDENT_MONTE_CARLO
  - ADVERSARIAL_STRESS
  - TEMPORAL_REPLICATION
  - CAPITAL_AMPLIFICATION
- blocking: true

## File needed from Architect B

Architect B should produce, on the B branch only, a durable machine-readable export/manfiest of the provider/Risk/CMA/forward evidence that is legally available after the frozen V3 decision point.

Suggested B-owned artifact identity:

`docs/research/CIBO-ARCH-B-FORWARD-ECONOMIC-EVIDENCE-MANIFEST-V1.json`

The exact file name may differ if B already has a canonical artifact, but B must return the canonical path and immutable evidence SHA.

## Reason

Architect A owns scientific/economic closure but must not invent or reconstruct provider-valid forward facts. A needs a causal population that can be bound to the sealed AS-IS control and the frozen GEN-C treatments without crossing the A/B file boundary.

## Expected contract

Every decision epoch supplied to A must be causally timestamped and, where available, include:

1. account identity and environment;
2. frozen V3 candidate identity and code SHA;
3. decision epoch id and decision timestamp;
4. Trader lineage and signal fingerprint;
5. candidate identity / selected identity / baseline-selected identity;
6. canonical Phase20D qualification fold id (WF1..WF4) for selected settled episodes;
7. pre-outcome decision evidence SHA;
8. selected policy/control/treatment identity;
9. structural stop risk;
10. provider-native requested volume and executable/minimum volume;
11. projected and/or observed margin, with source semantics;
12. provider-native execution cost/slippage evidence where observed;
13. Risk requested -> authorized -> executed lineage plus immutable SHA-256;
14. CMA reservation/allocation/release identifiers plus immutable SHA-256;
15. settlement/deal identifiers, terminal timestamp and settlement SHA-256;
16. realized net PnL only after terminal settlement;
17. capital-release / T20 lineage plus immutable SHA-256;
18. coverage flags required by frozen Phase20D;
19. explicit evidence_kind showing FORWARD_OBSERVED where appropriate;
20. source-manifest SHA-256 and provider-economics SHA-256;
21. no fabricated covariance, hedge credit, netting credit, provider history or missing USD economics;
22. immutable source/artifact hashes sufficient for deterministic replay.

## T16 / T17 provider capability dependency

B must separately expose the provider-verified capability state used for T16/T17:

- SUPPORTED
- CONDITIONALLY_SUPPORTED
- UNAVAILABLE
- UNKNOWN

Missing evidence must remain UNKNOWN / fail-closed, never silently promoted.

## Required tests/evidence from B

- deterministic export/manifest schema validation;
- duplicate decision/outcome rejection;
- timestamp ordering / no outcome-before-decision proof;
- coverage accounting against frozen Phase20D thresholds;
- account identity consistency;
- requested/authorized/executed lineage integrity;
- terminal settlement uniqueness;
- evidence hash reproducibility;
- no pre-freeze decisions in the qualification population;
- exact frozen-candidate identity check.

## Acceptance by A

A will not treat the export as economic proof merely because the manifest exists. A will use it only as the provider/Risk/CMA/forward evidence input to:

- fresh AS-IS baseline measurement;
- causal control/treatment replay;
- Compound chronological replay;
- GEN-C9 path population;
- adversarial stress;
- temporal replication;
- final integrated scientific gates.

If B cannot legally produce one or more fields, the manifest must state the missing field and why. A must not synthesize replacements.

## Boundary rule

Architect B must not edit:

- `docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json`
- A-owned GEN-C policy files
- A-owned Compound scientific policy files
- PR #651 body

Architect A will reconcile the delivered B artifact into the canonical ledger after integration.

## Architect A receiving adapter

A-side contract now implemented at:

`src/qore/infrastructure/cibo_compound_real_population_binding.py`

Preregistration:

`docs/research/CIBO-COMPOUND-REAL-POPULATION-BINDING-V1.md`

The adapter accepts only exact V3, post-freeze, FORWARD_OBSERVED, provider-valid
records with all four canonical Phase20D temporal folds and immutable provider/Risk/CMA/
settlement/release hashes. B does not need to edit the adapter; it only needs to
supply evidence conforming to the contract.


## Architect B CI blocker observed from A branch

A branch revalidation at `1fee6dbd4612df9b408b1af2b62b764371c5e97e`
observed B-owned workflow run:

`github-actions://36757582130/FAILURE`

Workflow:

`QORE CIBO Legacy Stack Quarantine`

Failure is an import-path defect in the B-owned quarantine test:

`ModuleNotFoundError: No module named 'scripts'`

A does not modify the legacy-quarantine implementation or its test. Architect B
must resolve this on the B boundary and return GREEN evidence before final A+B
integration. This observation does not alter A scientific dispositions.


### Latest B-side revalidation

At Architect A HEAD `5cc3ed93166a1960a4dbdc7c1d97f6ed38a56b94`, Legacy Stack Quarantine failed again:

`github-actions://36760959376/FAILURE`

The failure remains B-owned and does not authorize Architect A to edit the
legacy-quarantine implementation. B must return a GREEN quarantine run before
final integrated certification.


## Architect A empirical evidence input contract — V2

Architect A does **not** integrate Architect B implementation. The Integrator
owns branch integration. This section only defines the immutable evidence that A
must receive before A can execute its remaining scientific/economic gates.

### 1. Universal identity and chronology

Every row delivered to A must bind, without inference:

- decision epoch id;
- decision evidence SHA-256;
- decision timestamp;
- signal fingerprint;
- Trader lineage/id;
- frozen candidate id;
- frozen candidate code SHA;
- frozen parameter SHA-256;
- qualification fold `WF1..WF4`;
- account identity fingerprint;
- source-manifest SHA-256;
- evidence kind proving forward observation;
- no pre-freeze contamination;
- no future leakage or outcome-aware refit.

### 2. Provider / execution / Risk / settlement primitives

Where applicable A requires immutable provider-native facts:

- provider key and account reference;
- provider evidence id and provider-economics SHA-256;
- provider observation timestamp;
- provider symbol;
- minimum volume and volume step;
- margin per volume;
- commission per volume;
- slippage reserve per volume;
- bid and ask used by the sealed decision;
- executed source volume;
- executed initial stop-risk USD;
- execution-risk lineage SHA-256;
- terminal CMA settlement SHA-256;
- settlement deal ids;
- realized net PnL USD;
- outcome-observed timestamp;
- T20 release evidence SHA-256;
- released stop-risk capacity;
- released margin capacity;
- terminal release timestamp;
- observed capital-minutes.

A may derive drawdown/productivity only from these canonical chronological
outcomes. A will not synthesize provider economics or substitute current terms
for missing historical terms.

### 3. Compound and capital-state primitives

For Compound/GEN-C2..GEN-C13 scientific closure, the Integrator must expose
legally sourced capital-state facts from the canonical Compound/Integrated
Capital Truth state, including when applicable:

- episode id;
- deployment id;
- market-event id;
- decision id;
- deployed-at timestamp;
- settled-at timestamp;
- source lot id;
- source capital generation;
- deployed capital USD;
- stop-risk USD;
- margin USD;
- protected-floor graduation USD;
- protected-floor evidence SHA-256 when graduation is non-zero;
- minimum realized/base capital over the evaluated path;
- minimum compound capital;
- minimum liquid reserve;
- minimum optionality/capacity reserve;
- capital lock-up duration;
- profit/giveback path needed for retention attribution.

Risk, margin, realized PnL or timestamps may not be reused as stand-ins for a
missing capital-state field.

### 4. Crisis / stress primitives

GEN-C12 and Adversarial Stress require observed or preregistered crisis-factor
evidence, not post-hoc labels. A needs immutable evidence for applicable:

- provider degradation/failure incidence;
- liquidity degradation;
- volatility dislocation;
- correlation convergence;
- margin expansion/pressure;
- drawdown acceleration;
- simultaneous-loss clusters;
- capital lock-up;
- compound giveback;
- reserve/optionality state.

The crisis-factor-set identity must be frozen before treatment evaluation.

### 5. Causal-comparison requirements

For any control/treatment scientific claim:

- control and treatment must use the same frozen population;
- same provider-economic surface;
- same chronological horizon;
- same fold identities;
- same candidate universe where the protocol requires it;
- treatment must have been frozen before outcome use;
- no outcome-selected treatment;
- no weighted-score rescue when a non-compensatory dimension fails;
- empirical FAIL is scientifically consumable and must not be hidden.

Descriptive observed paths are not causal treatment effects.

### 6. A-side acceptance law

Architect A will accept the delivered evidence only when every required field is
present with immutable provenance and the relevant A binder/gate accepts it.

A will reject the package when:

- a required field is missing;
- an identity or lineage drifts;
- settlement/release arithmetic disagrees;
- provider evidence is not pre-decision;
- fold/population comparability fails;
- a field would need imputation or semantic substitution;
- causal identification is claimed only from descriptive OOS paths.

Architect A will not repair missing B/Integrator evidence with synthetic values.
