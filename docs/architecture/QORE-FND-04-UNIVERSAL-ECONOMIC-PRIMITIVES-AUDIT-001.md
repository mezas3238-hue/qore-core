# QORE-FND-04-UNIVERSAL-ECONOMIC-PRIMITIVES-AUDIT-001

## Status

**STAGE-04 / FND-04 — AUDIT CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #310  
Master roadmap: #303  
Related universal market/instrument program: #301  
Preceding certified foundation: FND-03 / UMI-02 — CLOSED via PR #309  
Certified starting baseline: `89705ed8c5cc3e4bf39a74ec2c37111a52285f8f`

This artifact audits the current QORE repository for semantic assumptions and authority boundaries involving quantity, notional, units, prices, monetary values, rates, yields, spreads, time, tenor, venue/provider/source/account identities, portfolio identity, collateral and related cross-domain primitives.

It is an **audit and architecture freeze only**. It does not introduce a universal money, quantity, rate, tenor, portfolio or account implementation; it does not implement UMI-03..14; it does not migrate legacy contracts; it does not promote PR #298; and it does not claim operational support for any unimplemented financial family.

The purpose of FND-04 is to freeze the semantic separations that later family and department contracts must preserve so that QORE does not create a convenient but incorrect universal scalar model.

---

# 1. Governing invariants

```text
QORE CORE IS UNIVERSAL AND NON-SELECTIVE
NUMERIC REPRESENTATION != ECONOMIC SEMANTIC
DECIMAL != UNIVERSAL FINANCIAL TYPE
UUID SHAPE != IDENTITY AUTHORITY
QUANTITY != NOTIONAL
QUANTITY != PORTFOLIO WEIGHT
PROVIDER VOLUME != CANONICAL ECONOMIC QUANTITY
CONTRACT COUNT != FACE VALUE != BASE UNITS != TOKEN UNITS
MULTIPLIER != QUANTITY
TICK SIZE != TICK VALUE
PRICE != MONETARY VALUE
PRICE != YIELD
PRICE != RATE
MARKET PRICE != VALUATION RESULT
EXECUTION PRICE != REFERENCE PRICE
CLEAN PRICE != DIRTY PRICE
RATE != YIELD WITHOUT EXPLICIT SEMANTICS
SPREAD NUMERIC VALUE != SPREAD ECONOMIC MEANING
BASIS-POINT STORAGE != ECONOMIC SEMANTIC
TENOR != MARKET TIMEFRAME
CALENDAR PERIOD != FIXED SECONDS
INSTANT != DURATION
OBSERVED TIME != EFFECTIVE TIME != RECORDED TIME
SETTLEMENT DATE != MATURITY != MARKET SESSION
VENUE != PROVIDER != ADAPTER != SOURCE
ECONOMIC IDENTITY != LISTING IDENTITY != PROVIDER-NATIVE ID
ACCOUNT IDENTITY != PROVIDER ACCOUNT REFERENCE
ACCOUNT IDENTITY != CLIENT IDENTITY
ACCOUNT IDENTITY != EXECUTION AUTHORITY
ACCOUNT IDENTITY != PORTFOLIO AGGREGATION
PORTFOLIO TARGET NAME != PORTFOLIO IDENTITY
COLLATERAL != CASH BALANCE != MARGIN USED
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO REPRODUCIBILITY -> NO PROMOTION
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

---

# 2. Audit method and claim discipline

The audit is anchored to exact baseline `89705ed8c5cc3e4bf39a74ec2c37111a52285f8f`.

Repository search is used only as a locator and as bounded negative evidence where explicitly qualified. Material positive claims are grounded in direct file inspection.

Classifications used in this artifact:

- **VERIFIED CURRENT CONTRACT** — directly inspected implementation at the baseline;
- **REUSABLE BOUNDED FOUNDATION** — valid contract for its current scope, not a universal semantic authority;
- **VERIFIED SEMANTIC COLLISION** — two or more current contracts use the same numeric/identity representation for materially different meanings;
- **VERIFIED STRUCTURAL GAP** — inspected contracts prove a missing relationship/semantic distinction needed for the roadmap;
- **NOT PROVEN IMPLEMENTED** — repository search/inspection did not establish an implementation; this is not an exhaustive absence claim;
- **DEFERRED BY DESIGN** — semantics intentionally belong to a later UMI/department stage;
- **MIGRATION CONSTRAINT** — current valid behavior must remain compatible while future canonical semantics are added.

This audit deliberately refuses two shortcuts:

```text
MANY SMALL TYPES -> COLLAPSE INTO ONE UNIVERSAL GOD TYPE
```

and

```text
ONE REUSABLE EXISTING TYPE -> SILENTLY PROMOTE IT TO GLOBAL AUTHORITY
```

Neither is acceptable without evidence that the semantics are actually identical.

---

# 3. Evidence ledger

## FND04-EVID-01 — Controlled order quantity and price are exact but semantically narrow — CLOSED

Verified file:

`src/qore/infrastructure/order_intent.py`

Verified current contracts:

```python
@dataclass(frozen=True, slots=True)
class OrderQuantity:
    value: Decimal
```

`OrderQuantity` requires a finite positive `Decimal`.

```python
@dataclass(frozen=True, slots=True)
class OrderPrice:
    value: Decimal
```

`OrderPrice` also requires a finite positive `Decimal`.

`OrderIntent` binds:

- `ExecutionInstrument`;
- BUY/SELL;
- MARKET/LIMIT;
- `OrderQuantity`;
- optional `OrderPrice` for LIMIT;
- explicit idempotency identity and timestamp.

### Analysis

The contracts correctly provide exact provider-neutral execution intent values. They do **not** establish, by themselves:

- whether quantity means shares, contracts, lots, base units, quote units, face amount, token units or another family unit;
- an economic/notional amount;
- a contract multiplier;
- a face/par amount;
- denomination/currency of `OrderPrice`;
- price kind such as clean/dirty/mark/index/NAV/reference;
- a typed relationship to the UMI-02 economic/listing identity graph.

Therefore:

```text
OrderQuantity(Decimal) != UniversalQuantity
OrderPrice(Decimal) != UniversalPrice/Value/Rate/Yield
```

### Classification

**REUSABLE BOUNDED EXECUTION FOUNDATION + VERIFIED UNIVERSAL SEMANTIC GAP**

Do not change this contract merely to reuse its names globally. Future execution rebase must project from certified economic terms into execution-scoped quantity/price values.

### Temporal observation

`OrderIntent.logical_values()` serializes `created_at` with direct `.isoformat()`. The timestamp is timezone-aware, but equivalent instants represented under different offsets can produce different strings.

This is recorded under FND04-GAP-TIME-01 below; it is not silently corrected by this audit.

---

## FND04-EVID-02 — Legacy market data carries float prices and fixed-second timeframe — CLOSED

Verified file:

`src/qore/infrastructure/market_data.py`

Verified current contracts:

```python
@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
```

```python
@dataclass(frozen=True, slots=True)
class Timeframe:
    seconds: int
