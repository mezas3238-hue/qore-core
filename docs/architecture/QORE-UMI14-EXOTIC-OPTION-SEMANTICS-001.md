# QORE-UMI14 Exotic Option Static Semantics

Status: **PROGRAM D / UMI-14 LANE-5 CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Tracker: `#380`  
Target: `UMI13-UNR-007`  
Family: `options`  
Starting baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

## 1. Purpose

This additive D04 owner closes the bounded static-semantic portion of UNR-007 that survives exact repository falsification: generic option terms do not by themselves retain digital/touch payout semantics or Asian averaging-in/averaging-out semantics.

The correction deliberately reuses the existing UMI-09 barrier owner instead of creating a second barrier taxonomy.

`GENERIC OPTION != EXOTIC PAYOFF COMPLETENESS`

`STRUCTURED BARRIER FEATURE EXISTS != DIGITAL PAYOUT EXISTS`

## 2. Evidence boundary

Tracker `#380` records the Integration-Gate adjudication based on exact UMI-05 and UMI-09 repository evidence plus primary FpML product semantics.

The present artifact is a correction candidate only. Source, tests and documentation require exact-head CI, independent review and Integration-Gate adjudication before any integration decision.

`CANDIDATE IMPLEMENTATION != CERTIFICATION`

## 3. Existing UMI-05 owner reconstruction

UMI-05 `OptionContractTerms` already owns generic CALL/PUT, typed strike, expiry, exercise terms, settlement style, evidence and multiplier/notional sizing.

Lane 5 therefore does not recreate generic vanilla-option terms.

A critical limitation is intentional and material: `OptionContractTerms.strike` is mandatory. An Asian averaging-in contract may derive its strike from averaging and therefore cannot be represented faithfully by fabricating a fixed `DerivativeStrike` merely to satisfy the vanilla aggregate.

`TYPE REUSE != PERMISSION TO INTRODUCE FALSE CONTRACTUAL DATA`

## 4. Existing UMI-09 owner reconstruction

UMI-09 already owns:

- `StructuredBarrierKindCode`;
- `StructuredBarrierDirection` (`AT_OR_ABOVE`, `AT_OR_BELOW`);
- `StructuredContractLevel`;
- `StructuredObservationTerms`;
- `StructuredObservationMode` (`CONTINUOUS`, `DISCRETE`);
- `StructuredBarrierFeature`.

Those objects retain static barrier level, direction, kind and observation cadence without detecting a barrier event.

Lane 5 therefore does not add a second barrier kind, direction, level or observation system.

`BARRIER TERMS != BARRIER EVENT DETECTION`

## 5. Integration-Gate findings adjudication

### Barrier static semantics

Basic barrier semantics are already sufficiently owned by UMI-09. The bounded correction adds only product composition between a certified generic option and one or more certified `StructuredBarrierFeature` objects.

### Digital / binary / touch

A material gap survived falsification. Existing UMI-05/UMI-09 material does not retain a typed digital payout contract or an explicit touch/no-touch polarity distinct from trigger direction.

### Asian / averaging

A material gap survived falsification. Existing owners do not retain averaging-in versus averaging-out, contractual averaging periods, optional governed schedule references, observation weights or the fact that averaging-in derives the strike rather than using a fixed strike.

### Deferred material

Lookback, generic rebate systems, compound/chooser/cliquet/shout/rainbow/best-of/worst-of, generic boolean payoff DSLs and cross-asset basket semantics remain outside this minimum candidate.

## 6. Barrier reuse boundary

`BarrierOptionTerms` composes:

- existing `OptionContractTerms`;
- a non-empty immutable tuple of existing `StructuredBarrierFeature` objects;
- derivative evidence reference.

Every barrier must reference the option's underlying identity. Barrier feature IDs must be unique. Explicit barrier observation dates may not follow option expiry. Caller tuple order is non-semantic and is canonicalized by feature ID.

No new barrier taxonomy is introduced.

## 7. Barrier-option composition

The composition preserves all generic option material through `OptionContractTerms.logical_values()` and all barrier material through `StructuredBarrierFeature.logical_values()`.

