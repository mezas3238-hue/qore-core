# QORE-UMI-11 — Universal Market Topology / Venue Model

Status: **PROGRAM D / UMI-11 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**  
Tracking: #357  
Master roadmap: #303  
Universal Markets / Instruments: #301  
Certified starting baseline: `4fcb1cc050c8eeb3f264ef2e28f19d0e49706866`  
Predecessor: UMI-10 / #355 / PR #356 — CERTIFIED/CLOSED

## 1. Mission

UMI-11 adds the minimum provider-neutral immutable market-topology semantics required to
represent materially different ways financial markets organize interaction without turning
reference semantics into market data, provider capability, time/session authority, routing or
execution.

The roadmap requires QORE to distinguish structures including centralized order books,
dealer/RFQ/OTC, quote-driven markets, auctions, dark/alternative venues, bilateral markets,
AMM/on-chain pools, primary/secondary stages and fragmented/multi-venue instruments.

Canonical inequalities:

```text
MARKET STRUCTURE != TRADING METHODOLOGY
VENUE IDENTITY != MARKET TOPOLOGY
VENUE != PROVIDER != ADAPTER != SOURCE
PROVIDER CAPABILITY != MARKET TOPOLOGY
TOPOLOGY != LIVE MARKET STATE
TOPOLOGY != CURRENT SESSION / PHASE
TOPOLOGY != ROUTING / EXECUTION
CEX != CLOB
ON-CHAIN != AMM
MULTI-VENUE != BEST-VENUE ROUTER
AUCTION TOPOLOGY != AUCTION SCHEDULE / CURRENT PHASE
RFQ TOPOLOGY != CURRENT RFQ QUOTE
AMM TOPOLOGY != CURRENT POOL RESERVES
EVIDENCE REF != EVIDENCE CONTENT / TRUTH
TYPE EXISTS != OPERATIONAL SUPPORT
```

## 2. Exact-baseline audit

The certified baseline was re-read before implementation.

### 2.1 UMI-02 remains identity authority

`universal_instrument_identity.py` already owns:

- `EconomicIdentityId`;
- `ListingIdentityId`;
- `MarketVenueCode`;
- `ListingIdentity`;
- `CanonicalIdentityRef`;
- external identity and lifecycle material.

`MarketVenueCode` is a provider-neutral venue/listing scope code.
`ListingIdentity` is one exact venue/listing representation of one economic identity with its
own validity interval and evidence.

UMI-11 therefore adds no second economic identity, listing identity or venue code.

```text
MarketVenueCode EXISTS
!=
MARKET TOPOLOGY EXISTS
```

### 2.2 D05 remains live market-evidence authority

`market_observation.py` owns exact retained quote/OHLC/specification evidence such as:

- `QualifiedQuoteTickObservation`;
- `QualifiedOhlcBarObservation`;
- `InstrumentMarketSpecification`.

Those are observations of market facts. UMI-11 does not duplicate them and does not add live
order-book levels, trades, quotes, RFQs, current auction state or AMM reserves.

### 2.3 UMI-08 explicitly reserves topology

Certified UMI-08 states:

```text
CEX / AMM / OTC / ON-CHAIN TOPOLOGY -> UMI-11
```

and explicitly refuses to decide CEX vs AMM vs OTC topology itself.

UMI-08 network qualification and NETWORK_NATIVE external identity remain UMI-02/UMI-08
material. UMI-11's `ON_CHAIN` context does not create a network identity, wallet, chain RPC,
transaction or custody fact.

### 2.4 D06 remains temporal/session authority

An effective-dated topology profile says only that retained evidence qualifies the structure
over that interval. It does not answer whether a market is open now, which auction phase is
active, whether an RFQ window remains open or whether an AMM is currently usable.

```text
EFFECTIVE PROFILE != CURRENT SESSION
```

### 2.5 D10/D18 remain routing and execution authority

Existing order/execution contracts own order intent, admission, submission and execution
lifecycle. UMI-11 contains no route, match, submit, execute, RFQ-request, swap or best-venue
method.

### 2.6 Gap conclusion

Targeted source search did not establish a canonical implemented owner equivalent to:

- `MarketTopology`;
- `MarketStructure`;
- `MarketMechanism`;
- `VenueType`;
- `OrderBook`;
- `LiquidityPool`.