```

The `Timeframe` docstring defines the current object as a canonical OHLC timeframe expressed as a positive whole number of seconds.

`QuoteSnapshot` and `OhlcSnapshot` use positive finite `float` price fields.

OHLC request/snapshot validation requires:

```python
(closed_at - opened_at).total_seconds() == timeframe.seconds
```

### Analysis

This is a valid legacy OHLC boundary. It cannot become the universal temporal model because:

- a financial tenor such as 3M is not generally a fixed number of seconds;
- a daily/weekly/monthly market period may be calendar/session defined;
- maturity and settlement dates are not OHLC timeframes;
- business-day conventions can alter date schedules;
- rate curve nodes/tenors are not market-data bar intervals.

Legacy price floats also do not establish universal price/value semantics.

### Classification

**REUSABLE LEGACY MARKET-DATA FOUNDATION + VERIFIED FIXED-DURATION LIMITATION**

`Timeframe(seconds)` remains valid where a fixed-duration OHLC contract is explicitly required. It must not be silently reinterpreted as `Tenor`, `CalendarPeriod`, `Maturity`, `SettlementInterval` or all market timeframe semantics.

---

## FND04-EVID-03 — Market Evidence v2 provides stronger Decimal/timeframe semantics but remains observation-scoped — CLOSED

Verified file:

`src/qore/infrastructure/market_observation.py`

Verified reusable contracts:

- `MarketPrice(value: Decimal)` — exact positive finite decimal;
- `MarketPriceSide` — BID / ASK / MID;
- `MarketOhlcField` with explicit VALID/MISSING/INVALID state;
- `MarketBarOrigin` — NATIVE / AGGREGATED;
- `MarketTimeframeCode` — current catalog M1..H12 plus D1/W1/MN1;
- `MarketTimeframe.fixed_seconds` — integer only for fixed intraday codes; `None` for D1/W1/MN1;
- `QualifiedOhlcBarObservation`;
- `QualifiedQuoteTickObservation`;
- `InstrumentMarketSpecification` with provider-qualified precision/minimum increment/effective time/evidence.

The module also has an explicit canonical timestamp helper:

```python
value.astimezone(UTC).isoformat(timespec="microseconds")
```

### Analysis

This is a strong reusable market-evidence foundation.

Important limits remain:

1. `MarketPrice` means a market price/increment in this boundary; it is not a money balance, cash P&L, yield, rate, discount factor, NAV or arbitrary valuation result.
2. `QualifiedQuoteTickObservation.spread` is the arithmetic ask-minus-bid difference in the same price dimension. It is not automatically a credit spread, yield spread, option spread or rate spread.
3. `MarketTimeframe` correctly avoids faking calendar durations, but its code catalog is a market-bar identity catalog, not a universal financial tenor ontology.
4. `InstrumentMarketSpecification` still binds legacy `Instrument`, not the certified UMI-02 `EconomicIdentityId` / `ListingIdentityId` graph.

### Classification

**REUSABLE BOUNDED MARKET-EVIDENCE FOUNDATION**

Do not duplicate its good properties. Future UMI-10 valuation observations should reuse the principles of exact value, explicit semantic kind, source/evidence and canonical time while keeping distinct economic dimensions.

---

## FND04-EVID-04 — Futures contracts expose materially different quantity/price representation — CLOSED

Verified file:

`src/qore/infrastructure/futures_adapter_contracts.py`

Verified current semantics include:

- quote `bid` / `ask`: positive finite `float`;
- trade `price`: positive finite `float`;
- trade `quantity`: positive `int`;
- execution request `quantity`: positive `int`;
- limit/stop prices: optional positive finite `float`;
- cumulative filled quantity: non-negative `int`;
- `FuturesProviderContractId` retained separately;
- `FuturesContractMapping` maps provider contract ID to legacy `Instrument`.

### Analysis

The contrast with `OrderQuantity(Decimal)` is intentional evidence that numeric representation is boundary-specific today.

A futures integer quantity is naturally compatible with whole contract counts in this adapter, but it does not establish universal economic quantity because later economics may also need:

- contract multiplier;
- contract unit;
- tick size;
- tick value;
- denomination/settlement currency;
- underlying/reference identity;
- notional relationship.

The same module validates `FuturesBarObservation` using exact `Timeframe.seconds`, which is valid for its current fixed-duration contract but cannot become the universal calendar/tenor rule.

Multiple timestamp-bearing `logical_values()` also use direct `.isoformat()`.

### Classification

**REUSABLE FUTURES ADAPTER FOUNDATION + VERIFIED QUANTITY/PRICE/TIME FRAGMENTATION**

---

## FND04-EVID-05 — Research explicitly proves price × quantity is not universal economic value — CLOSED

Verified file:

`src/qore/infrastructure/research_economic_evidence.py`

The module reuses:

- `OrderPrice`;
- `OrderQuantity`;
- `MoneyAmount`.

`ResearchGrossEconomicResult` explicitly states that gross cash P&L is supplied as evidence rather than recomputed from price × quantity because instrument multipliers, pip values and currency conversion remain outside that provider-neutral contract.

### Analysis

This is direct repository evidence for the constitutional rule:

```text
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
```

Depending on family, a reproducible economic-value derivation may require combinations of:

- contract count / units;
- multiplier / point value;
- face/par/notional;
- quote/denomination/settlement currency;
- FX conversion evidence;
- accrued interest;
- cash-flow schedule;
- funding/carry;
- price/yield methodology;
- valuation model and inputs.

FND-04 must preserve the current fail-safe behavior: missing economics must remain explicit missing evidence, not inferred by a generic formula.

### Classification

**VERIFIED STRUCTURAL GAP + REUSABLE FAIL-SAFE RESEARCH BEHAVIOR**

---

## FND04-EVID-06 — MoneyAmount is a strong reusable money binding, but its current currency contract is bounded — CLOSED

Verified file:

`src/qore/infrastructure/proprietary_accounts.py`

Verified contracts:

```python
@dataclass(frozen=True, slots=True)
class CurrencyCode:
    value: str
```

`CurrencyCode` accepts exactly three uppercase ASCII letters.

```python
@dataclass(frozen=True, slots=True)
class MoneyAmount:
    currency: CurrencyCode
    amount: Decimal
