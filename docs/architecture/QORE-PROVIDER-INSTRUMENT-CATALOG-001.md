# QORE-PROVIDER-INSTRUMENT-CATALOG-001 — Dynamic Provider Instrument Catalog

## Status

**IMPLEMENTATION CANDIDATE — INDEPENDENT REVIEW REQUIRED**

Tracking: Issue #296.

Exact implementation baseline:

`fad2ab34a286a297241d779f38b4d9fd87580ce4`

The baseline is the verified post-PR-#297 `main`, not the older SHA originally written into Issue #296.

## Purpose

QORE must learn account-available instruments and their effective provider terms from explicit provider evidence. It must not maintain a guessed symbol universe or blindly probe symbol strings.

Canonical rule:

`PROVIDER = AUTHORITY FOR INSTRUMENT AVAILABILITY AND EFFECTIVE TRADING TERMS`

`QORE NORMALIZES; QORE DOES NOT INVENT`

The catalog is account/server scoped. It does not claim a broker-global product universe from account-qualified evidence.

## Provider-neutral catalog boundary

`ProviderInstrumentCatalog` retains one deterministic catalog with:

- explicit provider/server/account scope;
- explicit external source descriptor;
- explicit provider evidence time;
- canonical deterministic entries.

Each `ProviderInstrumentCatalogEntry` keeps provider identity separate from QORE identity:

- canonical `Instrument`;
- exact provider symbol text;
- provider-native symbol ID when available;
- asset class/category evidence when available;
- price precision when available;
- minimum price increment only when independently evidenced;
- provider-native volume terms with explicit retained unit;
- normalized trading status;
- provider trading-session evidence without attaching trading methodology policy;
- provider-native timeframe capability when verified;
- margin terms without collapsing all models to one leverage scalar;
- sanitized provider-native fields that do not yet have a canonical equivalent;
- explicit effective timestamp and evidence reference.

Duplicate provider IDs, duplicate provider symbols and ambiguous many-to-one canonical instrument mappings fail closed.

## Precision is not tick size

Provider price digits/precision and minimum valid price increment are separate facts.

For cTrader, this slice retains `digits` as price precision but does **not** infer minimum tick size from `10^-digits` because the verified Open API symbol evidence used by this implementation does not independently expose a minimum tick-increment field.

Therefore the cTrader normalized entry uses:

`minimum_price_increment = None`

until provider evidence proves a concrete increment.

`DIGITS != PROVEN TICK SIZE`

## Margin/leverage semantics

The provider-neutral contract can retain, independently:

- account leverage;
- instrument margin rate;
- initial margin rate;
- maintenance margin rate;
- buy/sell margin modifiers;
- dynamic margin/leverage tiers;
- provider-native margin evidence fields and references.

No provider is forced into a single leverage scalar.

### cTrader normalization

The cTrader adapter retains account-level margin evidence separately from symbol dynamic leverage.

For the verified cTrader Open API model used by this slice:

- account `leverageInCents` is retained and normalized by exact division by 100 because that field explicitly carries cent-based encoding;
- dynamic leverage tier `volume` is retained as the provider-documented maximum USD volume **in cents**, per side;
- dynamic leverage tier `leverage` is retained as the provider-documented applied leverage value without inventing a hundredths conversion;
- tiers retain per-side semantics;
- the last dynamic tier is retained as applying above its stated bound;
- account-margin evidence, dynamic-leverage evidence, `leverageId`, total-margin calculation type, volume unit and native encoding names remain in sanitized native fields.

`DOCUMENTED SCALE MAY BE NORMALIZED; UNDOCUMENTED SCALE MUST BE RETAINED, NOT INVENTED.`

This does not authorize risk sizing. End-to-end margin semantics must be separately verified before risk sizing can rely on them.

## cTrader discovery path

The cTrader adapter models the official account-scoped discovery sequence explicitly:

