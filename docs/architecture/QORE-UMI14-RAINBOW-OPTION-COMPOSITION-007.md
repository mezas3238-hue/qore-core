# QORE UMI-14 — Rainbow Option Composition Residual 007

Status: **BOUNDED D04 CROSS-OWNER CORRECTION / NO OPERATIONAL AUTHORITY**

Parent final audit: #363  
Adjudication tracker: #380  
Finding: `F-UMI14-OPTION-COMPOSITION-001`  
Starting exact main: `8bef552a555a1762ad61b2fe6869912eb84e4695`

## 1. Why this residual exists

The existing exotic-option owner is already integrated and retains the previously
certified static semantics for barrier, digital/touch, Asian, lookback, chooser,
compound, cliquet/ratchet, shout and barrier rebate structures.

That owner deliberately left best-of/worst-of/rainbow option semantics unresolved
until a certified cross-asset composition owner existed.

UNR-024 now provides that owner through `ProductCompositionTerms`.

The final UMI-14 reconstruction therefore identified one bounded cross-owner gap:
QORE could represent an option and could represent a basket, but had no typed contract
stating that the option's underlying is that exact basket and that the contractual
rainbow selection is best-of or worst-of.

## 2. External semantic evidence

The ISDA glossary describes a Rainbow as a strategy whose payout uses the performance
of the asset in a basket that performed best or worst relative to the other basket
assets, and notes that it is also known as best-of or worst-of.

FpML's equity-derivative option architecture explicitly permits basket underlyings.

Primary references used for this bounded correction:

- https://www.isda.org/?p=6823
- https://www.fpml.org/spec/fpml-5-1-6-rec-1/html/reporting/fpml-5-1-intro-8.html

These references support a narrow static qualification. They do not authorize QORE
to calculate constituent performance, choose a current winner, value the option or
execute a payoff.

## 3. Existing owners remain authoritative

### UMI-05 option economics

`OptionContractTerms` remains the owner of:

- derivative terms identity;
- option instrument identity;
- underlying identity;
- settlement identity;
- CALL/PUT right;
- strike;
- expiry/exercise;
- settlement style;
- multiplier/notional;
- derivative evidence.

This correction does not copy those fields.

### UNR-024 product composition

`ProductCompositionTerms` remains the owner of:

- composition root identity;
- product composition class;
- ordered/unordered mode;
- component identities;
- local leg IDs;
- roles;
- LONG/SHORT qualification where present;
- ratio/weight/quantity magnitudes;
- quantity units;
- contractual ordinals;
- composition evidence;
- semantic duplicate rejection and canonicalization.

This correction imports the aggregate and class discriminator only. It does not import,
copy or redefine `ProductCompositionLeg`, `ProductCompositionMagnitude`, component IDs,
weights, quantities or ordering rules.

## 4. New bounded surface

The correction adds one enum, one opaque rule code and one aggregate:

- `RainbowOptionSelectionKind`
  - `BEST_OF`
  - `WORST_OF`
- `RainbowPerformanceRuleCode`
- `RainbowOptionCompositionQualification`

Logical schema tag:

`rainbow-option-composition.v1`

No generic `RAINBOW_OTHER`, ranked-payoff DSL, formula tree or arbitrary payoff language
is introduced.

## 5. Rainbow selection semantics

`BEST_OF` and `WORST_OF` identify the static contractual selection direction.

They do **not** identify a currently winning constituent.

The qualification has no field for:

- selected component;
- winning component;
- current performance;
- observed return;
- current constituent level;
- calculated payoff;
- valuation result.

Structural law:

```text
BEST_OF / WORST_OF RULE != CURRENT WINNER
RAINBOW QUALIFICATION != PERFORMANCE OBSERVATION ENGINE
RAINBOW QUALIFICATION != PAYOFF CALCULATION
```

## 6. Performance-rule boundary

"Best" and "worst" are relative to a contractually governed performance definition.
The correction therefore requires `RainbowPerformanceRuleCode`.

