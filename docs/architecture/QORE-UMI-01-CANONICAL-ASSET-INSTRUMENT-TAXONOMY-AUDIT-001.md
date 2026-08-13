# QORE-UMI-01-CANONICAL-ASSET-INSTRUMENT-TAXONOMY-AUDIT-001

## Status

**STAGE-02 / UMI-01 — AUDIT CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #301  
Master roadmap: #303  
Preceding foundation: #302 — CLOSED  
Certified starting baseline: `ac4841c3e55884890af2215f4eee3dc1bca20c1c`

This artifact inventories the current QORE instrument, asset, market-observation, execution, research, portfolio/risk and presentation assumptions that materially constrain universal financial semantics.

It is an audit only. It does **not** implement UMI-02, introduce a new universal identity type, migrate existing contracts, promote PR #298, or claim that any unimplemented asset family is supported.

## Governing rules

```text
QORE CORE IS UNIVERSAL AND NON-SELECTIVE
SYMBOL TEXT != UNIVERSAL INSTRUMENT IDENTITY
PROVIDER-NATIVE ID != ECONOMIC INSTRUMENT IDENTITY
PLATFORM COVERAGE != INSTRUMENT COVERAGE
INSTRUMENT COVERAGE != PLATFORM COVERAGE
YIELD != PRICE
RATE TENOR != FIXED TIMEFRAME
CURVE != SINGLE SCALAR
DOCUMENTED ASSET FAMILY != IMPLEMENTED ASSET FAMILY
CONTRACT FITNESS != OPERATIONAL SUPPORT
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

## Audit method

The audit is anchored to the certified starting baseline. Claims below distinguish:

- **VERIFIED CURRENT CONTRACT** — directly inspected in the baseline;
- **VERIFIED LEAKAGE** — current contract shape cannot preserve a material universal semantic without another typed relationship;
- **REUSABLE FOUNDATION** — current contract is valuable but is not sufficient as universal identity/semantics;
- **NOT CLAIMED** — absence was not proven exhaustively, or the capability belongs to a later stage.

Repository code-search results were used only as locators. Material claims are based on exact-baseline file inspection.

---

# 1. Evidence ledger

## UMI-EVID-01 — Legacy canonical market-data identity — CLOSED

Verified file:

`src/qore/infrastructure/market_data.py`

Current identity:

```python
@dataclass(frozen=True, slots=True)
class Instrument:
    """Canonical provider-neutral instrument symbol."""
    symbol: str
```

The contract validates only an uppercase symbol-like text value.

Current market snapshots bind to that identity:

- `QuoteSnapshot.instrument: Instrument`;
- `OhlcSnapshot.instrument: Instrument`;
- `QuoteRequest.instrument: Instrument`;
- `OhlcRequest.instrument: Instrument`.

`QuoteSnapshot.logical_values()` and `OhlcSnapshot.logical_values()` serialize `instrument.symbol` rather than a typed economic/listing/contract identity.

The same file defines legacy quote/OHLC price fields as positive finite `float` values.

### Classification

**VERIFIED LEAKAGE — SYMBOL-ONLY IDENTITY**

The current `Instrument` can identify a canonical symbol string, but cannot by itself distinguish:

- one economic instrument from multiple listings;
- one futures family from a dated contract;
- continuous futures series from native futures contract;
- option right/strike/expiry/underlying;
- bond issue/maturity/coupon/cash-flow identity;
- swap legs/schedules/index relationships;
- benchmark identity from tradable derivative identity;
- provider-native identifier from economic identity;
- denomination and settlement relationships.

### Reusable foundation

The frozen/slots validation style, deterministic textual validation and provider-neutral boundary remain reusable.

---

## UMI-EVID-02 — Market Evidence v2 precision/provenance with inherited symbol identity — CLOSED

Verified file:

`src/qore/infrastructure/market_observation.py`

Reusable improvements verified:

- `MarketPrice` uses exact finite positive `Decimal`;
- explicit `MarketObservationId`;
- explicit evidence reference;
- explicit `ExternalSourceDescriptor`;
- explicit BID/ASK/MID price-side semantics;
- native vs aggregated OHLC origin;
- explicit missing/invalid OHLC field validity;
- `MarketTimeframe` avoids inventing fixed seconds for D1/W1/MN1;
- `InstrumentMarketSpecification` retains provider symbol and optional provider symbol ID.

But the observations still import and bind:

```python
from qore.infrastructure.market_data import Instrument
```

and both `QualifiedOhlcBarObservation.logical_values()` and `QualifiedQuoteTickObservation.logical_values()` serialize `self.instrument.symbol`.

`InstrumentMarketSpecification` contains:

- `instrument: Instrument`;
- provider-qualified source;
- `provider_symbol`;
- optional `provider_symbol_id`;
- price precision;
- minimum increment;
- effective time;
- evidence.

### Classification

**REUSABLE FOUNDATION + VERIFIED IDENTITY GAP**

Exact Decimal market evidence and provider provenance improve observation quality but do not solve universal economic identity.

```text
EXACT PRICE + PROVIDER ID
!=
UNIVERSAL INSTRUMENT IDENTITY
```

Provider-native identifiers remain boundary facts and must map to a future economic/listing/contract identity rather than replace it.

---

## UMI-EVID-03 — Parallel execution instrument identity — CLOSED

Verified file:

`src/qore/infrastructure/order_intent.py`

Current execution identity:

```python
@dataclass(frozen=True, slots=True)
class ExecutionInstrument:
    value: str
