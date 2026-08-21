# QORE UMI14 — Exotic Option Full Closure Correction 001

Status: **GATE-B OWNER CORRECTION CANDIDATE — NOT MERGED / NOT SEALED**

Target: `UMI13-UNR-007`

Exact Gate-B starting baseline:

`5e455275a1c2e8704d8c8d8c0c26881b79f81808`

Exact starting tree:

`efb4e2338b9a265607d4cbf98cb2ba9f6f492a07`

Gate-B branch:

`agent/qore-umi14-full-closure-001`

## 1. Purpose

This correction extends the existing bounded D04 exotic-option owner without changing the semantics already certified for barrier, digital/touch, and Asian options.

The correction retains only static contractual material for the currently verified, directly implementable `UMI13-UNR-007` residual:

- fixed-strike and floating-strike lookback terms;
- chooser terms before the CALL/PUT choice is made;
- compound option-on-option relationship semantics;
- cliquet/ratchet reset terms;
- shout-right terms;
- explicit barrier-rebate association.

It does **not** claim full `UMI13-UNR-007` closure. Best-of/worst-of/rainbow option payoff semantics remain split with `UMI13-UNR-024` because basket identity and contractual weights belong to the cross-asset composition authority.

`BOUNDED CORRECTION != FULL UNR-007 CLOSURE`

## 2. Existing authority preserved

The correction reuses and does not replace:

- UMI05 `OptionContractTerms`, `OptionRight`, `DerivativeStrike`, exercise, settlement, sizing, IDs, and evidence primitives;
- UMI09 `StructuredBarrierFeature`, `StructuredFeatureId`, and `StructuredObservationScheduleCode`;
- current `option_exotic_semantics.py` digital/touch/barrier/Asian contracts.

No changes are made to:

- `derivative_contract_semantics.py`;
- `structured_hybrid_synthetic_semantics.py`;
- `fx_semantics.py`;
- `universal_instrument_identity.py`;
- `instrument_universe_registry.py`.

## 3. Lookback terms

`LookbackOptionTerms` is a bounded aggregate rather than a forced `OptionContractTerms` wrapper because UMI05 requires a fixed `DerivativeStrike`, while a floating-strike lookback contract legitimately has no fixed strike.

`LookbackKind` distinguishes:

- `FIXED_STRIKE`;
- `FLOATING_STRIKE`.

A fixed-strike lookback requires `fixed_strike`. A floating-strike lookback forbids it.

The aggregate retains:

- exact derivative terms identity;
- instrument, underlying, and settlement identities;
- CALL/PUT right;
- exact lookback kind;
- optional fixed strike only where financially real;
- observation-window start/end;
- `MIN`/`MAX` extremum role;
- optional governed `StructuredObservationScheduleCode`;
- expiry and exercise terms;
- settlement style;
- evidence;
- multiplier and/or notional.

The observation schedule is an opaque governed schedule code. It generates no dates and grants no scheduler, observation, or valuation authority.

`FLOATING LOOKBACK != VANILLA OPTION WITH FAKE STRIKE`

`LOOKBACK TERMS != OBSERVED EXTREMUM`

## 4. Chooser terms

`ChooserOptionTerms` is separate from `OptionContractTerms` because UMI05 requires one selected `OptionRight`. Before the chooser decision date, no CALL/PUT side has yet been selected.

The bounded classical chooser requires exactly the choice set `{CALL, PUT}`. Caller order is non-semantic and is canonicalized deterministically.

The aggregate retains:

- terms and economic identities;
- allowed rights;
- a real common contractual strike;
- decision date;
- final expiry;
- exercise and settlement terms;
- evidence;
- multiplier and/or notional.

It has no `selected_right`, current choice, choice event, or post-choice valuation state.

`CHOOSER ALLOWED RIGHTS != CHOOSER CURRENT CHOICE`

## 5. Compound option relationship

`CompoundOptionRelationship` composes two complete UMI05 option contracts:

- outer/compound option;
- underlying option.

It enforces both identity and chronology:

`outer_option.underlying_identity_id == underlying_option.instrument_identity_id`

`outer_option.expiry_date < underlying_option.expiry_date`

The two derivative terms IDs must differ.

The complete nested option projections preserve CALL-on-CALL, CALL-on-PUT, PUT-on-CALL, and PUT-on-PUT as distinct contractual material.

`COMPOUND OPTION != OPTION-ON-OPTION VALUATION`