1. read the account symbol list;
2. retain each provider symbol ID and exact symbol name;
3. retain a typed evidence reference for symbol-list account membership;
4. request full symbol/reference data by those returned IDs;
5. require exact membership agreement between list and full reference data;
6. join related category/asset-class evidence by explicit provider IDs when supplied;
7. resolve dynamic leverage only for leverage IDs actually referenced by returned symbols;
8. retain account-margin and native-period capability evidence explicitly;
9. normalize only after account/source binding is verified.

No static `EURUSD`, `GBPUSD`, or similar list is provider discovery truth.

Canonical QORE mapping is a separate explicit boundary. `CTraderExactSymbolMapper` may reuse provider text only when it already satisfies the canonical QORE instrument contract. Otherwise an explicit mapper is required; normalization does not guess aliases.

## Native timeframe identity versus capability

cTrader Open API defines native trendbar period identities corresponding to:

`M1 M2 M3 M4 M5 M10 M15 M30 H1 H4 H12 D1 W1 MN1`

The existence of a provider enum is not runtime capability evidence.

`ENUM EXISTS != RUNTIME CAPABILITY`

`CTraderProviderCatalogClientBoundary.native_period_capability` is an explicit injected `CTraderNativePeriodCapability` carrying the verified periods, observation timestamp and evidence reference for the concrete provider/account runtime. Only those periods are placed into each catalog entry as native capability, and the capability evidence reference is retained in provider-native fields.

`CTraderNativeMarketDataFlow` checks catalog capability **before** calling the provider client. Unsupported periods fail closed with no provider read.

## Calendar timeframe semantics

QORE's canonical `MarketTimeframe` intentionally has no fixed-second duration for:

- `D1`;
- `W1`;
- `MN1`.

The native cTrader path preserves that identity. It does not convert a month into 30 days or a calendar day into a universal fixed second count.

`PERIOD IDENTITY != FIXED DURATION`

The existing fixed-seconds `OhlcRequest` and existing cTrader M5 adapter remain unchanged. The new native path is additive and uses an explicit provider query window plus provider-native trendbar evidence.

For calendar bars the slice does not fabricate `closed_at` from an invented duration. A later qualified canonical observation may derive/retain interval closure only from an exact verified provider/time-calendar contract.

## Trading status and sessions

Provider trading availability is evidence, not strategy policy.

Normalized states distinguish:

- tradable;
- close-only;
- unavailable;
- unknown.

Only `tradable` permits new exposure at this catalog layer.

Provider weekly sessions are retained as provider-qualified schedule evidence. They do not define universal market close, forced liquidation, no-overnight, reset, or Trader Midpoints policy.

`PROVIDER AVAILABILITY != TRADING METHODOLOGY`

## Determinism and hygiene

Deterministic value contracts use supplied evidence only.

Forbidden inside those contracts:

- implicit current wall clock;
- `uuid4()`;
- random identity;
- hidden network calls;
- hidden retry/sleep/scheduler/thread behavior;
- provider credentials or secret values in logical values, errors or evidence references.

Provider transport/authentication remain injected outside deterministic normalization.

## Compatibility

Unchanged by this slice unless a later reviewed correction proves necessary:

- Core provider-neutral boundary;
- Market Evidence v2 contracts;
- mixed market-event replay and arrival provenance;
- Schedule A and Schedule B semantics;
- historical dataset/fingerprint contracts;
- existing cTrader DEMO M5 adapter and its current behavior;
- OANDA Practice paths;
- execution paths;
- Trader Midpoints methodology.

The new native cTrader read path coexists additively with legacy M5 behavior.

## Non-claims

This slice does not prove or authorize:

- a broker-global product universe;
- instruments absent from account/provider evidence;
- a tick increment inferred only from digits;
- one universal leverage scalar;
- production trading activation;
- risk sizing based on unverified margin semantics;
- synthetic calendar bar durations;
- provider availability as trading methodology;
- calibration, OOS, expected performance or profitability.

Promotion requires exact-head Quality Gate, independent adversarial review, Integration Gate, exact-head merge and post-merge baseline verification.