```

It is a separate uppercase symbol-like string abstraction with no typed relationship to `market_data.Instrument`.

`OrderIntent` binds:

- `ExecutionInstrument`;
- BUY/SELL;
- MARKET/LIMIT;
- `OrderQuantity(Decimal)`;
- optional `OrderPrice(Decimal)`.

### Classification

**VERIFIED LEAKAGE — PARALLEL SYMBOL IDENTITIES**

Current QORE has at least two provider-neutral instrument abstractions whose identity material is symbol text:

```text
market_data.Instrument(symbol)
order_intent.ExecutionInstrument(value)
```

No current typed contract in these inspected boundaries proves they refer to the same economic instrument/listing/contract.

This is a migration/compatibility concern for UMI-02. Existing public/internal contracts must not be silently reinterpreted.

---

## UMI-EVID-04 — Futures adapter contract retains native ID but collapses canonical side to symbol — CLOSED

Verified file:

`src/qore/infrastructure/futures_adapter_contracts.py`

`FuturesProviderContractId` retains one provider contract ID.

`FuturesContractMapping` binds:

- provider;
- provider contract ID;
- `instrument: Instrument`.

Its logical values contain the provider ID and `instrument.symbol`.

The inspected mapping does not itself carry typed canonical futures economics such as:

- contract month/series;
- expiry;
- multiplier;
- tick value relationship;
- settlement type;
- delivery/cash-settlement distinction;
- first notice date;
- last trade date;
- underlying/reference identity.

Futures market observations in this contract use positive finite `float` prices; trade/execution quantities use positive integers.

### Classification

**VERIFIED LEAKAGE — PROVIDER CONTRACT ID IS NOT CANONICAL FUTURES IDENTITY**

The mapping is a valid provider adapter foundation, but its canonical target is too narrow to represent complete futures economics.

```text
PROVIDER CONTRACT ID + GENERIC SYMBOL
!=
UNIVERSAL FUTURES CONTRACT IDENTITY
```

This does not invalidate the Futures adapter work. It establishes a required rebase/mapping target after UMI-02.

---

## UMI-EVID-05 — Historical market-data planning is OHLC/timeframe-centric — CLOSED

Verified file:

`src/qore/infrastructure/historical_market_data.py`

`HistoricalOhlcWindow` binds:

- `Instrument`;
- `Timeframe(seconds)`;
- opened/closed timestamps.

The planner constructs contiguous `OhlcRequest` values and its logical values serialize `instrument.symbol` plus timeframe seconds.

### Classification

**VERIFIED LEAKAGE — BAR-CENTRIC HISTORICAL PLANNING**

This is appropriate for OHLC research use cases but is not a universal historical financial-data model.

Universal research later needs to coexist with materially different observation families, for example:

- quote/trade/tick observations;
- yields/rates/curve nodes;
- bond accrued/cash-flow/reference observations;
- option volatility/Greeks where sourced or reproducibly computed;
- funding/mark/index observations;
- corporate actions;
- lifecycle/settlement events;
- RFQ/OTC observations where observable.

UMI-01 does not require replacing the OHLC planner. It identifies that OHLC cannot be the universal observation ontology.

---

## UMI-EVID-06 — Client Execution Agent inherits execution symbol identity — CLOSED

Verified file:

`src/qore/infrastructure/client_execution_agent.py`

`CoreTradeDecision` currently projects a `FunctionalDecision` into provider-neutral execution semantics using:

- `ExecutionInstrument`;
- BUY/SELL;
- MARKET/LIMIT;
- expiry;
- optional `OrderPrice`.

Client execution calculations use `OrderQuantity` and `OrderPrice` for entry/protection.

### Classification

**REUSABLE SERVICE FOUNDATION + VERIFIED UMI-02 REBASE DEPENDENCY**

The authority separation is valid, but the EA cannot become universally instrument-aware while its execution identity is only `ExecutionInstrument(value: str)`.

UMI-02 must provide a governed identity relationship that the future CSP-03 universal EA rebase can consume without making the EA an identity authority.

---

## UMI-EVID-07 — Research economic evidence explicitly externalizes missing instrument economics — CLOSED

Verified file:

`src/qore/infrastructure/research_economic_evidence.py`

Research fill/economic evidence obtains instrument identity through `OrderIntent.instrument`, i.e. `ExecutionInstrument`.

`ResearchGrossEconomicResult` explicitly states that gross P&L is supplied as evidence rather than recomputed from price × quantity because instrument multipliers, pip values and currency conversion are outside that provider-neutral contract.

### Classification

**VERIFIED STRUCTURAL SIGNAL — INSTRUMENT ECONOMICS NOT YET UNIVERSAL**

This is correct defensive behavior for the current contract and must be preserved until richer semantics exist.

It also proves why later stages must not infer universal economics from price and quantity alone:

```text
PRICE × QUANTITY
!=
UNIVERSAL ECONOMIC VALUE
```

Depending on instrument family, valuation/execution economics may require multiplier, contract unit, face value, denomination, FX conversion, accrued interest, funding/carry, cash-flow schedules or other typed terms.

UMI-01 does not authorize adding those values ad hoc to research contracts. They belong to UMI-02+ and FND-04/UMI-03..10.

---

## UMI-EVID-08 — Executive market read models are symbol projections, not identity authority — CLOSED

Verified file:

`src/qore/governance/executive_operational_read_models.py`

Current presentation identity:

```python
@dataclass(frozen=True, slots=True)
class ExecutiveMarketInstrument:
    symbol: str