The owner does not evaluate knock-in/knock-out state, current price, touch state, payoff, Greeks or settlement.

## 8. Digital trigger semantics

`DigitalOptionTrigger` reuses one UMI-09 `StructuredBarrierFeature` and adds only two dimensions not owned there:

- trigger style: `EXPIRY` or `TOUCH`;
- touch polarity: `TOUCH` or `NO_TOUCH` when the style is touch-based.

`TOUCH CONDITION != TRIGGER DIRECTION`

`AT_OR_ABOVE` / `AT_OR_BELOW` remain UMI-09 barrier direction. They are not reused as a touch/no-touch flag.

The bounded first candidate supports exactly one digital trigger. Multiple-trigger boolean relationships are deliberately deferred instead of inventing an unverified logical-expression DSL.

An expiry trigger cannot use continuous observation. If expiry observation is represented by explicit dates, the sole explicit date must equal the enclosing option expiry. An opaque governed schedule code remains static and is not resolved by this owner.

## 9. Touch / no-touch distinction

A touch-style trigger requires an explicit `TOUCH` or `NO_TOUCH` value. An expiry-style trigger forbids that field.

For explicit-date expiry triggers, the sole explicit observation date must equal the enclosing option expiry. Opaque external schedule codes remain static governed references; this owner does not resolve them.

## 10. Digital payout semantics

`DigitalPayoutAmount` retains a positive finite Decimal and exact payout-unit `EconomicIdentityId`.

`DigitalOptionPayout` distinguishes:

- `CASH` versus `ASSET` payout kind;
- `IMMEDIATE` versus `DEFERRED` contractual timing;
- exact amount/unit;
- evidence.

No current entitlement, account credit or settlement mutation is represented.

`DIGITAL PAYOUT TERMS != PAYMENT MUTATION`

`DIGITAL PAYOUT AMOUNT != DERIVATIVE NOTIONAL`

## 11. Asian averaging-in / averaging-out / both

`AsianAveragingRole` distinguishes:

- `IN`: averaging derives the strike;
- `OUT`: averaging derives the expiration/settlement observation side while a fixed strike remains contractual;
- `BOTH`: both averaging roles are present.

The role is deterministic logical material and may not be inferred from the presence of a generic strike.

## 12. Averaging-period representation

`AsianAveragingPeriod` supports:

- explicit observations only;
- governed schedule code only;
- governed schedule plus explicit additional observations.

Explicit observations are immutable, unique by date and canonicalized chronologically.

`AsianAveragingObservation` retains an exact date and optional positive finite weight. Weights are retained as supplied and are not normalized or required to sum to one.

`AsianAveragingMethodCode` is an extensible canonical lower-case code. This avoids falsely claiming that a short enum exhausts contractual averaging methodologies while still preserving method identity.

`AVERAGING DEFINITION != CALCULATED AVERAGE`

## 13. Mandatory-strike incompatibility

UMI-05 `OptionContractTerms` requires a `DerivativeStrike`. That is correct for its certified generic owner but not universal for an Asian averaging-in contract.

Lane 5 therefore reuses the exact UMI-05 primitive types where semantics match, while `AsianOptionTerms` is a separate bounded aggregate whose `fixed_strike` is role-dependent.

## 14. Why no fake strike is permitted

Role laws are fail-closed:

- `IN`: requires only averaging-in period; `fixed_strike` must be absent;
- `OUT`: requires only averaging-out period; `fixed_strike` is required;
- `BOTH`: requires both periods; `fixed_strike` must be absent.

A fabricated strike would convert missing contractual material into false data and is therefore forbidden.

## 15. D04 vs D05 / D07 / D10 / D11 / D03

D04 owns only static contract definition here.

Outside this owner:

- current underlying price / observed barrier path / observed touch state: D05;
- calculated average, extrema, payoff valuation, option price, implied volatility and Greeks: D07 or another governed calculation authority;
- exercise instruction/execution: D10;
- payout or rebate payment mutation/finality: D11;
- provider product availability/support: D03.

## 16. FX / #378 boundary

