# QORE-UMI14 Exotic Option Static Semantics

Status: **PROGRAM D / UMI-14 LANE-5 CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Adjudication tracker: `#380`
Implementation PR: `#384`
Target: `UMI13-UNR-007`
Family: `options`
Current baseline: `b30f0847f4962fd12a8506fea61f797e402a8a9c`

## 1. Purpose

This additive D04 owner closes the bounded static-semantic portion of UNR-007 that survives exact repository falsification: generic option terms do not by themselves retain digital/touch payout semantics or Asian averaging-in/averaging-out semantics.

The correction deliberately reuses the existing UMI-09 barrier owner instead of creating a second barrier taxonomy.

`GENERIC OPTION != EXOTIC PAYOFF COMPLETENESS`

`STRUCTURED BARRIER FEATURE EXISTS != DIGITAL PAYOUT EXISTS`

## 2. Evidence boundary

Adjudication tracker `#380` records the Integration-Gate adjudication based on exact UMI-05 and UMI-09 repository evidence plus primary FpML product semantics. PR `#384` carries this bounded implementation candidate.

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

`AsianOptionTerms` also retains optional `strike_factor`. It is a finite Decimal with no positivity restriction. `None`, `0`, positive and negative finite values are distinct contractual material. It does not replace `fixed_strike` or change role-presence rules.

## 12. Averaging-period representation

`AsianAveragingPeriod` supports:

- explicit observations only;
- governed schedule identities only;
- governed schedules plus explicit observations.

A period must have at least one representation.

Explicit observations are immutable and unique by complete locator identity.

`AsianAveragingObservation` retains a locator and optional non-negative weight.

### Literal date locator

`AsianAveragingLiteralDate` retains an exact calendar date.

### Literal datetime locator

`AsianAveragingLiteralDateTime` retains an exact timezone-aware `datetime`. It enables multiple observations on the same calendar date without fabricating midnight. Timezone-aware timestamps are retained exactly and never silently normalized.

Expiry qualification for a literal datetime uses that locator's own contractual calendar date (`locator.value.date()`). D04 deliberately does not normalize the timestamp to UTC or invent an expiry time before comparing it with the contractual expiry date.

### Schedule observation locator

`AsianAveragingScheduleObservation` retains a governed schedule code and positive integer observation number. It identifies an observation by schedule identity plus observation number. It does not generate or resolve schedule dates.

### Multiple schedules

`AsianAveragingPeriod.schedule_codes` is an immutable tuple of governed schedule identities. Schedule codes must be unique. Caller schedule order is non-semantic.

A schedule-observation locator inside a period must reference one of that period's schedule identities.

### Unweighted vs weighted

`AsianAveragingObservationKind` explicitly distinguishes `UNWEIGHTED` from `WEIGHTED` explicit observation lists.

`UNWEIGHTED`:
- literal date/dateTime locators allowed;
- schedule-number locator forbidden;
- every weight must be `None`.

`WEIGHTED`:
- literal date/dateTime and schedule-number locators allowed;
- weight may be `None`, `0`, or positive finite Decimal.

The discriminator is mandatory whenever explicit observations are present, and absent when explicit observations are empty.

Weights are retained as supplied and are not normalized or required to sum to one.

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

`strike_factor` does not alter these role rules.

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
- generic multi-trigger boolean DSL;
- market disruption mechanics.

FpML market-disruption material exists, but it is outside this bounded UNR-007 correction and requires a separately governed contractual/event-qualification owner.

## 18. Determinism and security

All new values are frozen/slotted dataclasses. Decimal contractual magnitudes are finite and canonically serialized. Codes use bounded canonical syntax. Dates are exact `date` values. DateTimes are exact timezone-aware `datetime` values. Identities and evidence references are caller supplied.

There is no implicit UUID generation, wall clock, randomness, network, provider SDK, database, filesystem runtime, thread, scheduler, sleep, secret material, valuation engine, observation engine or execution method.

## 19. Test-oracle matrix

The dedicated test modules directly falsify:

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
- duplicate observation locators;
- canonical observation order;
- non-negative optional weights including zero;
- no weight normalization;
- strike-factor finite typing and logical sensitivity;
- literal date and timezone-aware datetime locators;
- multiple same-day datetime observations;
- same-instant/different-offset datetime locators remaining distinct exact contractual locators;
- schedule observation number typing and binding;
- multiple schedule identities and canonical schedule ordering;
- unweighted vs weighted logical distinction;
- unweighted weight/schedule-locator rejection;
- weighted literal/schedule locator acceptance;
- averaging-IN without fake strike;
- averaging-OUT requiring fixed strike;
- averaging-BOTH requiring both periods and no fixed strike;
- role-level logical distinctness;
- post-expiry averaging observations;
- extensible canonical averaging-method code;
- multiplier/notional sizing requirement;
- strict date/dateTime typing;
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

## 21. Integration-order status

This candidate is currently synchronized to base `b30f0847f4962fd12a8506fea61f797e402a8a9c`.

It is preparatory only. Certification requires a new exact head, exact-head CI, diff audit, independent review, Integration Gate adjudication, protected merge and post-merge verification.

## 22. Mandatory UMI-12 final follow-up

Before final UMI-14 closure, the cross-asset conformance harness and architecture documentation must be re-evaluated for all newly certified family owners. This bounded candidate does not mutate UMI-12.