RFQ/AMM/Auction references were documentation or bounded family semantics rather than a
universal market-topology owner.

```text
VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-11 CONTRACT DELTA REQUIRED
```

## 3. Authority map

| Material | Owner | UMI-11 treatment |
|---|---|---|
| Economic identity | UMI-02 / D04 | reuse exact typed identity |
| Listing identity | UMI-02 / D04 | retain exact `ListingIdentity` when listing-scoped |
| Venue code | UMI-02 / D04 | reuse exact `MarketVenueCode` |
| Static topology qualification | UMI-11 / D04 | owner of this bounded semantic layer |
| Provider capability | D03 / UPR-11 | no capability inference |
| Live quote/OHLC/trade/depth/RFQ/pool evidence | D05 | no live state |
| Calendar/session/current phase | D06 | no resolver/scheduler |
| Valuation observation | D07 / UMI-10 | no valuation |
| Order/routing/execution | D10 / D18 | no execution authority |
| Position/settlement mutation | D11 | no mutation |

## 4. Subject scopes

One scope shape cannot safely represent all market structures.

### 4.1 Economic scope

`EconomicMarketTopologyScope(EconomicIdentityId)` means the structural qualification applies
to the economic object without asserting a venue or listing.

This is valid for bilateral/OTC semantics where a more specific venue is not being claimed.

### 4.2 Listing scope

`ListingMarketTopologyScope(ListingIdentity)` retains the exact UMI-02 listing object.

The topology profile derives economic identity and venue from that object rather than copying
caller-supplied IDs.

The topology effective interval must be contained inside the exact listing validity interval.
This is local consistency validation only; it is not a current-listing resolver.

### 4.3 Venue scope

`VenueMarketTopologyScope(MarketVenueCode)` describes venue-wide topology without asserting
that any specific economic instrument is available there.

```text
VENUE-WIDE TOPOLOGY != INSTRUMENT SUPPORT
```

### 4.4 Economic + venue scope without listing

The initial three-scope design was corrected before code because it could not represent an
OTC instrument at one venue/dealer network without fabricating a `ListingIdentity`.

`EconomicVenueMarketTopologyScope(EconomicIdentityId, MarketVenueCode)` closes that gap.

It deliberately has no:

- `ListingIdentityId`;
- display symbol;
- listing validity;
- claim that a listing exists.

```text
ECONOMIC + VENUE SCOPE != ListingIdentity
OTC / BILATERAL != FAKE LISTING
```

## 5. Interaction mechanism

`MarketInteractionMechanism` is a closed minimum structural vocabulary:

- `CENTRAL_LIMIT_ORDER_BOOK`;
- `DEALER_RFQ`;
- `QUOTE_DRIVEN`;
- `AUCTION`;
- `BILATERAL`;
- `AUTOMATED_MARKET_MAKER`.

A profile contains a non-empty tuple of mechanisms.

Multiple mechanisms may coexist. This is necessary for real hybrid market structures such as
order-book plus auction phases or dealer RFQ plus bilateral negotiation.

Duplicates fail closed. Caller ordering is canonicalized by enum value.

```text
ONE MARKET PROFILE != EXACTLY ONE MECHANISM
```

The mechanism vocabulary contains no current prices, quote IDs, order IDs, reserves, depth,
participants or phase state.

## 6. Market stage

`MarketStage` distinguishes:

- `PRIMARY`;
- `SECONDARY`.

A profile may retain zero, one or both stage qualifications. An empty tuple means this stage
dimension is not asserted by the profile; it does not mean UNKNOWN has been magically
resolved.

Stage values are structural classification only.

```text
PRIMARY != PRIMARY LISTING IDENTITY
SECONDARY != CURRENT SECONDARY-MARKET SESSION
```

## 7. Transparency

`MarketTransparency` optionally qualifies:

- `LIT`;
- `DARK`;
- `MIXED`.

This is intentionally separate from mechanism.

A dark profile does not claim that current liquidity exists, that D05 has full visibility, or
that execution access is available.

```text
DARK STRUCTURAL QUALIFICATION != CURRENT HIDDEN LIQUIDITY OBSERVED
```

## 8. Infrastructure context

