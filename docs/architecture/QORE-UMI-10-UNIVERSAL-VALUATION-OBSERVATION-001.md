# QORE-UMI-10 — Universal Valuation Observation Boundary

Status: IMPLEMENTATION CANDIDATE — NOT CERTIFIED  
Tracking: #355  
Program: #301 / #303  
Certified starting baseline: `ff2db4c75f0e3ff620ce14da356e6c65640d3c6f`  
Predecessor: UMI-09 / #352 / PR #354 — CERTIFIED/CLOSED  
Related but distinct: #350 — D07 Computed Valuation Methodology / Producer / Reproducibility Boundary

## 1. Mission

UMI-10 defines the minimum provider-neutral immutable D07 boundary for typed valuation
observations. It binds canonical economic identity, exact temporal semantics, a bounded
family-specific value, and either external-observed provenance or retained QORE-computed
input lineage.

It does **not** implement a pricing engine, select an identity mapping revision, prove
external evidence truth, execute a methodology, mutate positions/cash/settlement, or
authorize production.

Canonical inequalities:

```text
D05 MARKET OBSERVATION != D07 VALUATION OBSERVATION
PRICE != YIELD != RATE != SPREAD != NAV != IMPLIED VOLATILITY
OBSERVED EXTERNAL VALUE != QORE-COMPUTED VALUE
PROVIDER-COMPUTED BUT EXTERNALLY PUBLISHED != QORE-COMPUTED
Instrument.symbol != EconomicIdentityId
EVIDENCE REF != EVIDENCE CONTENT/TRUTH
FINGERPRINT != RETAINED INPUT EVIDENCE
METHODOLOGY IDENTITY != METHODOLOGY IMPLEMENTATION
AS-OF DATE != AS-OF INSTANT != AS-OF INTERVAL
OBSERVATION CONTRACT != VALUATION PRODUCER
```

## 2. Authority boundaries

| Authority | Owner | UMI-10 treatment |
|---|---|---|
| Economic/listing identity and mapping revisions | D04 / UMI-02 | retain exact supplied mapping/binding; validate consistency only |
| Raw provider market evidence | D05 | retain exact D05 object + exact field selector |
| Calendar/lifecycle/currentness policy | D06 | no resolver/scheduler authority |
| Valuation observation semantics | D07 / UMI-10 | owner of this contract |
| Valuation methodology execution/producer | D07 / #350 | explicitly not implemented here |
| Account/collateral/portfolio | D08 | no mutation |
| Risk/exposure | D09 | no authority |
| Order/execution | D10/D18 | no authority |
| Settlement/cash mutation | D11 | no authority |

## 3. Exact baseline evidence

The exact baseline audit established:

- D05 `QualifiedQuoteTickObservation` retains exact BID/ASK `MarketPrice`, legacy
  `Instrument`, source, timestamp, and evidence reference.
- D05 `QualifiedOhlcBarObservation` retains source, legacy instrument, timeframe,
  BID/ASK/MID side, origin, open/close interval, exact OHLC fields, and evidence reference.
- UMI-02 owns `EconomicIdentityId`, `ListingIdentityId`, `ExternalIdentifier`,
  `ExternalIdentityMappingRevision`, and exact listing→economic binding.
- UMI-03 already separates fixed-income price, yield, spread, and contractual cash flows.
- UMI-04 already separates zero/par/forward rates and discount factor; a
  `RateTermStructureNode` additionally asserts curve membership and must not be fabricated
  for an independent scalar observation.
- UMI-06 `FundNavBasis` contains structural NAV basis only, no NAV value/calculation authority.
- UMI-08 owns crypto-perpetual MARK/INDEX/LAST semantic roles; observed values remain D07.
- UMI-05 contains contractual strikes but no canonical implied-volatility or model-price value.
- Existing fingerprints do not substitute for retained source material.
- `ExternalSourceDescriptor` identifies an external source/adapter/port; it is not evidence content.

No inspected owner already provided one D07 carrier satisfying identity + time + typed
measure + observed/computed provenance. Therefore the implementation is additive.

## 4. Value-family design

UMI-10 deliberately uses a bounded union, not `Decimal + enum`.