## 6. Cliquet / ratchet static terms

`CliquetOptionFeature` is bound to a parent `OptionContractTerms`; reset dates cannot exist as an orphan schedule detached from the option contract.

It retains:

- immutable reset dates;
- opaque local strike-convention code;
- optional finite local cap/floor;
- optional bounded local reset observation window;
- evidence.

Reset dates are unique, canonicalized, and strictly before the option expiry. If both local floor and cap are present, floor may not exceed cap.

No observed reset level, accrued performance, valuation observation, or pricing model is represented.

`CLIQUET RESET SCHEDULE != OBSERVED RESET LEVEL`

## 7. Shout static terms

`ShoutOptionFeature` is bound to a parent `OptionContractTerms` and retains:

- positive exact shout-right count;
- shout-window start/end;
- opaque locked-in-reference rule code;
- evidence.

It does not store actual shout dates, actual locked-in values, current payoff, or execution state.

`SHOUT RIGHT != SHOUT EVENT`

## 8. Barrier rebate relationship

Existing barrier and payout primitives preserve their own material, but before this correction no bounded aggregate stated that one exact payout is the rebate associated with one exact barrier feature inside one exact barrier option.

`BarrierRebateTerms` therefore binds:

- a `BarrierOptionTerms` parent;
- one exact `StructuredFeatureId` that must occur exactly once in the parent's immutable barrier tuple;
- a reused `DigitalOptionPayout` static payout;
- independent derivative evidence.

No duplicate rebate-condition enum is introduced. Barrier kind/direction/observation remain owned by UMI09, while payout kind/amount/timing remain owned by the existing exotic-option payout type.

`SAME PAYOUT FIELDS != SAME CONTRACTUAL ROLE`

`REBATE TERMS != DIGITAL OPTION BY IMPLICATION`

`REBATE TERMS != PAYMENT MUTATION`

## 9. Determinism and type discipline

All additive values are frozen/slotted dataclasses or `StrEnum` discriminators.

The correction preserves:

- exact caller-supplied IDs and evidence refs;
- exact `date` semantics;
- finite Decimal material;
- strict positive `int` shout count (`bool` rejected);
- immutable tuples;
- canonical ordering for chooser rights and cliquet reset dates;
- complete deterministic `logical_values()` projections.

There is no wall clock, `date.today()`, `datetime.now()`, UUID generation, randomness, filesystem runtime, database, network, provider SDK, retry loop, thread, scheduler, sleep, valuation, execution, settlement mutation, or secret material.

## 10. Full-closure oracle

`tests/infrastructure/test_option_exotic_semantics_full_closure.py` provides independent expected projections and direct fail-closed tests for:

- fake-strike rejection;
- lookback window and exercise chronology;
- exact identity and type guards;
- chooser CALL/PUT choice-set canonicalization without a selected right;
- chooser decision chronology;
- compound identity binding and corrected outer-before-underlying expiry;
- all four compound CALL/PUT forms;
- cliquet reset uniqueness, ordering, expiry boundary, finite cap/floor, and bounded reset window;
- shout count strictness and shout-window chronology;
- rebate exact parent/feature binding;
- frozen/slotted values;
- cross-type Decimal non-flattening;
- absence of operational methods.

Expected material is manually assembled. The expected side does not call SUT `logical_values()`, a production serializer, production sort helper, or fingerprint helper to manufacture the expected projection.

## 11. Explicit remaining UNR-007 material

Best-of/worst-of/rainbow option payoff rules remain a split-authority residual because the option-specific selection rule depends on basket/composition identity and contractual weights owned by `UMI13-UNR-024`.

This Gate-B correction therefore records:

`UNR-007 = PARTIAL CORRECTION / NOT CLOSED`

until the `UNR-024` authority exists and the final UMI14 audit can re-run the complete cross-owner conformance.

## 12. Non-claims

This correction does not authorize or implement:

- basket identity or weights;
- best-of/worst-of/rainbow closure;
- quanto FX ownership;
- generic multi-trigger boolean DSL;
- market-disruption event detection/governance;
- current extrema/reset/shout observations;
- option valuation, Greeks, implied volatility, or pricing;
- provider capability;
- execution or settlement mutation;
- Production or real capital.

`GATE B CORRECTION != GATE C CANDIDATE`

`GATE B CORRECTION != MERGE AUTHORIZATION`

`GATE B CORRECTION != UMI14 SEAL`