```

`ExecutiveAssetClass` is an extensible canonical text code, and `ExecutiveMarketSummary` combines symbol + asset class + availability/authorization/regime/session/evidence.

Uniqueness and sorting in the markets projection are based on `instrument.symbol`.

### Classification

**PRESENTATION-SCOPE LEAKAGE / FUTURE PROJECTION DEPENDENCY**

The executive read model is not expected to own economic identity. However, a symbol-only uniqueness key cannot represent two distinct listings/contracts that share a display symbol.

After UMI-02, executive/client surfaces should project stable display information from the canonical identity relationship rather than become an alternate identity source.

---

## UMI-EVID-09 — Portfolio foundation is target-name based and instrument-agnostic — CLOSED

Verified file:

`src/qore/modules/portfolio/contracts.py`

`PortfolioTarget` currently contains:

- `name: str`;
- `weight_bps: int`.

`AllocationIntent` is explicitly logical allocation state without real positions/execution.

### Classification

**REUSABLE FUNCTIONAL FOUNDATION — NOT UNIVERSAL PORTFOLIO SEMANTICS**

The current module correctly avoids pretending to be a full position system. Its target names are not typed instrument identity and must not become such by convention.

UMI-02/FND-05+ must later determine which portfolio targets represent instruments, strategies, sleeves, mandates or other allocation entities, and how those identities relate to canonical instrument/position state.

---

## UMI-EVID-10 — Risk foundation is concentration-by-target, not instrument-economic risk — CLOSED

Verified file:

`src/qore/modules/risk/contracts.py`

The current `RiskPolicy` evaluates soft/hard single-target concentration limits against `PortfolioTarget.weight_bps`.

The module explicitly does not consume market data or execution state in this foundation.

### Classification

**REUSABLE GOVERNANCE FOUNDATION — NOT UNIVERSAL CROSS-ASSET RISK SEMANTICS**

No defect is asserted against the current scope. UMI-01 records that the current Risk foundation does not prove instrument-aware exposures across contract multipliers, rates duration, options Greeks, bond cash flows, margin models, collateral pools or cross-currency economics.

Those capabilities must be built only after identity/economic primitives are certified.

---

# 2. Current identity/taxonomy propagation map

The audited current chain contains multiple identity surfaces:

```text
MARKET DATA
  market_data.Instrument(symbol: str)
       |
       +-> QuoteSnapshot / OhlcSnapshot / requests
       +-> Market Evidence v2 observations
       +-> historical OHLC planning
       +-> provider market specifications
       +-> FuturesContractMapping canonical side