| Family | Representation |
|---|---|
| D05 exact market price | `D05MarketPriceMeasure` derived from exact D05 retained source |
| Fixed-income price | `FixedIncomePriceMeasure(FixedIncomePrice)` |
| Fixed-income yield | `FixedIncomeYieldMeasure(FixedIncomeYield, YieldConvention)` |
| Fixed-income spread | `FixedIncomeSpreadMeasure(FixedIncomeSpread, reference_identity)` |
| Standalone zero/par/forward rate | certified UMI-04 scalar + convention + bounded coordinate |
| Discount factor | certified `DiscountFactor` + bounded coordinate |
| Fund NAV | `FundNavValue` + exact UMI-06 `FundNavBasis` |
| Implied volatility | dedicated finite non-negative `ImpliedVolatility`; zero valid |
| Model/theoretical value | `QuotedValuationValue` + explicit model-output code |
| Crypto-perpetual price | explicit quoted value + exact UMI-08 role and pricing terms |
| Contractual cash-flow value | exact UMI-03 `FixedIncomeCashFlow` + valued quote |

No universal Premium is introduced. The exact cross-family premium semantic was not
established by repository evidence.

No global price-role enum is introduced. D05 BID/ASK/MID remain D05 semantics; UMI-08
MARK/INDEX/LAST remain crypto-perpetual semantics; a model output remains a distinct
D07 measure rather than masquerading as market evidence.

## 5. D05 → UMI-02 → D07 identity bridge

For exact D05 market evidence:

```text
EXACT D05 OBJECT
+ exact field/side selector
+ exact LEGACY_QORE ExternalIdentifier
+ exact supplied ExternalIdentityMappingRevision
+ exact ListingIdentity when target is listing
+ final EconomicIdentityId
-> observed valuation source
```

The exact D05 legacy identifier must be:

```text
kind      = LEGACY_QORE
namespace = market-data.instrument
value     = exact Instrument.symbol
```

If mapping target is `EconomicIdentityId`, it must equal the final economic identity.
If target is `ListingIdentityId`, exact `ListingIdentity` is mandatory and its
`economic_identity_id` must equal the final identity.

UMI-10 **does not select** the current/latest/precedence mapping revision. It may reject a
supplied revision that cannot apply to an exact source instant or interval. Selection among
overlapping revisions remains D04/D06 authority.

## 6. Temporal semantics

Closed temporal union:

- `ValuationAsOfInstant`: timezone-aware, canonical UTC microseconds.
- `ValuationAsOfDate`: strict `date`; rejects `datetime`.
- `ValuationAsOfInterval`: exact timezone-aware open/close interval with positive span.

D05 quote BID/ASK is point evidence and maps to the quote `observed_at` instant.

D05 OHLC OPEN/HIGH/LOW/CLOSE is conservatively retained as the source bar interval.
UMI-10 does not invent an exact tick time for a bar field.

For a supplied mapping revision:
- point evidence must lie in its effective window;
- interval evidence must be fully covered;
- date-only facts are not coerced to midnight solely to compare with datetime windows.

No cross-source `recorded_at` chronology is inferred. #333 remains open.

## 7. Observed provenance

`D05QuoteValuationSource` and `D05OhlcValuationSource` retain the exact D05 source object,
the exact selector, and the exact UMI-02 identity binding. The selected price is derived
from the retained D05 object; a caller does not provide a duplicate Decimal.

Quote selectors allow BID or ASK only. QORE cannot take BID+ASK and relabel the derived
midpoint OBSERVED. If a provider publishes MID in an owned D05 representation, that is a
separate external observation fact.

`PublishedValuationSource` covers externally published non-D05 valuation values. It retains:
source observation ID, `ExternalSourceDescriptor`, exact identity binding, exact temporal
role, typed measure, and evidence reference. Provider-scoped identity source must match
the published valuation source.

A provider may have computed the value internally; if QORE merely receives it, QORE
classifies the value as OBSERVED.

Evidence references remain opaque references and never become claims that evidence
content/truth is embedded.

## 8. Computed provenance

A QORE-computed carrier requires:

```text
ValuationMethodologyIdentity(
  family,
  schema_version,
  software_revision
)
+ non-empty immutable ValuationComputedInput tuple
+ unique explicit input roles
+ deterministic canonical order
+ retained exact leaf sources
+ internally derived SHA-256 input fingerprint
+ output evidence reference
```

`input_fingerprint` is `init=False`; callers cannot supply it.

Inputs are non-recursive in UMI-10. A `ValuationComputedInput` accepts an observed leaf
source, not another `ObservedValuationObservation` or `ComputedValuationObservation`.
The tuple is bounded to 64 inputs. This makes cycles/depth unrepresentable in this slice.

UMI-10 does not execute or certify the methodology. Concrete computation/producer
authority remains #350.

A `ComputedValuationObservation` cannot use `D05MarketPriceMeasure`, because that measure
means an exact externally observed D05 price. Derived model values use their own measure
family.

## 9. Determinism and fail-closed rules

- frozen/slots dataclasses;
- explicit UUIDs; no implicit `uuid4`;
- finite Decimal; positivity only where family semantics require it;
- canonical Decimal material including zero;
- canonical UTC microsecond instants;
- strict date vs datetime;
- immutable tuples;
- deterministic computed-input ordering;
- unique input roles;
- internally derived fingerprint;
- no arbitrary mutable metadata/parameter dictionaries;
- no callback/AST/formula/eval/exec;
- no wall clock/random/global mutable state;
- no provider/network/retry/sleep/thread/scheduler;
- no pricing/evaluate/calculate engine methods;
- no account/risk/execution/settlement mutation.

## 10. PRE-CHK-UMI10 disposition

All PRE-CHK-UMI10-00..34 remain mandatory adversarial oracles:

- 00–03: reuse D05 + exact UMI-02 bridge; no second system or symbol identity.
- 04–05: source descriptor/evidence reference never become evidence content/truth.
- 06–10, 23–24: retained deterministic leaf inputs + derived fingerprint +
  versioned methodology + non-recursive bounded graph.
- 11–14, 16, 27–28: family-specific semantics; no scalar collapse or curve-node fabrication.
- 15: QORE-derived midpoint cannot be OBSERVED.
- 17: no valuation engine.
- 18: cash-flow value remains separate from D11 settlement mutation.
- 19, 31, 33: no currentness/precedence/cross-clock authority.
- 20, 34: canonical instant and strict date/instant/interval distinction.
- 21, 25–26: bounded immutable state, no arbitrary executable/I/O authority.
- 29–30: no UMI-09 event truth and no support/readiness promotion.
- 32: exact listing→economic binding retained.

## 11. Non-claims

Existence or certification of UMI-10 does not establish:

- a concrete pricing/valuation methodology exists;
- any pricing model is implemented;
- a value is economically correct;
- external evidence content has been independently proven;
- an identity mapping resolver/currentness policy exists;
- market-data ingestion support beyond existing D05 boundaries;
- a barrier/autocall event occurred;
- a position/cash/settlement mutation;
- provider/product/platform support;
- production or real-capital readiness;
- closure of #332, #333, #350, #146, #286, PR #298, research producer/lineage gaps,
  D16 failover completeness, or external in-flight side-effect containment.

## 12. Integration law

```text
EXACT BASELINE AUDIT
-> OWNER/COLLISION DECISION
-> MINIMUM ADDITIVE IMPLEMENTATION
-> ADVERSARIAL TESTS
-> DIFF / AUTHORITY AUDIT
-> DRAFT PR
-> EXACT-HEAD QORE CI
-> COVERAGE PATH AUDIT
-> FREEZE EXACT HEAD/TREE/BLOBS
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE
-> CORRECTION LOOP IF REQUIRED
-> EXPECTED_HEAD_SHA MERGE
-> VERIFY ACTUAL MERGE
-> VERIFY MAIN == MERGE AND AHEAD=0/BEHIND=0
-> CERTIFIED BASELINE
```

`CI GREEN != ENGINEERING APPROVAL`.
`READY FOR INTEGRATION GATE != MERGED`.
`MERGED != CERTIFIED UNTIL POST-MERGE VERIFICATION`.