```

`MoneyAmount` requires a finite `Decimal`, normalizes canonical zero and binds amount to currency explicitly.

The proprietary account financial snapshot uses `MoneyAmount` for:

- balance;
- equity;
- unrealized P&L;
- margin used.

The same `MoneyAmount` is imported/reused by inspected account-policy, research and client read-model contracts. The audit does **not** claim multiple independent `MoneyAmount` class definitions from search matches; the inspected paths reuse the proprietary-account definition.

### Analysis

This is good design for money-like account/cash values and should not be discarded.

But two boundaries must be frozen:

1. `MoneyAmount` is monetary amount, not market price, yield, quantity, notional identity or generic scalar.
2. Current `CurrencyCode` is a three-letter account/money currency code. It is not proven sufficient as universal identity for every digital asset, commodity unit, settlement asset, collateral asset or economic reference object.

UMI-02 already allows currencies to exist as canonical reference-object economic identities and deliberately did not promote this account-specific `CurrencyCode` into universal instrument identity.

### Classification

**REUSABLE MONEY FOUNDATION; NOT GLOBAL ECONOMIC-IDENTITY AUTHORITY**

Migration rule:

```text
MoneyAmount MAY remain a bounded money primitive
CurrencyCode MAY remain a bounded currency code
NEITHER silently becomes the UMI-02 EconomicIdentity authority
```

A later explicit bridge may map a currency code to a certified currency reference identity where needed.

---

## FND04-EVID-07 — Basis points are already used for different economic meanings — CLOSED

Verified files:

- `src/qore/infrastructure/proprietary_accounts.py`;
- `src/qore/infrastructure/account_policy.py`;
- `src/qore/modules/portfolio/contracts.py`;
- `src/qore/modules/risk/contracts.py`.

Verified uses:

- `DrawdownBps` — drawdown ratio;
- `ProfitSplitBps` — client profit entitlement ratio;
- `PortfolioTarget.weight_bps` — portfolio allocation weight;
- `RiskPolicy.soft_single_target_limit_bps` / `hard_single_target_limit_bps` — concentration thresholds.

### Analysis

The integer basis-point representation is useful, deterministic and strict. The economic meanings are not interchangeable.

It would be incorrect to create one universal `RateBps` and permit these values to flow into:

- bond yield;
- coupon rate;
- benchmark rate;
- credit spread;
- funding rate;
- portfolio allocation;
- risk concentration;
- profit split;
- drawdown

without a semantic type/role.

### Classification

**VERIFIED SEMANTIC COLLISION**

Canonical rule:

```text
BASIS POINTS = REPRESENTATION / SCALE
BASIS POINTS != ECONOMIC SEMANTIC
```

Family-specific rates/yields/spreads may use basis points as an encoding where justified, but semantic identity must remain explicit.

---

## FND04-EVID-08 — Portfolio foundation has weights but no verified canonical portfolio identity — CLOSED

Verified file:

`src/qore/modules/portfolio/contracts.py`

`PortfolioTarget` contains:

- `name: str`;
- `weight_bps: int`.

`AllocationIntent` requires target weights to sum to 10,000 bps and explicitly represents logical allocation intent without real positions/execution.

Repository search for `PortfolioId` at this baseline did not return an implementation result.

### Analysis

Current `PortfolioTarget.name` is intentionally abstract. It may represent an instrument, strategy, sleeve, mandate or other allocation target depending on future design; it must not be silently reinterpreted as an instrument identity or portfolio identity.

The absence of a verified `PortfolioId` from this bounded search does not prove no portfolio-related identifier exists under every possible name. It proves that FND-04 has no evidence to promote a canonical `PortfolioId` today.

### Classification

**REUSABLE ALLOCATION FOUNDATION + CANONICAL PORTFOLIO IDENTITY NOT PROVEN IMPLEMENTED**

FND-05 must assign portfolio authority and dependencies explicitly. Later portfolio/position work must add identity only when its authoritative aggregate boundary is defined.

---

## FND04-EVID-09 — Client trading-account identity is explicit and authority-safe — CLOSED

Verified file:

`src/qore/infrastructure/client_accounts.py`

Verified values include:

- `ClientId`;
- `TradingAccountId`;
- `AccountPolicyReference`;
- `ProductEntitlementReference`;
- `ExecutionRuntimeReference`;
- `ClientTradingAccountBinding`.

`TradingAccountId` explicitly states that it is an opaque QORE identity and not a broker login, provider account number or credential.

`ExecutionRuntimeReference` explicitly states that identity/provenance alone grants no execution authority.

### Analysis

This is an important reusable authority boundary:

```text
TradingAccountId != provider account number
ExecutionRuntimeReference != execution lease/authority
ClientId != TradingAccountId
```

FND-04 must preserve it.

### Classification

**REUSABLE CANONICAL CLIENT-ACCOUNT FOUNDATION FOR ITS SCOPE**

It does not, by itself, define:

- provider account identity;
- provider server identity;
- clearing/custody account identity;
- portfolio aggregation identity;
- collateral pool identity;
- legal owner/beneficial owner identity;
- execution authority.

Those remain explicit neighboring contracts/stages.

---

## FND04-EVID-10 — Proprietary account identity is distinct from client trading-account identity — CLOSED

Verified file:

`src/qore/infrastructure/proprietary_accounts.py`

`ProprietaryAccountId` is an opaque QORE identity for one CEO-controlled account and explicitly not a broker account number/provider credential.

### Analysis

The repository currently has at least two legitimate account identity concepts:

```text
TradingAccountId
ProprietaryAccountId
```

Their common UUID representation does not prove that they should be collapsed.

They represent different bounded contexts and ownership/service semantics. FND-05 must determine whether a future higher-level account aggregate references both through typed relations, not by replacing them with an unqualified `AccountId` solely for type-count reduction.

### Classification

**VERIFIED BOUNDED ACCOUNT IDENTITIES — NO SILENT UNIFICATION**

---

## FND04-EVID-11 — ExternalSourceDescriptor is provenance identity, not provider/server/account/venue identity — CLOSED

Verified file:

`src/qore/infrastructure/ports.py`

Verified values:

- `AdapterId`;
- `SourceId`;
- `PortName`;
- `ExternalSourceDescriptor(adapter_id, source_id, port_name)`.

### Analysis

`ExternalSourceDescriptor` correctly identifies an adapter/source pair and port namespace. It does not encode a canonical provider, broker server, venue, trading account or economic instrument.

Canonical rule:

```text
AdapterId != ProviderId
SourceId != VenueId
ExternalSourceDescriptor != ProviderAccountScope
```

A provider adapter may retain a relation among them, but provenance identity must not become business-domain identity by convention.

### Classification

**REUSABLE CROSS-BOUNDARY PROVENANCE FOUNDATION**

---

## FND04-EVID-12 — UMI-02 already freezes economic/listing/venue authority — CLOSED

Verified file:

`src/qore/infrastructure/universal_instrument_identity.py`

Certified UMI-02 values include:

- `EconomicIdentityId`;
- `ListingIdentityId`;
- `EconomicIdentity`;
- `ListingIdentity`;
- `MarketVenueCode`;
- `ExternalIdentifier`;
- versioned/effective-dated identity mapping lineage.

`ListingIdentity` binds a stable economic identity to a provider-neutral venue/listing scope and display symbol.

`ExternalIdentifier` distinguishes provider-native, venue-native, standard, network-native and legacy material from QORE canonical identity.

### Analysis

FND-04 is not authorized to reopen or duplicate UMI-02.

Authority rule:

```text
Markets / Instruments owns economic identity and listing/venue identity semantics.
Provider/native IDs remain external mapping evidence.
FND-04 adds semantic-dimension constraints around values and neighboring identities;
it does not create a second instrument/venue authority.
```

### Classification

**CERTIFIED FOUNDATION — MUST BE REUSED, NOT REPLACED**

---

## FND04-EVID-13 — PR #298 contains useful provider-native terms but raw provider/server/account scope — CLOSED FOR AUDIT

PR #298 remains OPEN / DRAFT / HOLD and is **not** part of the certified baseline.

Inspected candidate file on PR #298 exact current head at audit time:

`src/qore/infrastructure/provider_instrument_catalog.py`

Useful bounded candidate contracts include:

- `ProviderVolumeTerms(minimum, maximum, step: Decimal, unit: str)`;
- `ProviderTradingSession(start_second, end_second, timezone_name)`;
- `ProviderMarginTier` with explicit bound/leverage/unit/per-side semantics;
- `ProviderMarginTerms` preserving multiple margin/leverage dimensions and tiers;
- `ProviderInstrumentCatalogEntry` preserving provider symbol/id, price precision, minimum price increment, volume terms, sessions, timeframes, margin terms, effective time and evidence.

The candidate also defines:

```python
class ProviderCatalogScope:
    provider_name: str
    server_environment: str
    account_reference: str