EXECUTION
  order_intent.ExecutionInstrument(value: str)
       |
       +-> OrderIntent
       +-> Client CoreTradeDecision
       +-> Client execution calculation flow
       +-> research fill/economic evidence

PRESENTATION
  ExecutiveMarketInstrument(symbol: str)
       + ExecutiveAssetClass(value: str)
       |
       +-> executive market/trader read models

PORTFOLIO/RISK FOUNDATION
  PortfolioTarget(name: str, weight_bps)
       |
       +-> allocation intent
       +-> concentration risk decision
```

No inspected contract establishes a single typed relationship joining these into one economic instrument/listing/contract identity graph.

That relationship is the core UMI-02 obligation.

---

# 3. Leakage taxonomy

## LEAK-01 — Symbol-only canonical identity — VERIFIED

Current canonical market-data identity is one symbol string.

Risk:

- same display symbol across venues/listings;
- roll/series collisions;
- provider aliases;
- continuous vs native contract confusion;
- benchmark vs tradable instrument ambiguity.

Required downstream action: UMI-02 typed identity relationship.

## LEAK-02 — Parallel identity abstractions — VERIFIED

Current audited abstractions include:

- `Instrument`;
- `ExecutionInstrument`;
- `ExecutiveMarketInstrument`;
- provider-specific contract/symbol identifiers;
- `PortfolioTarget.name` for logical allocation targeting.

They serve different scopes, which is legitimate, but no typed canonical mapping currently unifies their economic referent.

Required downstream action: UMI-02 must define ownership/mapping, not collapse every surface into one god-type.

## LEAK-03 — Provider-native identity can be retained without economic identity — VERIFIED

`InstrumentMarketSpecification` and `FuturesProviderContractId` retain provider-qualified identifiers, which is good provenance.

But provider ID alone cannot establish:

- economic equivalence across providers;
- listing relationship;
- contract-series relationship;
- underlying/reference relationship.

Required downstream action: preserve provider IDs as boundary/listing facts and map them to governed universal identity.

## LEAK-04 — OHLC/timeframe-centric observation assumptions — VERIFIED

Legacy market data and historical planning are dominated by quote/OHLC and fixed-timeframe concepts.

Market Evidence v2 correctly improves timeframe semantics and does not fake D1/W1/MN1 fixed durations, but universal market semantics extend beyond bars.

Required downstream action: UMI-10/UMI-11 later define universal valuation/observation/topology boundaries; do not delete OHLC foundations.

## LEAK-05 — Price representation fragmentation — VERIFIED

Audited boundaries contain:

- legacy market-data `float` prices;
- Futures adapter `float` prices;
- Market Evidence v2 `Decimal MarketPrice`;
- controlled execution `Decimal OrderPrice`.

This does not mean one price type can serve every financial semantic.

Later FND-04/UMI-10 must distinguish at least when applicable:

- market price;
- clean price;
- dirty price;
- yield;
- rate;
- spread;
- discount factor;
- NAV;
- mark/index/reference price;
- implied volatility;
- accrued amount;
- cash-flow valuation;
- funding/carry.

`Decimal` is a numeric representation property, not a semantic type system by itself.

## LEAK-06 — Quantity semantics fragmentation — VERIFIED

Audited boundaries contain:

- `OrderQuantity(Decimal)`;
- Futures trade/execution integer quantities;
- portfolio weights in basis points.

Research explicitly acknowledges multiplier/pip/currency-conversion concerns outside its current contract.

Later FND-04 must distinguish economic quantity/notional/contract units/face value/lot or other family-specific units without forcing one asset's convention onto all assets.

## LEAK-07 — Contract/lifecycle terms not represented by current canonical target — VERIFIED

The audited canonical symbol identity does not carry material contract/lifecycle relationships required by #301, including where applicable:

- listing/venue;
- issue/series;
- expiry/maturity;
- strike/right/exercise;
- underlying/reference;
- denomination;
- settlement;
- multiplier/contract unit;
- lifecycle state.

This statement is about the inspected canonical identity target, not an exhaustive claim that no isolated field with one of these names exists anywhere in the repository.

## LEAK-08 — Fixed-income/rates/curve semantics are not representable through current `Instrument(symbol)` alone — VERIFIED

A symbol plus generic market price cannot encode the required relationships of bonds/rates/curves.

UMI-01 does not claim those later contracts are absent repository-wide. It establishes that the current canonical instrument identity and price/bar boundaries are insufficient to represent them without additional typed semantics.

## LEAK-09 — Derivatives economics are not preserved by current canonical futures mapping — VERIFIED

Current Futures provider mapping retains provider contract ID but maps canonically to generic `Instrument(symbol)`.

UMI-02/UMI-05 must later preserve typed contract identity and relationships without moving provider SDK semantics into Core.

## LEAK-10 — Presentation uniqueness is symbol-based — VERIFIED

Executive read models deduplicate/sort by symbol.

That is acceptable for the current presentation contract but cannot be the universal identity rule.

## LEAK-11 — Research economics cannot yet be derived generically from instrument terms — VERIFIED

Research gross P&L is correctly supplied as evidence because multipliers/pip values/currency conversion are outside the current provider-neutral contract.

This is a deliberate safety property to preserve until universal economics are certified.

---

# 4. Reusable foundations that MUST NOT be discarded

UMI-02 is not a rewrite license.

The following audited patterns are reusable:

1. frozen/slots immutable value objects;
2. typed explicit validation;
3. `ExternalSourceDescriptor` provider/source provenance;
4. explicit evidence references;
5. exact `Decimal` market/execution values where already present;
6. `MarketTimeframe` distinction between fixed and calendar-like periods;
7. provider-native symbol/contract IDs retained as boundary evidence;
8. deterministic `logical_values()`;
9. `MoneyAmount`-style amount/currency binding where applicable;
10. execution idempotency/authorization boundaries;
11. research evidence refusing to invent missing economics;
12. portfolio/risk foundations explicitly limiting their scope instead of pretending to be full universal position/risk systems.

Migration must preserve these properties.

---

# 5. UMI-02 mandatory semantic obligations

UMI-01 does not design the final class graph, but the audit proves UMI-02 must distinguish at minimum the following concepts through typed contracts/relationships where applicable:

## 5.1 Economic identity

A stable QORE identity for the economic instrument/reference object independent of provider symbol text.

## 5.2 Listing / venue identity

One economic instrument may have one or more venue/listing representations.

Listing/venue must not be encoded by informal symbol suffix conventions.

## 5.3 Provider-native identity

Provider IDs/symbols remain explicit boundary facts with evidence and effective/version context where needed.

## 5.4 Family/taxonomy

The model must classify materially different families without using taxonomy as a substitute for identity.

```text
ASSET FAMILY != INSTRUMENT IDENTITY
```

## 5.5 Contract/series identity

Derivatives and other series-based products must preserve contract terms and relationships rather than flatten into symbols.

## 5.6 Lifecycle

Issue/start/active/expiry/maturity/termination/delisting or family-appropriate lifecycle semantics must be representable without assuming every instrument has an expiry.

## 5.7 Underlying/reference relationships

Options, derivatives, indices, benchmarks, structured products and rate products require explicit reference/underlying relationships.

## 5.8 Currency / denomination

Trading currency, denomination, settlement currency and collateral currency are not automatically the same concept.

UMI-02 must leave room for those distinctions without prematurely forcing every family to populate every field.

## 5.9 Settlement relationship

Cash/physical/deliverable/non-deliverable or family-specific settlement semantics must be expressible later without changing base identity assumptions.

## 5.10 Provenance

Identity mappings and externally sourced terms require evidence/provenance; a provider symbol mapping without provenance cannot silently become canonical identity.

---

# 6. Domain impact inventory

## Markets / Instruments — HIGH

Becomes canonical owner of economic identity/reference relationships under the certified departmental freeze.

Must not derive identity from provider adapters.

## Market Data / Market Evidence — HIGH

Observations must bind to the future canonical identity/listing relationship plus source provenance.

Market Data remains owner of dynamic observations, not economic identity.

## Execution — HIGH

`ExecutionInstrument` must eventually become a projection/reference into universal identity rather than a parallel source of truth.

Order/execution contracts must preserve family-specific execution units without embedding provider SDK objects.

## Position / Settlement / Reconciliation — HIGH

Future position truth must bind to exact economic/listing/contract identity. Reconciliation must retain provider-native identifiers as evidence/mapping, not canonical replacements.

## Portfolio — MEDIUM/HIGH

Current target-name allocation is intentionally abstract. Future instrument-targeted portfolio state needs typed identity while still allowing strategy/sleeve/mandate targets that are not instruments.

## Risk — HIGH

Universal risk needs identity-aware exposures and family economics, but should be implemented only after identity + FND-04 primitives are certified.

## Valuation — HIGH

Universal valuation cannot assume last price. UMI-10 later requires typed observation/methodology/provenance semantics.

## Research — HIGH

Datasets, fills and economic results must retain exact instrument/listing/contract identity and economics needed for reproducible cross-asset analysis.

## Client Execution Agent — HIGH

Future universal EA rebase depends on UMI-02 and platform boundary work. EA remains delegated execution only.

## Executive / Client read models — MEDIUM

Presentation symbols remain useful display values, but uniqueness/identity must derive from canonical identities rather than symbol text alone.

## Provider / platform adapters — HIGH

Adapters retain native IDs and translate to canonical identities. Adapters do not define economic identity.

---

# 7. Asset-family audit outcome

UMI-01 does **not** require implementing the following families now. It classifies current universal readiness against #301.

| Family | Current universal identity/semantic status from this audit | UMI destination |
|---|---|---|
| Cash / money market | Not proven universally representable by current symbol identity | UMI-02/03/04 |
| Fixed income / bonds / credit | Current symbol/price boundaries insufficient | UMI-02/03 |
| Rates / curves | Current symbol/timeframe/price model insufficient | UMI-02/04/10 |
| Equities | Existing symbol model usable as legacy display/reference, not universal listing identity | UMI-02/06 |
| Funds / pooled vehicles | Not proven universal | UMI-02/06 |
| Indices / benchmarks | Need benchmark vs tradable-instrument distinction | UMI-02/06/11 |
| FX | Existing foundations significant but symbol text does not prove universal FX identity/forward/swap semantics | UMI-02/05 |
| Futures | Provider contract IDs exist, canonical contract semantics incomplete | UMI-02/05/07 |
| Options | Current generic identity cannot preserve option terms | UMI-02/05 |
| Forwards / swaps / OTC | Current generic identity cannot preserve leg/schedule/reference semantics | UMI-02/05/11 |
| Commodities | Need economic commodity/reference vs dated derivative identity | UMI-02/07 |
| Crypto / digital assets | Need venue/network/spot/perp/funding identity relationships | UMI-02/08/11 |
| Structured / hybrid | Generic symbol insufficient for payoff/component identity | UMI-02/09 |
| Volatility / variance | Need measure/index/derivative distinction and provenance | UMI-02/05/10 |
| Securities financing / borrow | Need financing/borrow/repo terms and identities | UMI-02/03/05 |
| Baskets / spreads / multi-leg / synthetic | Need explicit composition, not fake primitive symbol | UMI-02/09 |

`NOT PROVEN UNIVERSAL` is not equivalent to `ABSENT`. It means current audited canonical contracts do not provide enough verified semantics for a universal-support claim.

---

# 8. Compatibility and migration constraints for UMI-02

UMI-02 must not perform an uncontrolled big-bang replacement.

Required migration principles:

```text
NO SILENT SYMBOL REINTERPRETATION
NO PROVIDER-NATIVE ID AS CANONICAL ECONOMIC ID
NO PARALLEL NEW SOURCE OF TRUTH
NO ADAPTER SDK TYPE IN CORE CONTRACTS
NO BIG-BANG BREAKAGE WITHOUT COMPATIBILITY PLAN
```

UMI-02 must classify each existing type as one of:

- retained unchanged;
- retained as display/provider projection;
- extended compatibly;
- mapped through an additive adapter/bridge;
- deprecated through an explicit migration path;
- replaced only with proven blast-radius handling.

In particular:

- `Instrument` cannot silently change meaning from symbol to universal object without migration analysis;
- `ExecutionInstrument` cannot silently become economic identity without execution-boundary analysis;
- `ExecutiveMarketInstrument` should remain a presentation projection rather than become canonical owner;
- provider symbol/contract IDs remain external/boundary mappings;
- existing OHLC/research datasets must preserve reproducibility and lineage during identity migration.

---

# 9. PR #298 impact

PR #298 remains useful cTrader/provider-instrument-catalog work.

UMI-01 does not merge, rewrite or reject that implementation.

The architecture gate remains:

```text
CTRADER-SPECIFIC CATALOG CORRECTNESS
!=
UNIVERSAL INSTRUMENT IDENTITY
```

PR #298 may only be reconsidered for universal-foundation promotion after UMI-02 defines the certified identity/lifecycle relationship and the PR is rebased/re-reviewed for compatibility on its then-current exact head.

Historical CI/review evidence for PR #298 does not authorize a future changed head.

---

# 10. Findings ledger

## GAP-UMI-01 — Universal economic instrument identity missing from audited canonical boundaries — HIGH

Evidence: current market identity is `Instrument(symbol: str)`; execution and executive projections have separate symbol abstractions.

Required next stage: UMI-02.

## GAP-UMI-02 — Listing/venue/provider mapping is not a complete canonical identity graph — HIGH

Evidence: provider symbol/provider ID can be retained, but canonical mapping target remains generic symbol identity.

Required next stage: UMI-02.

## GAP-UMI-03 — Derivative contract/lifecycle/reference semantics not carried by current canonical mapping target — HIGH

Evidence: inspected Futures mapping has provider contract ID + generic `Instrument`; missing canonical typed terms in the mapping target.

Required stages: UMI-02/05/07.

## GAP-UMI-04 — Universal valuation semantic types are not established by current market price boundaries — HIGH

Evidence: legacy float prices coexist with Decimal price contracts; semantic dimensions such as yield/rate/NAV/IV are distinct obligations.

Required stages: FND-04 / UMI-03/04/10.

## GAP-UMI-05 — Universal quantity/economic-unit semantics not established — HIGH

Evidence: Decimal OrderQuantity, integer Futures quantities, bps portfolio weights, and explicit research non-recomputation due missing multiplier/pip/conversion.

Required stages: FND-04 / UMI-03/05/07.

## GAP-UMI-06 — Historical/research observation ontology remains heavily OHLC/execution-symbol centric — MEDIUM/HIGH

Evidence: historical planner is OHLC/timeframe based; research economic evidence inherits ExecutionInstrument.

Required stages: UMI-02/10/11 + Program G lineage work.

## GAP-UMI-07 — Presentation models use symbol uniqueness — MEDIUM

Evidence: Executive market/trader read models use symbol-only instrument projection and symbol deduplication.

Required action: later projection rebase after UMI-02; not a reason to move identity ownership into presentation.

## GAP-UMI-08 — Portfolio/Risk foundations are identity-agnostic rather than universal instrument-economic models — MEDIUM

Evidence: portfolio target name + weight; risk concentration over target weights.

Required action: preserve current scope; extend only after identity/economic primitives and department charters are certified.

---

# 11. UMI-02 work-order requirements generated by this audit

The next stage must produce a typed, immutable, deterministic, provider-neutral identity/lifecycle foundation that can pass adversarial examples from materially different families.

Minimum design questions UMI-02 must answer:

1. What is the stable economic instrument/reference identity?
2. How are listings/venues represented independently from economic identity?
3. How are provider-native IDs mapped with provenance and effective scope?
4. How are series/contracts represented without forcing expiry onto non-expiring instruments?
5. How are underlying/reference links represented?
6. How are denomination/trading/settlement currency relationships represented?
7. How is lifecycle modeled without one enum flattening every family?
8. How are continuous/synthetic/composite identities distinguished from native primitives?
9. How do legacy `Instrument`, `ExecutionInstrument` and presentation identities migrate without breaking evidence/replay?
10. How does canonicalization preserve deterministic `logical_values()` and secret hygiene?
11. What compatibility boundary lets PR #298 map cTrader native instruments into the new model?
12. What minimal adversarial conformance tests prove the model can represent a bond, listed equity, dated future, option, FX pair, benchmark/index and multi-leg/reference relationship without semantic distortion?

UMI-02 must not implement every family-specific economic term. It must provide the identity/lifecycle/reference foundation on which UMI-03..09 can add family semantics without redesigning identity.

---

# 12. Explicit non-claims

This audit does **not** claim:

- QORE has no support for FX, Futures or other existing bounded scopes;
- every use of a symbol string is a defect;
- `Decimal` alone solves financial semantics;
- every price must use one universal price class;
- every quantity must use one universal unit;
- all instruments have expiry, venue, underlying or settlement fields;
- every isolated bond/options/rates-related symbol or helper in the repository has been exhaustively proven absent;
- UMI-02 implementation already exists;
- PR #298 is invalid;
- current Futures work should be deleted;
- current Portfolio/Risk foundations are wrong for their declared scope;
- current OHLC/replay work is invalid;
- any new asset family is operationally supported;
- production is authorized.

The audit claims only that current inspected canonical boundaries are insufficient for the universal financial semantics required by #301/#303 and identifies the exact architectural gaps that UMI-02+ must close.

---

# 13. Case status

Evidence cases completed by repository inspection:

```text
UMI-EVID-01 CLOSED
UMI-EVID-02 CLOSED
UMI-EVID-03 CLOSED
UMI-EVID-04 CLOSED
UMI-EVID-05 CLOSED
UMI-EVID-06 CLOSED
UMI-EVID-07 CLOSED
UMI-EVID-08 CLOSED
UMI-EVID-09 CLOSED
UMI-EVID-10 CLOSED
```

Audit findings remain OPEN obligations for downstream implementation:

```text
GAP-UMI-01 OPEN -> UMI-02
GAP-UMI-02 OPEN -> UMI-02
GAP-UMI-03 OPEN -> UMI-02/05/07
GAP-UMI-04 OPEN -> FND-04 / UMI-03/04/10
GAP-UMI-05 OPEN -> FND-04 / family stages
GAP-UMI-06 OPEN -> UMI-02/10/11 + Program G
GAP-UMI-07 OPEN -> downstream projection rebase
GAP-UMI-08 OPEN -> later Portfolio/Risk universalization
```

These gaps are not defects that block UMI-01 certification; discovering and correctly bounding them is the purpose of UMI-01.

## UMI-01 closure gate

UMI-01 itself remains `ACTIVE` until this exact artifact passes:

```text
EXACT-HEAD QUALITY GATE
-> INDEPENDENT ADVERSARIAL REVIEW
-> CORRECTION IF REQUIRED
-> EXACT-HEAD RE-REVIEW
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> EXPECTED-HEAD MERGE
-> VERIFY MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> MARK UMI-01 CLOSED IN #301
```

Issue #301 remains OPEN after UMI-01 because UMI-02 through UMI-14 remain outstanding.

Only after UMI-01 is explicitly `CLOSED` may STAGE-03 / UMI-02 begin.