`MarketInfrastructureContext` optionally distinguishes:

- `CENTRALIZED`;
- `ON_CHAIN`;
- `HYBRID`.

This dimension is separate from interaction mechanism.

The candidate deliberately permits combinations such as:

```text
CENTRALIZED + AUTOMATED_MARKET_MAKER
ON_CHAIN + CENTRAL_LIMIT_ORDER_BOOK
```

so that implementation cannot silently encode:

```text
CEX == CLOB
ON_CHAIN == AMM
```

`ON_CHAIN` is topology context only. It is not network identity, transaction finality, wallet,
custody or operational support.

## 9. Effective interval

`MarketTopologyEffectiveInterval` retains explicit timezone-aware instants.

Deterministic logical material canonicalizes them to UTC with microsecond precision.
Equivalent instants supplied with different offsets therefore serialize identically.

An optional open end is allowed.

For listing scope, an open-ended topology is rejected if the retained listing itself has a
finite `valid_until`.

No wall clock is read.

```text
EFFECTIVE-DATED PROFILE != CURRENT PROFILE SELECTED
```

## 10. Topology profile

`MarketTopologyProfile` contains only:

- explicit `MarketTopologyProfileId`;
- exact typed subject;
- one-or-more structural mechanisms;
- exact effective interval;
- opaque topology evidence reference;
- optional stage set;
- optional transparency qualification;
- optional infrastructure context.

It exposes derived economic identity / venue where the subject proves them.

It does not carry duplicated economic/venue fields for `ListingMarketTopologyScope`.

All collections are immutable tuples and canonicalized deterministically.

## 11. Fragmented / multi-venue topology

`FragmentedMarketTopology` is the minimum static structure proving that one economic identity
has topology across multiple venues during one common interval.

It requires:

- explicit fragmentation ID;
- exact `EconomicIdentityId`;
- at least two exact `MarketTopologyProfile` components;
- unique profile IDs;
- every component proves the exact same economic identity;
- every component is venue-qualified;
- at least two distinct `MarketVenueCode`s;
- every component profile covers the declared fragmentation interval;
- opaque evidence reference;
- deterministic venue/profile ordering.

Economic-only profiles and venue-wide-only profiles are insufficient for this aggregate
because they cannot prove both sides of the economic+venue claim.

A component may be:

- exact `ListingMarketTopologyScope`; or
- `EconomicVenueMarketTopologyScope` where no listing is asserted.

This allows listed and OTC-style fragmented markets without false identity.

```text
MULTI-VENUE FACT
!=
BEST VENUE
!=
ROUTE POLICY
!=
SMART ORDER ROUTING
```

No ranking, weighting, cost, liquidity, slippage or route-selection field exists.

## 12. Determinism

All UMI-11 dataclasses use `frozen=True, slots=True`.

Deterministic material requires:

- explicit UUIDs; no implicit generation;
- inherited typed UMI-02 identities;
- canonical UTC/microsecond instant representation;
- deterministic mechanism ordering;
- deterministic stage ordering;
- deterministic fragmentation profile ordering;
- deterministic venue ordering;
- no mutable `dict`/`list` state in canonical fields;
- no arbitrary `Any`/callback/formula surface.

No network, provider SDK, retry, sleep, scheduler, thread, wall-clock source, randomness,
`eval` or `exec` exists.

## 13. PRE-CHK disposition targets

The candidate is designed to falsify all work-order PRE-CHK items:

- second venue/listing identity graph;
- venue/topology collapse;
- provider capability/topology collapse;
- live order-book/topology collapse;
- D05 live-state authority creep;
- D10 routing/matching/execution authority creep;
- D06 session/current-phase authority creep;
- CEX/CLOB collapse;
- on-chain/AMM collapse;
- fake OTC listing;
- RFQ/current-quote collapse;
- AMM/live-reserve collapse;
- auction/current-phase collapse;
- dark/current-liquidity claim;
- primary/secondary/listing collapse;
- one-mechanism flattening;
- multi-venue/router collapse;
- contract/support claim;
- mutable arbitrary metadata;
- provider/network/scheduler leakage;
- effective-date/currentness collapse;
- evidence-ref/truth collapse;
- nondeterministic ordering;
- duplicated listing economic/venue binding;
- fragmentation/router-policy collapse.