```

### Analysis

The candidate demonstrates valuable provider-native evidence that FND-04 should not reinvent.

However:

- provider/server/account scope is raw string material in the candidate;
- the entry still binds legacy `Instrument` rather than the certified UMI-02 identity graph;
- provider volume units remain provider-native facts, not universal economic quantity semantics;
- margin model terms remain provider-native evidence and must not define Core risk semantics.

### Compatibility decision

PR #298 remains HOLD.

Earliest compatibility path after FND-04 certification:

```text
PR #298 CURRENT HEAD
-> rebase from then-certified main
-> replace/bridge legacy Instrument target with UMI-02 mapping semantics where required
-> retain provider-native volume/margin/session evidence as bounded facts
-> map provider/server/account scope to typed provider-boundary identity once frozen
-> independent compatibility review
-> exact-head CI
-> Integration Gate
```

FND-04 does not promote the PR and does not require discarding its useful adapter evidence.

---

## FND04-EVID-14 — Universal notional, tenor, collateral and yield/rate primitives are not proven implemented — CLOSED AS BOUNDED NEGATIVE EVIDENCE

Repository search at the certified baseline produced these bounded observations:

- search for `notional` located architecture material, not a verified production primitive;
- search for `tenor` located architecture material, not a verified production primitive;
- search for `PortfolioId` did not locate an implementation;
- search for `collateral` located architecture obligations but did not establish a production collateral primitive;
- search for `yield` did not establish a universal production yield primitive.

### Claim discipline

These results are **not exhaustive absence proofs**. They mean only:

```text
FND-04 has no verified repository evidence to treat these as existing universal primitives.
```

That is sufficient to prohibit downstream code from assuming they already exist.

### Classification

**NOT PROVEN IMPLEMENTED — DOWNSTREAM EXPLICIT CONTRACTS REQUIRED WHERE APPLICABLE**

---

## FND04-EVID-15 — Canonical timestamp serialization is inconsistent across legacy/bounded contracts — CLOSED

Verified canonical implementations:

- `universal_instrument_identity.py` uses UTC + explicit microseconds for timestamp-bearing logical values;
- `market_observation.py` uses `_canonical_timestamp()` -> `astimezone(UTC).isoformat(timespec="microseconds")`.

Verified direct-offset-preserving implementations include inspected paths such as:

- `order_intent.py`;
- `market_data.py`;
- `futures_adapter_contracts.py`;
- `ports.py` (`ExternalHealth`);
- `account_policy.py`;
- `proprietary_accounts.py`;
- `client_multiaccount_read_model.py`;
- `research_economic_evidence.py`;
- `portfolio/contracts.py`.

These validate timezone awareness but serialize with direct `.isoformat()` in at least the inspected logical-value paths.

### Analysis

For two equal instants:

```python
2026-06-15T12:00:00+00:00
2026-06-15T14:00:00+02:00
```

Python datetime equality can be true while direct `.isoformat()` strings differ.

Therefore direct offset-preserving serialization is unsafe whenever `logical_values()` is intended to represent canonical instant identity for fingerprint/reproducibility purposes.

This is the same defect class corrected in UMI-02, but FND-04 does **not** claim every direct `.isoformat()` is automatically defective: some contracts may intentionally preserve representation or may never use the value as a canonical instant fingerprint. Each remediation requires contract-specific review.

### Classification

**VERIFIED CROSS-CUTTING CANONICALIZATION INCONSISTENCY**

Tracked as `GAP-FND04-TIME-01`.

---

# 4. Semantic collision / gap matrix

| Dimension | Current verified representations | Collision / gap | FND-04 disposition |
|---|---|---|---|
| Execution quantity | `OrderQuantity(Decimal)` | no explicit economic unit/notional | bounded; future typed projection |
| Futures quantity | positive `int` contracts/fills | incompatible with generic fractional-unit assumption | bounded contract count |
| Provider volume | PR #298 `ProviderVolumeTerms(Decimal, unit:str)` | provider-native unit != economic quantity authority | retain as adapter evidence |
| Portfolio allocation | `weight_bps:int` | same numeric scale as unrelated ratios/rates | allocation semantic only |
| Price | legacy/futures `float`, `OrderPrice(Decimal)`, `MarketPrice(Decimal)` | representation and meaning fragmented | no god Price; explicit semantic role |
| Money/value | `MoneyAmount(CurrencyCode, Decimal)` | money amount != market price/valuation | reuse as money-scoped foundation |
| Drawdown | `DrawdownBps` | BPS scale reused elsewhere | keep typed role |
| Profit split | `ProfitSplitBps` | BPS scale reused elsewhere | keep typed role |
| Risk limits | raw `*_bps:int` | scale alone not semantic type | later harden when touched |
| Yield | not proven universal implementation | required by UMI-03/04/10 | explicit later contract |
| Rate | multiple context-specific ratios/terms; no universal financial rate proven | rate kind/methodology/tenor absent | explicit UMI-03/04/08/10 contracts |
| Spread | quote ask-bid Decimal exists | quote spread != credit/yield/rate spread | explicit semantic kind |
| Fixed duration | `Timeframe(seconds)` | cannot model calendar/financial tenor | retain bounded |
| Market period | `MarketTimeframe` with fixed/nonfixed distinction | current code catalog != universal tenor | reuse principle, not global type |
| Financial tenor | not proven implementation | required for rates/curves/contracts | UMI-03/04/05 |
| Effective/recorded/observed time | multiple datetime fields | semantic roles exist but canonical serialization inconsistent | freeze roles + canonical instant rule |
| Economic identity | UMI-02 `EconomicIdentityId` | certified | reuse |
| Listing/venue identity | UMI-02 `ListingIdentityId`, `MarketVenueCode` | certified | reuse |
| Source identity | `AdapterId`, `SourceId`, `ExternalSourceDescriptor` | provenance != provider/venue/account | retain bounded |
| Client trading account | `TradingAccountId` | valid scope, not provider identity or authority | reuse |
| Proprietary account | `ProprietaryAccountId` | separate bounded account concept | do not auto-collapse |
| Provider account/server | PR #298 raw strings; certified Core type not established here | canonical provider-boundary identity gap | UPR-01/FND-05 dependency |
| Portfolio identity | `PortfolioId` not proven | target names are insufficient authority | FND-05/later portfolio |
| Collateral | production primitive not proven | margin/cash != collateral pool by default | FND-05 + risk/account downstream |

---

# 5. Canonical-vs-bounded classification

## 5.1 Certified canonical foundations to preserve

### UMI-02 economic/listing identity

Authority:
Markets / Instruments & Reference Data.

Use:
- economic/reference identity;
- listing identity;
- venue/listing scope;
- provider/venue/standard/network/legacy mapping lineage.

Must not be duplicated by FND-04.

### Client-account identity

`TradingAccountId` is a canonical opaque QORE client trading-account identity for the client service/account foundation.

It must not be treated as provider account number or execution authority.

### External source provenance

`ExternalSourceDescriptor` is canonical provenance for adapter/source/port identity.

It must not be treated as market venue or provider account identity.

## 5.2 Reusable bounded economic value foundations

- `MoneyAmount` — money amount with explicit three-letter currency code;
- `MarketPrice` — exact market-observation price/increment;
- `OrderPrice` — execution intent price;
- `OrderQuantity` — execution intent quantity;
- `MarketTimeframe` — current market-observation period identity;
- `Timeframe(seconds)` — fixed-duration legacy OHLC interval;
- basis-point role types/fields — role-specific ratios/weights/limits;
- PR #298 provider volume/margin/session evidence — provider-bound candidate facts.

None may silently become a global semantic authority solely because it is reusable.

## 5.3 Semantics that require later explicit canonical contracts

When applicable to a family or department, later work must explicitly model:

- quantity dimension/unit and economic identity context;
- notional / face / par amount;
- contract unit/multiplier;
- tick value economic relationship;
- price semantic kind / quote or denomination context;
- valuation amount/result;
- rate semantic kind;
- yield semantic kind;
- spread semantic kind;
- discount factor;
- financial tenor;
- business/calendar period;
- settlement/maturity/business dates;
- provider/server/provider-account identity;
- portfolio aggregate identity;
- collateral pool/asset/valuation relationship.

FND-04 freezes the obligation to distinguish them. It does not prejudge every final class name or force every family to populate every field.

---

# 6. Minimum universal semantic model — architecture decision

## DEC-FND04-01 — No universal scalar god type

QORE shall not introduce a single `FinancialValue`, `Scalar`, `Rate`, `Price`, `Quantity` or `Amount` object whose only semantic differentiator is an ungoverned string.

A universal system requires shared composition rules, not semantic erasure.

Minimum rule:

```text
NUMERIC MAGNITUDE
+
EXPLICIT ECONOMIC SEMANTIC
+
REQUIRED CONTEXT / IDENTITY / PROVENANCE
```

The exact required context varies by dimension.

## DEC-FND04-02 — Quantity is a dimensioned magnitude, not a universal Decimal

Future canonical quantity-bearing contracts must be able to distinguish, when materially relevant:

- shares/units;
- contracts;
- base units;
- quote units;
- face/par amount;
- token units;
- physical units;
- provider lot/volume units;
- notional amounts;
- composition weights.

A provider volume unit may map to an economic quantity dimension, but adapters do not define Core semantic authority.

No rule requires all instruments to use fractional Decimal quantity. Whole contract counts remain valid where family semantics require them.

## DEC-FND04-03 — Notional is not quantity

Notional/face/par is an economic amount basis. It may require currency/reference identity and may coexist with contract/unit quantity.

Examples:

- 5 futures contracts may have a notional derived through multiplier/reference price;
- a bond may carry face amount distinct from clean price;
- a swap may carry notional while having no share-like quantity;
- FX may express base quantity and quote notional relationships.

No generic `price × quantity` derivation is authorized without certified instrument economics and valuation inputs.

## DEC-FND04-04 — Price, money and valuation remain separate dimensions

FND-04 freezes these distinctions:

### Market/execution price

A price is a quotation/transaction dimension attached to an exact instrument/listing/reference context and semantic price kind where required.

### Money amount

A monetary amount is a currency/settlement-value amount such as cash balance, P&L, fee or margin amount.

### Valuation result

A valuation result may be monetary, price-like, rate-like or another typed dimension, but must retain methodology/inputs/source/time/evidence when computed.

Consequently:

```text
MarketPrice != MoneyAmount
OrderPrice != MoneyAmount
Price != ValuationResult
```

## DEC-FND04-05 — Price semantic kind must remain extensible

Later UMI-03..10 contracts must be able to distinguish where applicable:

- trade/last;
- bid/ask/mid;
- clean price;
- dirty price;
- mark;
- index/reference;
- NAV;
- settlement price;
- accrued amount as separate value;
- model-derived price.

FND-04 does not create a global enum now because family semantics and UMI-10 provenance must be designed before the final observation contract.

## DEC-FND04-06 — Rates/yields/spreads require semantic identity beyond scale

A future financial rate-like value must state enough semantic context to reproduce its meaning.

Depending on kind, this may include:

- rate/yield/spread semantic code;
- decimal/rational magnitude and scale;
- benchmark/reference identity;
- tenor;
- day-count;
- compounding;
- effective period;
- source or calculation methodology;
- evidence/provenance.

Not every rate requires every field. Missing applicable semantics must fail closed rather than default silently.

Basis points or percentages are encodings, not semantic identities.

## DEC-FND04-07 — Time ontology has separate categories

QORE future contracts must distinguish at minimum:

### Instant

One timezone-aware point in time. Canonical logical representation of an instant, where determinism is required, is UTC with explicit microsecond precision:

```python
value.astimezone(UTC).isoformat(timespec="microseconds")
```

### Fixed duration

A mathematically fixed elapsed duration, representable in exact seconds/microseconds where appropriate.

### Market timeframe / observation period identity

A provider/market bar period or sampling identity. It may be fixed-duration or calendar/session defined.

### Calendar period

A date/calendar-relative period such as month/quarter/year where elapsed seconds are context-dependent.

### Financial tenor

A contractual/rate-curve maturity horizon such as 1M/3M/5Y whose semantics may depend on calendars/day-count/business conventions.

### Business/contract dates

Settlement date, maturity, issue date, first notice, last trade and payment dates remain explicit roles, not aliases of timeframe/tenor.

### Temporal fact roles

Observed, received, effective, recorded, created, evaluated and reconciled time remain semantically distinct even when all are represented as `datetime`.

## DEC-FND04-08 — Canonical instant serialization is constitutional

For any deterministic `logical_values()` / fingerprint material whose timestamp represents an instant, equal instants must not differ solely due to timezone-offset representation.

New or materially modified contracts must use canonical UTC instant serialization.

Legacy direct `.isoformat()` sites must be reviewed/remediated by scoped work orders before FND-08 final Levels 0–3 audit can certify time determinism broadly.

This decision does not authorize a blind repository-wide search/replace because not every serialized datetime necessarily has identical contract semantics.

## DEC-FND04-09 — Identity domains remain orthogonal

The following are not interchangeable:

```text
EconomicIdentityId
ListingIdentityId
MarketVenueCode
External provider/native identifier
AdapterId
SourceId
TradingAccountId
ProprietaryAccountId
Provider account/server identity
ClientId
Portfolio aggregate identity
Execution runtime reference
Execution authority/lease
```

A future relationship graph may link them, but no UUID/string coincidence grants cross-domain authority.

## DEC-FND04-10 — Account identity does not imply authority or aggregation

An account identity answers **which account**.

It does not answer:

- who may execute now;
- what provider-native account number applies;
- which runtime owns the lease;
- which portfolio aggregates the account;
- which collateral pool secures exposure;
- what commercial entitlement exists.

These require typed relations/evidence under FND-05/FND-06/FND-07 and downstream departments.

## DEC-FND04-11 — Portfolio and collateral require aggregate ownership before type proliferation

FND-04 does not introduce `PortfolioId` or `CollateralPoolId` merely because the terms are required by the roadmap.

FND-05 must first freeze the authoritative department/aggregate ownership and dependency graph. Then later contracts can add identities with clear ownership and lifecycle.

This preserves:

```text
TYPE EXISTS != AUTHORITY EXISTS
```

## DEC-FND04-12 — Provider-native trading terms remain evidence, not Core economic authority

PR #298 demonstrates useful provider-native volume/margin/session terms.

Those values should remain retained provider facts with evidence/effective scope. Core may normalize or map them only after the canonical economic meaning exists.

Example:

```text
provider volume step = 1000 native units
```

is not sufficient evidence to infer:

```text
1000 shares
1000 base-currency units
1 lot
1 contract
```

without explicit mapping semantics.

---

# 7. Duplicate-authority inventory

## 7.1 No duplicate economic identity authority introduced by FND-04

UMI-02 remains the sole certified universal economic/listing identity foundation.

Legacy `Instrument` and `ExecutionInstrument` remain compatibility projections until separately rebased.

## 7.2 Account identities are parallel bounded contexts, not proven duplicates

`TradingAccountId` and `ProprietaryAccountId` are both QORE opaque account identities but have different declared scopes.

FND-04 classifies them as **parallel bounded identities**, not duplicate authorities requiring immediate collapse.

FND-05 must decide aggregate ownership and relation.

## 7.3 Numeric-semantic duplication exists, authority duplication does not automatically follow

Examples:

- `Decimal` in OrderPrice, OrderQuantity, MarketPrice, MoneyAmount;
- integer basis points in portfolio/risk/drawdown/profit split;
- `datetime` across many temporal roles.

The underlying Python type is shared. The semantic authority is not.

The solution is explicit typed semantics, not one globally imported value class for every meaning.

---

# 8. Time / temporal taxonomy and remediation ledger

| Current concept | Verified representation | Universal classification | Action |
|---|---|---|---|
| `Timeframe(seconds)` | positive int seconds | fixed-duration OHLC only | retain legacy bounded |
| `MarketTimeframe` | code + optional fixed_seconds | market observation period identity | reusable; not tenor |
| UMI-02 effective/recorded lifecycle times | aware datetime + canonical UTC logical values | canonical instant roles | certified |
| Market observation times | aware datetime + canonical UTC logical values | canonical observed/open/close instants | reusable |
| Order/futures/account/research/etc. times | aware datetime, many direct `.isoformat()` logical values | semantic roles valid; canonical representation inconsistent | scoped remediation |
| tenor | not proven implemented | financial horizon | UMI-03/04/05 |
| settlement/maturity/business dates | family-specific semantics not frozen here | contract/business date roles | UMI-03/05/07 + calendar department |

### GAP-FND04-TIME-01

**Severity at architecture level: HIGH / cross-cutting reproducibility obligation.**

Claim:
The repository contains both canonical UTC logical timestamp serialization and direct offset-preserving `.isoformat()` serialization across deterministic contracts.

Required downstream closure:

1. inventory each timestamp-bearing deterministic contract before FND-08;
2. classify whether timestamp is instant identity, representation-preserving evidence, or non-fingerprint display;
3. canonicalize equal instants where logical determinism requires it;
4. add timezone-offset-equivalence regression tests;
5. avoid mass edits without contract review.

FND-04 audit may close with this remediation obligation explicitly assigned; FND-08 may not claim full Levels 0–3 temporal determinism while the obligation is unresolved.

---

# 9. Cross-asset adversarial semantic cases

These cases are architecture tests. They demonstrate why current primitives cannot be globally collapsed.

## FND04-CASE-01 — Listed equity

Example semantics:

- economic equity identity;
- listing identity / venue;
- quantity = shares;
- price = currency per share;
- money value = quantity × price only when units/currency and corporate-action-adjusted semantics are valid;
- settlement currency/account cash remains separate.

Pass condition:
No generic `Quantity(Decimal)` is assumed to mean shares without unit/identity context.

## FND04-CASE-02 — Bond

Required distinctions may include:

- economic bond identity;
- face/par amount;
- clean price;
- dirty price;
- accrued interest;
- coupon/rate;
- yield/YTM/YTW;
- day-count/settlement calendar;
- maturity date;
- currency.

Pass condition:
No bond is represented as generic `price × shares`; yield is not encoded as market price.

## FND04-CASE-03 — Futures contract

Required distinctions may include:

- exact native contract identity;
- contract count quantity;
- contract multiplier/unit;
- tick size;
- tick value;
- quote/settlement currency;
- expiry/notice/last trade lifecycle;
- price.

Pass condition:
Integer contract quantity remains valid and is not forced into a fractional-share model; economic value is not inferred without multiplier semantics.

## FND04-CASE-04 — FX spot/forward

Potential distinctions:

- economic pair / base & quote reference identities;
- base quantity;
- quote price;
- settlement currency/date;
- notional;
- pip/tick convention;
- forward points/carry where applicable.

Pass condition:
`OrderQuantity` alone does not establish base-vs-quote notional meaning.

## FND04-CASE-05 — Option

Potential distinctions:

- option contract identity;
- underlying identity;
- contract count;
- multiplier;
- premium price;
- strike;
- expiry;
- right/exercise/settlement;
- implied volatility/Greeks with methodology/provenance.

Pass condition:
Implied volatility is not a `Price`; multiplier is not quantity.

## FND04-CASE-06 — Interest-rate swap

Potential distinctions:

- contract identity;
- notional;
- currency;
- fixed/floating legs;
- rate index/reference;
- tenor/schedules;
- day-count/compounding;
- payment/settlement dates.

Pass condition:
Swap notional is representable without inventing share quantity; tenor is not converted to fixed seconds.

## FND04-CASE-07 — Yield curve node

Potential distinctions:

- curve/reference identity;
- tenor/node identity;
- rate/yield/discount-factor semantic kind;
- value;
- observation/effective time;
- source/methodology/evidence.

Pass condition:
A curve node is not an OHLC `MarketTimeframe` and a discount factor is not a market price.

## FND04-CASE-08 — Crypto perpetual

Potential distinctions:

- economic asset/perpetual contract identity;
- venue/network identity where relevant;
- token/base quantity;
- mark/index/last prices;
- funding rate and funding interval;
- collateral asset;
- account/provider terms.

Pass condition:
Funding rate is not conflated with quote spread; collateral asset is not assumed to equal settlement currency.

## FND04-CASE-09 — Multi-leg / basket

Potential distinctions:

- composite identity;
- ordered component identities;
- component weights/ratios;
- component quantities;
- valuation methodology.

Pass condition:
Portfolio weight BPS is not reused as a generic component quantity without semantics.

## FND04-CASE-10 — Provider volume mapping

Provider publishes:

- minimum 1000;
- maximum 10,000,000;
- step 1000;
- unit = provider-defined native unit.

Pass condition:
Adapter retains this evidence exactly but does not infer shares/contracts/lots/base units until a certified mapping exists.

## FND04-CASE-11 — Same instant, different timezone offsets

Two datetime values represent the same instant under UTC and UTC+02.

Pass condition:
Any canonical instant fingerprint/logical value is identical after UTC normalization.

## FND04-CASE-12 — One account, multiple authorities

A `TradingAccountId` exists while:

- an execution runtime reference exists;
- hosting lease/fencing may decide active authority;
- provider-native account reference exists externally;
- client/commercial entitlement exists separately.

Pass condition:
Account identity alone cannot authorize execution.

## FND04-CASE-13 — Proprietary vs client account identity

A CEO proprietary account and a client trading account may both ultimately point to external accounts.

Pass condition:
Common UUID representation does not allow equality/substitution across bounded identity classes.

## FND04-CASE-14 — Money currency vs economic currency identity

`MoneyAmount(CurrencyCode("USD"), ...)` exists and UMI-02 may also contain a canonical USD currency reference-object identity.

Pass condition:
The code value and economic identity are bridged explicitly where needed; neither silently replaces the other.

---

# 10. Downstream dependency map

## UMI-03 — Fixed income / bonds

Must consume FND-04 distinctions for:

- face/par/notional;
- money/currency;
- clean/dirty price;
- accrued amount;
- coupon/rate/yield;
- day-count;
- maturity/settlement dates;
- curve/reference identity.

UMI-03 must not introduce a private alternate definition of universal quantity/time semantics that conflicts with this audit.

## UMI-04 — Rates / curves / term structures

Must define financial tenor, rate/yield/spread/discount semantics and curve methodology/provenance without reusing `MarketTimeframe` as tenor.

## UMI-05 — Derivatives

Must distinguish contract count, notional, multiplier, underlying/reference, leg structure and price/rate/volatility semantics.

## UMI-06 — Equity/funds/corporate actions

Must bind share/unit quantities and listing identity without making shares the default universal quantity.

## UMI-07 — Commodities / contract lifecycle

Must preserve physical/contract units, multipliers, delivery and lifecycle without genericizing all quantity.

## UMI-08 — Crypto/perpetual/funding/on-chain

Must distinguish token/network/venue identity, funding-rate semantics, collateral and mark/index/last prices.

## UMI-09 — Structured/hybrid/synthetic

Must preserve composition roles/weights/quantities/payoff semantics explicitly.

## UMI-10 — Universal valuation observation

Must build the canonical observation/provenance envelope for typed price/yield/rate/spread/NAV/mark/IV/accrual/cash-flow valuation dimensions.

It should reuse `market_observation.py` design strengths without turning `MarketPrice` into every valuation kind.

## FND-05 — Department registry / dependency graph

Must assign authoritative ownership for:

- portfolio aggregate identity/state;
- account/cash/collateral facts;
- provider/account/server identity;
- market/instrument/reference identity;
- valuation facts;
- temporal/calendar semantics.

## FND-06 — Cross-department contracts

Must preserve dimensioned values and identity refs; commands/events/evidence cannot erase semantic kind or provenance at department boundaries.

## FND-07 — Distributed state

Must define version/freshness/concurrency/reconciliation for account, portfolio, collateral, valuation and provider state without confusing identity with active authority.

## FND-08 — Independent Levels 0–3 audit

Must confirm that all FND-04 obligations needed for foundation determinism/authority are either closed or explicitly assigned to later non-foundation semantics without undermining Levels 0–3.

---

# 11. PR #298 compatibility matrix

| PR #298 candidate concept | FND-04 treatment |
|---|---|
| provider symbol / provider symbol ID | external/native identity evidence; map through UMI-02 |
| `ProviderCatalogScope.provider_name` | bounded provider text; future typed provider identity boundary |
| `server_environment` | bounded server/environment text; not market venue |
| `account_reference` | provider-native account reference; not `TradingAccountId` |
| `ProviderVolumeTerms` | retain exactly as provider-native volume evidence |
| volume `unit: str` | never infer economic quantity dimension without mapping |
| price precision | provider/listing market-spec evidence |
| minimum price increment | provider/listing market-spec evidence; not money value |
| native timeframes | provider capability; not financial tenor |
| trading sessions | provider/market schedule evidence; not universal calendar implementation |
| margin terms / tiers | provider-native account/instrument terms; not Core risk authority |
| effective_at/evidence | retain; required for reproducibility |

PR #298 remains HOLD until post-FND-04 compatibility work is independently reviewed.

---

# 12. Minimum implementation delta decision

## Decision

**NO PRODUCTION CODE IMPLEMENTATION IS JUSTIFIED INSIDE THE FND-04 AUDIT SLICE AT THIS point.**

Reasoning:

1. The master roadmap explicitly defines FND-04 as an **audit**.
2. Existing repository foundations already provide several correct bounded primitives (`MoneyAmount`, `MarketPrice`, `OrderPrice`, `OrderQuantity`, `MarketTimeframe`, UMI-02 identity, source provenance).
3. The largest gaps are semantic ownership/composition questions whose concrete forms belong to UMI-03..10 and FND-05..07.
4. Creating universal `Quantity`, `Rate`, `Tenor`, `PortfolioId` or collateral types before the owning aggregate/family semantics are frozen would convert an audit finding into accidental architecture.
5. UMI-01 established the successful precedent of a documentation-only architecture audit before UMI-02 implementation.
6. PR #298 contains useful provider-native candidate terms that should be reconciled later rather than duplicated now.

Therefore the minimum justified FND-04 repository delta is this architecture evidence artifact only.

### What FND-04 freezes now

- semantic-separation invariants;
- canonical-vs-bounded classification;
- identity authority boundaries;
- time ontology categories;
- canonical instant representation requirement;
- downstream assignments;
- PR #298 compatibility constraints;
- adversarial cases / conformance obligations.

### What FND-04 deliberately does not freeze yet

- final class names for bond/rate/curve/derivative primitives;
- one universal quantity-unit enum;
- one universal rate-kind enum;
- one global price-kind enum before UMI-10;
- portfolio aggregate identity before FND-05;
- collateral aggregate identity before FND-05;
- provider/server/account identity contract before UPR-01/FND-05 mapping;
- operational adapters or provider SDK semantics.

Independent review may reject this minimum-delta decision if repository evidence proves a foundation contract must be implemented before FND-05. In that case, correction occurs on the same branch under the normal QORE correction loop.

---

# 13. Conformance requirements for future implementation slices

Any implementation created from FND-04 obligations must include adversarial tests appropriate to its dimension.

Minimum test classes:

## Quantity

- strict rejection of `bool` where integer is expected;
- finite Decimal where exact decimal magnitude is required;
- unit/dimension mismatch fail-closed;
- whole-contract vs fractional-unit distinction;
- notional not accepted as quantity by type coincidence;
- provider unit cannot masquerade as economic unit.

## Price/value

- MarketPrice cannot be substituted for MoneyAmount;
- money requires explicit currency/reference context;
- clean/dirty/yield semantic distinctions when implemented;
- deterministic decimal canonicalization;
- no float/Decimal silent cross-type equality as semantic proof.

## Rates/yields/spreads

- semantic kind required;
- BPS/percentage encoding cannot change economic meaning;
- tenor/day-count/compounding required when applicable;
- quote spread cannot masquerade as yield/credit spread.

## Time

- timezone awareness;
- UTC canonical instant equivalence across offsets;
- calendar period not coerced to fixed seconds;
- tenor not accepted as market timeframe;
- effective/recorded/observed chronology rules.

## Identity

- economic/listing/provider/account/source identities non-interchangeable;
- identical raw UUID/string content in different identity types does not grant substitution;
- account identity alone cannot create execution authority;
- provider account reference maps explicitly to QORE account identity where a mapping exists.

## Portfolio/collateral

- aggregate identity scope explicit;
- account membership/versioning explicit;
- collateral asset/value provenance explicit;
- no cash-balance == collateral assumption unless certified policy says so.

---

# 14. Compatibility / blast-radius analysis

## Existing production code

This FND-04 candidate changes no production code.

No current public/internal value object is reinterpreted.

No import path changes.

No provider adapter changes.

No database/runtime/network behavior changes.

## UMI-02

No change. UMI-02 remains the certified identity/lifecycle authority.

## UMI-03..14

They gain explicit constraints and do not require immediate code migration from this audit.

## Market data

Legacy `Timeframe`, float snapshots and symbol `Instrument` remain unchanged. Future migration must be additive/compatible.

Market Evidence v2 remains a preferred reusable precision/provenance foundation.

## Execution

`OrderQuantity`, `OrderPrice`, `ExecutionInstrument` remain unchanged. Future rebase must preserve current deterministic authorization/idempotency boundaries.

## Account / portfolio / risk

`TradingAccountId`, `ProprietaryAccountId`, `MoneyAmount`, account policy, portfolio targets and current concentration risk remain unchanged.

FND-05+ must define ownership before wider identity changes.

## Research / replay / fingerprints

No historical evidence is rewritten. Current research behavior that refuses to derive P&L from incomplete economics remains correct.

Temporal canonicalization remediation must preserve historical evidence compatibility and must be reviewed per contract.

## Client / EA / Widget

Current read/execution projections remain unchanged. They must eventually consume certified canonical identities/economic values as projections, never become authorities.

## PR #298

Remains HOLD. Its future rebase is an explicit downstream compatibility task.

---

# 15. Gap ledger

## GAP-FND04-QTY-01 — Universal quantity/notional/unit semantics

**Status:** VERIFIED STRUCTURAL GAP / downstream implementation required.

Evidence:
`OrderQuantity(Decimal)`, Futures integer quantities, portfolio weight BPS and provider-native volume terms represent different dimensions.

Required closure:
UMI family contracts + execution/position/risk mapping must preserve explicit quantity/notional/unit semantics.

## GAP-FND04-VAL-01 — Universal price/value/valuation semantic distinction

**Status:** VERIFIED STRUCTURAL GAP / downstream implementation required.

Evidence:
legacy/futures floats, `MarketPrice`, `OrderPrice`, `MoneyAmount`; no one current type establishes universal price/value/rate/yield semantics.

Required closure:
UMI-03..10, especially UMI-10 valuation-observation boundary.

## GAP-FND04-RATE-01 — Financial rate/yield/spread/tenor semantics

**Status:** VERIFIED STRUCTURAL GAP / downstream implementation required.

Evidence:
basis-point values already encode unrelated meanings; universal yield/tenor production primitives are not proven.

Required closure:
UMI-03 / UMI-04 / UMI-05 / UMI-08 / UMI-10 as applicable.

## GAP-FND04-TIME-01 — Canonical temporal taxonomy and instant serialization consistency

**Status:** VERIFIED CROSS-CUTTING GAP.

Evidence:
certified UMI-02/Market Observation canonical UTC timestamps coexist with direct `.isoformat()` deterministic paths.

Required closure:
scoped remediation and tests before FND-08 can claim broad temporal determinism.

## GAP-FND04-PROVIDER-ID-01 — Typed provider/server/provider-account scope

**Status:** VERIFIED FOUNDATION DEPENDENCY.

Evidence:
UMI-02 owns venue/listing identity; Ports owns adapter/source provenance; client accounts own QORE trading account identity; PR #298 candidate provider scope remains raw text.

Required closure:
UPR-01/FND-05 relationship design before universal provider catalog promotion.

## GAP-FND04-PORTFOLIO-01 — Portfolio aggregate identity/authority

**Status:** NOT PROVEN IMPLEMENTED / ownership unresolved.

Evidence:
Portfolio module has allocation target names/weights; `PortfolioId` was not located in bounded repository search.

Required closure:
FND-05 authority/dependency graph, then portfolio implementation as justified.

## GAP-FND04-COLLATERAL-01 — Collateral aggregate/asset/value semantics

**Status:** NOT PROVEN IMPLEMENTED / ownership unresolved.

Evidence:
current inspected account financial state includes margin-used money; roadmap requires collateral; no production collateral primitive was established by this audit.

Required closure:
FND-05 ownership followed by account/risk/margin implementation.

---

# 16. Explicit non-claims

FND-04 does **not** claim:

- all repository quantity/price/rate/time/account symbols were exhaustively enumerated;
- every direct `.isoformat()` site is defective;
- Decimal must replace every float in QORE;
- `MoneyAmount` is invalid;
- `CurrencyCode` is invalid for its current scope;
- `TradingAccountId` and `ProprietaryAccountId` should be merged;
- a portfolio/collateral implementation should be added before ownership is frozen;
- PR #298 is ready for merge;
- bonds/rates/derivatives/crypto are implemented by this audit;
- provider-native margin/volume semantics are canonical Core risk/economic semantics;
- a generic formula can derive economic value from price and quantity;
- operational support follows from architectural representability.

---

# 17. Required independent review questions

The independent reviewer must answer at minimum:

1. Is the evidence ledger faithful to exact baseline `89705ed8...`?
2. Does the audit correctly distinguish numeric representation from economic semantics?
3. Is `MoneyAmount` classified as reusable without over-promoting its `CurrencyCode` authority?
4. Are `OrderQuantity`, Futures integer quantity and provider volume correctly kept as bounded semantics?
5. Does the audit prevent `price × quantity` from becoming an unsafe universal valuation rule?
6. Does the rate/yield/spread decision avoid both under-typing and a universal scalar god type?
7. Does the time ontology correctly distinguish instant/duration/timeframe/calendar period/tenor/business dates?
8. Is GAP-FND04-TIME-01 correctly characterized without overclaiming every `.isoformat()` site as defective?
9. Are UMI-02 economic/listing/venue authority boundaries preserved?
10. Are AdapterId/SourceId correctly prevented from becoming provider/venue/account identities?
11. Are TradingAccountId and ProprietaryAccountId correctly treated as bounded identities instead of automatically collapsed?
12. Is absence/not-proven language for notional/tenor/PortfolioId/collateral/yield appropriately disciplined?
13. Is the PR #298 compatibility plan conservative and sufficient?
14. Is the documentation-only minimum delta justified by the FND-04 audit scope?
15. Does any missing foundation primitive have to be implemented **before** FND-05, contrary to this candidate decision?
16. Are the cross-asset adversarial cases sufficient to prevent equity/FX/bar-centric leakage?
17. Are downstream assignments to UMI-03..10 and FND-05..08 coherent?
18. Does this artifact create any parallel authority or contradict the certified UMI-02 model?

For every finding, the reviewer must provide:

```text
CLAIM
EVIDENCE
ANALYSIS
SEVERITY
REQUIRED CORRECTION
```

Allowed final verdicts:

1. `READY FOR STAGE-04 / FND-04 CERTIFICATION — VERIFIED`
2. `COHERENT BUT REQUIRES CORRECTIONS BEFORE CERTIFICATION`
3. `REJECTED FOR ARCHITECTURE CORRECTION`
4. `NOT VERIFIED`

---

# 18. FND-04 closure criteria

FND-04 is not CLOSED merely because this document exists.

Required sequence:

```text
EXACT BASELINE VERIFIED
-> REPOSITORY AUDIT
-> EVIDENCE LEDGER
-> COLLISION / GAP ANALYSIS
-> MINIMUM ARCHITECTURE DECISION
-> AUDIT ARTIFACT
-> PR
-> EXACT-HEAD CI
-> DIFF / BLAST-RADIUS AUDIT
-> INDEPENDENT ADVERSARIAL REVIEW
-> CORRECTION LOOP IF REQUIRED
-> INDEPENDENT RE-REVIEW
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> MERGE(expected_head_sha)
-> VERIFY MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> FND-04 CLOSED
```

Only then may Program A advance to FND-05.

---

# 19. Final architecture freeze candidate

If independently certified, FND-04 freezes these conclusions:

```text
1. QORE UNIVERSALITY REQUIRES SEMANTIC DIMENSIONS, NOT A GOD SCALAR.
2. NUMERIC STORAGE TYPE DOES NOT DEFINE ECONOMIC MEANING.
3. QUANTITY, NOTIONAL, PRICE, MONEY, VALUE, RATE, YIELD, SPREAD AND WEIGHT REMAIN DISTINCT.
4. PRICE × QUANTITY IS NOT A UNIVERSAL ECONOMIC-VALUE RULE.
5. UMI-02 REMAINS THE ECONOMIC/LISTING/VENUE IDENTITY AUTHORITY.
6. PROVIDER/SOURCE/ACCOUNT/RUNTIME IDENTITIES REMAIN ORTHOGONAL TO INSTRUMENT IDENTITY.
7. ACCOUNT IDENTITY DOES NOT GRANT EXECUTION AUTHORITY OR PORTFOLIO OWNERSHIP.
8. INSTANT, DURATION, MARKET TIMEFRAME, CALENDAR PERIOD AND FINANCIAL TENOR ARE DISTINCT.
9. CANONICAL INSTANT FINGERPRINTS MUST NORMALIZE EQUAL INSTANTS DETERMINISTICALLY.
10. CURRENT BOUNDED PRIMITIVES ARE REUSED WHERE VALID; THEY ARE NOT SILENTLY PROMOTED.
11. FAMILY ECONOMICS ARE IMPLEMENTED IN UMI-03..10 ON THIS SEMANTIC FOUNDATION.
12. PORTFOLIO/COLLATERAL/PROVIDER-ACCOUNT OWNERSHIP IS FROZEN BY FND-05+ BEFORE TYPE PROLIFERATION.
13. PR #298 REMAINS HOLD UNTIL REBASED AGAINST UMI-02 + FND-04 + TYPED PROVIDER SCOPE.
14. FND-04 ITSELF REQUIRES NO PRODUCTION CODE UNLESS INDEPENDENT REVIEW PROVES A FOUNDATION BLOCKER.
```

This preserves the central QORE principle:

```text
QORE CORE IS UNIVERSAL BY VERIFIED SEMANTICS AND GOVERNED AUTHORITY,
NOT BY USING THE SAME PYTHON TYPE EVERYWHERE.
```