It is an opaque canonical lowercase code, not a formula. Examples of governed external
rules may distinguish contractual price-return, total-return or another retained
contract definition without QORE evaluating that definition here.

The code:

- is exact `str`;
- uses bounded canonical lowercase syntax;
- carries no expression AST;
- has no evaluation method;
- grants no market-data or calculation authority.

Structural law:

```text
PERFORMANCE RULE CODE != PERFORMANCE CALCULATOR
OPAQUE GOVERNED RULE != GENERIC PAYOFF DSL
```

## 7. Cross-owner binding laws

`RainbowOptionCompositionQualification` requires exact aggregate types and recursively
revalidates them.

The binding is valid only when:

```text
option.underlying_identity_id == composition.root_identity_id
composition.composition_class == BASKET
```

The first law proves that the option economics refer to the exact composition being
qualified. The second keeps this bounded correction aligned with the ISDA best/worst
basket semantic and prevents accidental interpretation of a spread or arbitrary
multi-leg structure as a rainbow basket.

The composition already requires at least two legs and independently owns all leg
validity/canonicalization laws.

This correction intentionally does not impose new weight, role, direction or ordering
rules on the basket. Those remain UNR-024 authority.

## 8. Why this is a qualification, not another option owner

The aggregate is named `Qualification` because it links two independently certified
owners and adds only the missing best/worst semantic.

It does not create a second vanilla option schema and does not create a second basket
schema.

```text
RAINBOW OPTION COMPOSITION
= UMI-05 OPTION ECONOMICS
+ UNR-024 BASKET COMPOSITION
+ BEST_OF | WORST_OF SELECTION
+ OPAQUE PERFORMANCE RULE

QUALIFICATION != DUPLICATE OPTION OWNER
QUALIFICATION != DUPLICATE BASKET OWNER
```

## 9. Determinism, immutability and revalidation

All additive values use frozen/slotted dataclasses or `StrEnum`.

`logical_values()` re-enters the aggregate validation and recursively calls the
certified owner validations before serialization. Forced post-construction corruption
of the option/composition binding, composition internals, selection or performance rule
therefore fails closed on the next projection.

The projection embeds the complete deterministic owner projections rather than
flattening them or manufacturing a parallel representation.

No wall clock, UUID generation, randomness or global mutable state is introduced.

## 10. Adversarial certification expectations

The dedicated test suite proves at least:

- exact selection set `best-of | worst-of`;
- exact option-underlying ↔ composition-root binding;
- BASKET-only qualification;
- option economics preserved verbatim through owner projection;
- product composition preserved verbatim through owner projection;
- no duplicated leg/magnitude/component fields in the qualification;
- canonical unordered composition remains caller-order independent;
- performance rule is required, canonical and opaque;
- exact aggregate/wrapper/enum runtime types;
- nested composition corruption is detected recursively;
- root-binding corruption is detected recursively;
- selection/rule corruption is detected recursively;
- frozen values;
- no ambiguous third rainbow-selection value;
- no current winner/performance/payoff state;
- no operational or valuation authority.

## 11. Explicit negative space

This owner does not provide or authorize:

- current constituent prices or returns;
- observation/fixing production;
- best/worst winner calculation;
- ranking calculation;
- correlation calculation;
- basket NAV;
- option payoff calculation;
- pricing/valuation/Greeks/implied volatility;
- market data access;
- portfolio/risk state;
- routing/execution/exercise mutation;
- settlement/payment mutation;
- provider capability or network I/O;
- credentials/secrets;
- Production or real capital.

It also does not claim generic Himalaya, ranked-weight rainbow, outperformance or other
multi-factor exotic variants that require additional independently justified contract
material.

## 12. Closure effect

This correction is intended only to close the exact final-reconstruction finding:

`F-UMI14-OPTION-COMPOSITION-001`.

After protected integration and post-merge validation, the remaining mandatory order is:

`#458 final UMI-12 owner-universe recertification -> rerun #363 final UMI-14 audit`.

Closing this finding does not by itself authorize `PROGRAM-D FINAL PASS`, QORE Universal
Market Ready, provider readiness, Production or real capital.