## 14. Adversarial conformance specimens

Tests intentionally prove:

1. economic, listing, venue and economic+venue scopes remain distinct;
2. economic+venue scope creates no fake listing fields;
3. listing scope derives exact UMI-02 economic+venue material;
4. listing-bound topology cannot extend outside listing validity;
5. CLOB + AUCTION hybrid profile is valid and order independent;
6. PRIMARY + SECONDARY stage tuple is canonical;
7. CENTRALIZED + AMM is valid;
8. ON_CHAIN + CLOB is valid;
9. OTC economic+venue RFQ/BILATERAL is valid without listing;
10. bilateral economic-only scope is valid without venue claim;
11. equivalent-offset instants produce identical logical material;
12. fragmentation across listing + OTC/economic-venue components is valid;
13. fragmentation input order does not change logical material;
14. wrong economic identity fails;
15. venue-unqualified component fails;
16. one-venue pseudo-fragmentation fails;
17. non-overlapping/common-invalid effective interval fails;
18. duplicate/wrong/mutable mechanism/stage material fails;
19. arbitrary subject/type laundering fails;
20. routing/matching/live-state method surfaces are absent;
21. provider I/O, scheduler and nondeterministic source patterns are absent.

## 15. Compatibility / blast radius

Implementation is additive.

It imports only:

- UMI-02 identity types;
- QORE infrastructure error base;
- standard-library deterministic value primitives.

It does not require changes to certified UMI-02, D05, D06, UMI-08, UMI-10, D10 or D11
owners.

Consumers may later bind topology profiles through explicit owner contracts; this stage does
not silently rewrite current symbol/provider/execution surfaces.

## 16. Security

Topology IDs/evidence refs are UUID wrappers.

Venue/economic/listing semantics reuse UMI-02 validated types rather than introducing raw
public credential-bearing strings.

No secret store, credentials, provider account, auth token or network payload enters the
contract.

```text
EVIDENCE REF != EVIDENCE CONTENT
IDENTIFIER != CREDENTIAL
TOPOLOGY PROFILE != PROVIDER ACCESS AUTHORITY
```

## 17. Explicit non-claims

UMI-11 does not establish:

- current order-book content;
- RFQ quotes;
- auction phase;
- AMM reserve state;
- trade/tick/depth evidence;
- current liquidity;
- provider capability;
- market access;
- best execution;
- smart order routing;
- matching;
- execution;
- provider/exchange/venue support;
- network/wallet/custody/transaction support;
- production readiness;
- real-capital authority;
- universal market readiness.

`TYPE EXISTS != OPERATIONAL SUPPORT`.

## 18. Carry-forwards

Unchanged:

- #333 / `GAP-FND04-TIME-01` — OPEN/HIGH;
- #332 / `GAP-FND07-RES-01` — OPEN/HIGH;
- #350 D07 valuation producer — OPEN/preparatory;
- `GAP-EXEC` — OPEN/HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN/HIGH;
- `GAP-LIN-001` — OPEN/HIGH;
- UMI-02 cross-revision overlap/precedence — OPEN;
- #334 productive in-flight side-effect containment — OPEN;
- #146 OANDA Practice external blocker — OPEN;
- #286 methodology/operator evidence — OPEN;
- PR #298 — HOLD.

## 19. Gate

```text
CERTIFIED BASELINE
-> EXACT REPOSITORY AUDIT
-> VERIFIED STRUCTURAL GAP
-> WORK ORDER #357
-> MINIMUM ARCHITECTURE
-> IMPLEMENTATION
-> ADVERSARIAL TESTS
-> DIFF / BLAST-RADIUS AUDIT
-> DRAFT PR
-> EXACT-HEAD QORE CI + COVERAGE AUDIT
-> HEAD FREEZE
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE
-> CORRECTION LOOP IF REQUIRED
-> MERGE(expected_head_sha)
-> VERIFY ACTUAL MERGE / PARENTS / TREE / SIGNATURE
-> VERIFY LIVE MAIN 0/0
-> BASELINE FREEZE
-> UMI-11 CLOSED
```

No self-certification. CI green alone is not approval. A document/type is not operational
support. Any candidate mutation after review freeze invalidates the review target.