Lane 4 / `#378` owns FX quoted-pair direction, FX spot/forward/NDF/swap and FX put/call currency binding.

Lane 5 does not introduce:

- `FxQuotedCurrencyPair`;
- FX put/call currency ownership;
- NDF semantics;
- FX swap semantics;
- provider FX mapping.

A future FX exotic can compose the generic exotic feature owner with the FX-specific binding without duplicating either authority.

## 17. Deferred lookback / rebate / other exotics

This candidate does not implement:

- fixed/floating lookback;
- observed min/max extrema;
- generic rebate engine;
- compound options;
- chooser options;
- cliquets;
- shout options;
- rainbow/basket/best-of/worst-of options;
- quanto FX ownership;
- generic multi-trigger boolean DSL.

Those require separate bounded evidence if needed for final UMI-14 closure.

## 18. Determinism and security

All new values are frozen/slotted dataclasses. Decimal contractual magnitudes are finite and canonically serialized. Codes use bounded canonical syntax. Dates are exact `date` values. Identities and evidence references are caller supplied.

There is no implicit UUID generation, wall clock, randomness, network, provider SDK, database, filesystem runtime, thread, scheduler, sleep, secret material, valuation engine, observation engine or execution method.

## 19. Test-oracle matrix

The dedicated test module directly falsifies:

- barrier-reference mismatch;
- duplicate barrier feature IDs;
- barrier tuple canonicalization;
- knock-in/out and up/down retained through UMI-09;
- continuous/discrete retained through UMI-09;
- barrier observations after expiry;
- EXPIRY/touch-condition incompatibility;
- TOUCH requiring explicit touch/no-touch;
- touch vs no-touch independent of barrier direction;
- cash vs asset digital payout;
- immediate vs deferred payout;
- positive finite payout amounts;
- single-trigger bounded scope;
- digital trigger underlying binding;
- expiry trigger rejecting continuous observation;
- explicit expiry observation equality;
- post-expiry observation rejection;
- opaque schedule retention without schedule resolution;
- Asian schedule-only, explicit-only and combined representations;
- duplicate observation dates;
- canonical observation order;
- positive finite optional weights;
- no weight normalization;
- averaging-IN without fake strike;
- averaging-OUT requiring fixed strike;
- averaging-BOTH requiring both periods and no fixed strike;
- role-level logical distinctness;
- post-expiry averaging observations;
- extensible canonical averaging-method code;
- multiplier/notional sizing requirement;
- strict date typing;
- frozen/slotted values;
- no operational methods.

`GUARD EXISTS != REGRESSION ORACLE EXISTS`

## 20. Non-claims

`EXOTIC OPTION STATIC SEMANTICS != OPTION VALUATION`

`EXOTIC OPTION STATIC SEMANTICS != IMPLIED VOLATILITY / GREEKS`

`EXOTIC OPTION STATIC SEMANTICS != PATH OBSERVATION`

`EXOTIC OPTION STATIC SEMANTICS != CURRENT BARRIER STATE`

`EXOTIC OPTION STATIC SEMANTICS != EXERCISE EXECUTION`

`EXOTIC OPTION STATIC SEMANTICS != PAYMENT EXECUTION`

`EXOTIC OPTION STATIC SEMANTICS != PROVIDER SUPPORT`

`LANE-5 CANDIDATE != LANE-5 CERTIFICATION`

`LANE-5 CERTIFICATION != UMI-14 PASS`

## 21. Integration-order warning

This candidate begins from the current pre-Lane-3 baseline. Merge order remains:

`LANE 3 / PR #376 -> LANE 4 / PR #382 -> LANE 5 / #380`

Any CI before upstream synchronization is preparatory only. Final Lane-5 certification requires synchronization to then-current main, a new SHA, new exact-head CI, diff audit, independent review, Integration Gate, expected-head merge and post-merge verification.

## 22. Mandatory UMI-12 final follow-up

Before final UMI-14 closure, the cross-asset conformance harness and architecture documentation must be re-evaluated for all newly certified family owners. This bounded candidate does not mutate UMI-12.
