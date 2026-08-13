# QORE-UMI-02-UNIVERSAL-INSTRUMENT-IDENTITY-LIFECYCLE-001

## Status

**STAGE-03 / UMI-02 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #301  
Master roadmap: #303  
Preceding stage: STAGE-02 / UMI-01 — CLOSED  
Certified starting baseline: `ab69f0f2f43c73e2b0d2c4c4c4ca480b1b8f68f7`

This artifact defines the minimum provider-neutral identity/lifecycle graph required before QORE can safely add family-specific universal economics. It is additive to legacy boundaries and does not silently reinterpret current symbol contracts.

## Governing invariants

```text
QORE CORE IS UNIVERSAL AND NON-SELECTIVE
SYMBOL TEXT != UNIVERSAL INSTRUMENT IDENTITY
ECONOMIC IDENTITY != LISTING / VENUE IDENTITY
TRADABLE INSTRUMENT IDENTITY != REFERENCE-OBJECT IDENTITY
PROVIDER-NATIVE ID != ECONOMIC INSTRUMENT IDENTITY
STANDARD IDENTIFIER != PROVIDER-NATIVE RUNTIME IDENTIFIER
EXTERNAL IDENTIFIER != QORE CANONICAL IDENTITY
ASSET FAMILY != INSTRUMENT IDENTITY
DISPLAY SYMBOL != CANONICAL IDENTITY
CONTINUOUS REFERENCE != NATIVE CONTRACT
COMPOSITE / SYNTHETIC != PRIMITIVE INSTRUMENT
LIFECYCLE != UNIVERSAL EXPIRY FIELD
CURRENT MAPPING != HISTORICAL IDENTITY INTERPRETATION
MAPPING DIGEST != RETAINED VERSIONED MAPPING EVIDENCE
IDENTITY FOUNDATION != FAMILY-SPECIFIC ECONOMIC TERMS
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO REPRODUCIBILITY -> NO PROMOTION
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

## Scope and authority

Under the certified departmental sovereignty freeze, Markets / Instruments owns canonical economic identity/reference facts. Provider/platform adapters retain provider-native IDs and map them through governed boundaries. Market Data, Execution, Position, Risk, Research, Valuation, Client EA and presentation surfaces consume identity; none becomes a parallel identity authority.

UMI-02 freezes the identity graph and lifecycle foundation only. It does not implement provider discovery, operational registries, family valuation, risk models, execution economics or productive support.

---

# 1. Repository starting evidence

The certified baseline still contains multiple valid but bounded identity surfaces:

- `market_data.Instrument(symbol: str)` — legacy provider-neutral market symbol;
- `order_intent.ExecutionInstrument(value: str)` — execution-scope symbol;
- provider/source identity through `ExternalSourceDescriptor`;
- provider-native symbol/contract IDs in adapter contracts;
- presentation-specific symbols in executive/client read models;
- historical/research evidence that serializes legacy symbol material.

UMI-01 certified that these bounded contracts are reusable but insufficient as universal economic identity. UMI-02 therefore adds a canonical graph without changing the meaning of those legacy types.

```text
ADDITIVE CANONICAL GRAPH
!=
SILENT LEGACY TYPE REINTERPRETATION
```

---

# 2. Canonical identity graph

## 2.1 Economic identity

`EconomicIdentityId` is the stable QORE identity for one economic instrument or one reference object. It is independent of display symbol, provider ID and listing.

`EconomicIdentity` carries only identity-foundation material:

- stable identity ID;
- `EconomicIdentityKind`;
- extensible family classification;
- construction kind;
- retained evidence reference.

It does not carry one universal price, quantity, expiry, strike, coupon or settlement field.

## 2.2 Tradable instrument vs reference object

`EconomicIdentityKind` distinguishes:

- `TRADABLE_INSTRUMENT`;
- `REFERENCE_OBJECT`.

Reference objects include concepts such as benchmark rates, indices, currencies or physical/reference objects that may be referenced by instruments without themselves being directly tradable.

This prevents benchmark/index/reference semantics from being forced into an orderable instrument shape.

## 2.3 Construction kind

`IdentityConstructionKind` distinguishes:

- native;
- synthetic;
- composite;
- continuous reference.

A continuous reference must be a reference object. A continuous futures chain is therefore not allowed to masquerade as one native dated futures contract.

## 2.4 Listing / venue identity

`ListingIdentity` gives one economic identity a separately governed listing/venue representation with:

- independent listing ID;
- parent economic identity ID;
- venue code;
- display symbol;
- effective interval;
- evidence reference.

Two listings may legitimately share a display symbol while remaining distinct listings of the same economic identity.

```text
SAME SYMBOL != SAME LISTING
SAME ECONOMIC IDENTITY MAY HAVE MULTIPLE LISTINGS
```

---

# 3. External identifier model

`ExternalIdentifier` keeps external identity material explicit and non-sovereign.

The semantic classes are:

- `LEGACY_QORE` — legacy QORE symbol identity material used for migration;
- `PROVIDER_NATIVE` — broker/provider runtime identifiers; explicit `ExternalSourceDescriptor` required;
- `VENUE_NATIVE` — exchange/venue-native identifiers; explicit venue required;
- `STANDARD` — cross-provider standards such as ISIN-like namespaces;
- `NETWORK_NATIVE` — network/on-chain identifiers where applicable.

This explicitly resolves the UMI-01 informational observation that a standard security identifier and a broker runtime key are not semantically identical even though neither becomes QORE canonical identity.

```text
STANDARD IDENTIFIER MAY AID CROSS-PROVIDER RECONCILIATION
!=
STANDARD IDENTIFIER BECOMES QORE SOVEREIGN IDENTITY
```

Provider-native identifiers require explicit source provenance. Venue-native identifiers require explicit venue scope. Legacy QORE identifiers cannot masquerade as provider/venue facts.

---

# 4. Typed identity relationships

`IdentityRelationship` forms an effective-dated directed edge between economic identities.

Relationship roles are extensible validated codes rather than a closed global family enum. This permits later family stages to define semantic roles without redesigning identity.

Examples that UMI-02 can already represent:

- option / future / derivative -> underlying;
- future contract -> series/reference;
- instrument -> benchmark;
- FX pair -> base-currency reference;
- FX pair -> quote-currency reference;
- instrument -> denomination/settlement currency reference;
- synthetic/composite -> ordered component identities;
- structured instrument -> reference/component identities.

Optional positive `ordinal` preserves ordered composition where leg ordering is material.

A relationship cannot point from an identity to itself. The graph rejects dangling endpoints and duplicate ordered ordinals within the same relationship/effective scope.

---

# 5. Currency / denomination boundary

UMI-02 deliberately does not promote the existing account-specific `CurrencyCode` or create a universal money/value primitive. Those economic primitives belong to FND-04 and the family stages.

Instead, currencies required for identity relationships are representable as canonical `REFERENCE_OBJECT` economic identities, and instruments relate to them with typed roles such as base, quote, denomination, trading, settlement or collateral currency where applicable.

```text
CURRENCY REFERENCE IDENTITY
!=
MONEY AMOUNT TYPE
```

This permits UMI-02 to freeze identity relationships without prematurely freezing quantity/value semantics.

---

# 6. Contract / series / derivative boundary

A dated contract or option may have its own stable `EconomicIdentityId`; a continuous series or benchmark may have a separate reference-object identity; `IdentityRelationship` links them.

UMI-02 therefore solves contract identity and reference topology without flattening everything into a symbol.

UMI-02 does **not** define every derivative economic term. In particular, numeric strike semantics, option right/exercise style, multipliers, payoff terms and other family economics remain mandatory UMI-05/FND-04 work.

This is the certified UMI-01 sequencing rule:

```text
UMI-02 MUST MAKE FAMILY TERMS ATTACHABLE WITHOUT IDENTITY REDESIGN
!=
UMI-02 IMPLEMENTS EVERY FAMILY ECONOMIC TERM
```

A future option contract can therefore be uniquely identified and related to its underlying/lifecycle now, while its strike/right/exercise semantics are added by UMI-05 without replacing the identity model.

---

# 7. Lifecycle model

`IdentityLifecycleEvent` is an immutable evidence-bearing lifecycle fact with:

- explicit event identity;
- economic or listing subject;
- extensible lifecycle event code;
- `effective_at`;
- `recorded_at`;
- evidence reference.

There is intentionally no universal `expiry` field and no one global lifecycle-state enum.

Examples:

- equity: listing/start, suspension, delisting, corporate-action-related lifecycle events later;
- future: listing, first notice, last trade, expiry where family semantics require them;
- bond: issue, maturity, call/put lifecycle where defined later;
- swap: effective/termination lifecycle;
- perpetual: valid identity with no expiry event.

`recorded_at` is distinct from `effective_at`, allowing future-dated announcements and evidence discovered after an effective event without rewriting historical time.

---

# 8. Versioned mapping lineage

`ExternalIdentityMappingRevision` is an immutable revision of one external/legacy-to-canonical mapping.

It contains:

- stable mapping ID;
- positive mapping revision;
- explicit parent revision;
- exact external identifier;
- canonical economic or listing target;
- effective interval;
- recorded time;
- retained evidence reference.

`IdentityMappingHistory` retains the complete revision chain. It requires:

- one mapping ID;
- one external identity;
- contiguous revisions starting at 1;
- exact parent-revision chain.

The canonical graph additionally requires strictly increasing `recorded_at` across retained revisions and forbids multiple independent mapping histories for the same exact external identity.

This closes the reproducibility requirement certified in UMI-01:

```text
DATASET REVISION != IDENTITY MAPPING REVISION
CURRENT MAPPING != HISTORICAL IDENTITY INTERPRETATION
MAPPING DIGEST != RETAINED VERSIONED MAPPING EVIDENCE
```

Historical research/replay can retain the original legacy symbol bytes while separately citing the mapping revision/evidence that governed the economic interpretation used for a later certified analysis.

No historical dataset is silently rewritten by UMI-02.

---

# 9. Canonical graph integrity

`UniversalInstrumentIdentityGraph` is an immutable composition boundary, not a database or registry implementation.

It requires:

- at least one economic identity;
- unique economic IDs;
- unique listing IDs;
- listing parent identities retained in the graph;
- unique relationship IDs;
- retained relationship endpoints;
- unique ordered-component ordinals inside their scope;
- unique lifecycle event IDs;
- retained lifecycle subjects;
- unique mapping IDs;
- one retained mapping history per exact external identity;
- retained mapping targets;
- increasing mapping recording chronology.

All retained collections are canonicalized into deterministic order before `logical_values()` are emitted.

```text
TYPES EXIST != GRAPH IS CONSISTENT
LOCAL INPUT ORDER != CANONICAL LOGICAL ORDER
```

The graph is technology-neutral. It does not select SQL, Event Sourcing, Kafka, consensus, one global database or a distributed registry implementation.

---

# 10. Answers to the 13 UMI-02 mandatory questions

## Q1 — Stable economic/reference identity

Answer: `EconomicIdentityId` + `EconomicIdentity`, independent of symbol/provider/listing.

## Q2 — Listing / venue independence

Answer: `ListingIdentity` has an independent ID and effective interval while referencing its economic identity.

## Q3 — Provider-native mappings with provenance/effective scope

Answer: `ExternalIdentifier(PROVIDER_NATIVE)` requires `ExternalSourceDescriptor`; mapping revisions carry explicit effective intervals, recording time and evidence.

## Q4 — Series/contracts without universal expiry

Answer: each native contract may have its own economic identity; series/continuous references use separate reference identities and relationships; expiry is a lifecycle event only where applicable.

## Q5 — Underlying/reference links

Answer: evidence-bearing effective-dated `IdentityRelationship` edges.

## Q6 — Denomination/trading/settlement currency relationships

Answer: currencies are reference-object identities; relationship roles carry the identity topology. Money/value primitives remain FND-04 scope.

## Q7 — Lifecycle without one flattening enum

Answer: extensible `LifecycleEventCode` + evidence-bearing lifecycle events, no one global lifecycle state or forced expiry.

## Q8 — Continuous/synthetic/composite vs native

Answer: `IdentityConstructionKind`; continuous reference is constrained to reference-object identity, while synthetic/composite identities remain distinguishable from native primitives.

## Q9 — Legacy migration without breaking evidence/replay

Answer: existing `Instrument`, `ExecutionInstrument` and presentation symbols keep their current meanings; `ExternalIdentifier(LEGACY_QORE)` + mapping history creates an additive bridge. Existing datasets are not rewritten.

## Q10 — Deterministic logical values / secret hygiene

Answer: all new values are immutable and explicitly validated; IDs/timestamps/codes serialize deterministically; graph collections are canonicalized before serialization. External identifiers are identity facts only, never credentials or secret references. Credential-like material is prohibited from identity evidence/logical-value paths.

## Q11 — PR #298 compatibility boundary

Answer: cTrader/provider-native symbol and symbol-ID material maps as external/provider identity evidence into economic/listing targets. PR #298 remains on hold until its then-current exact head is rebased and independently certified against this model.

## Q12 — Minimal adversarial family conformance

Answer: the identity foundation must represent, without semantic collapse, at minimum:

- bond identity + maturity lifecycle/reference relationships;
- listed equity with multiple listings;
- dated future + separate series + expiry lifecycle;
- option identity + underlying + lifecycle while family economics remain UMI-05;
- FX pair + base/quote currency reference identities;
- benchmark/index as a non-tradable reference object;
- multi-leg/composite identity with ordered component relationships;
- perpetual identity without forced expiry.

## Q13 — Versioned historical mapping lineage

Answer: `ExternalIdentityMappingRevision` + `IdentityMappingHistory` + graph uniqueness/chronology rules provide versioned, effective-dated, evidence-bearing, historically retained mapping lineage.

---

# 11. Legacy migration classification

| Existing boundary | UMI-02 treatment |
|---|---|
| `market_data.Instrument` | Retained unchanged as legacy market-symbol boundary; mapped additively |
| `ExecutionInstrument` | Retained unchanged; future execution projection references certified canonical identity |
| `ExecutiveMarketInstrument` | Retained as presentation projection; not identity authority |
| provider symbol / provider contract ID | Retained external boundary evidence; mapped, never promoted as economic identity |
| standard security identifier | Retained typed external identifier; useful reconciliation bridge, never QORE sovereign identity |
| `FuturesContractMapping` | Retained provider adapter foundation; future mapping target must bind certified identity graph |
| historical OHLC/replay datasets | Retained unchanged; historical identity interpretation is carried by explicit mapping lineage |
| research fingerprints/evidence | Existing values remain reproducible; future identity-aware evidence must cite mapping/canonical identity lineage |
| PR #298 cTrader catalog | Remains HOLD until exact-head compatibility rebase/re-review after UMI-02 certification |

No old public/internal symbol type is redefined in place by this stage.

---

# 12. Downstream family boundary

UMI-02 intentionally leaves these OPEN:

- FND-04: universal quantity/price/value/rate/yield/currency economic primitives;
- UMI-03: fixed-income/bond economics;
- UMI-04: rates/curves/term structures;
- UMI-05: derivatives economics including strike/right/exercise/multiplier/legs/payoff;
- UMI-06: equity/fund/corporate-action semantics;
- UMI-07: commodity/contract delivery economics;
- UMI-08: crypto/perpetual/funding/network economics;
- UMI-09: structured/hybrid/payoff composition;
- UMI-10/11: universal valuation observations and market topology;
- Program G: research execution/analysis lineage producer gaps.

These are not UMI-02 defects. UMI-02 is correct only if those stages can attach their semantics to the identity graph without replacing it.

---

# 13. Security and evidence discipline

New identity contracts contain no authentication secrets, provider credentials or execution authority.

`IdentityEvidenceRef` is an opaque reference to retained evidence, not the evidence payload and not a hash substitute.

External identifiers may contain public/provider-native lookup material, but they must never be used to carry credentials. Any identity value admitted into `logical_values()` must remain safe for deterministic evidence use.

```text
IDENTIFIER != CREDENTIAL
EVIDENCE REF != SECRET
EVIDENCE REF != RETAINED EVIDENCE CONTENT
HASH != RETAINED SOURCE EVIDENCE
```

---

# 14. Explicit non-claims

UMI-02 does **not** claim:

- every asset family is fully modeled;
- strike/right/coupon/yield/multiplier/payoff semantics are implemented;
- any provider catalog is universally certified;
- PR #298 is ready to merge/promote;
- existing market/execution symbols are obsolete;
- historical datasets have been rewritten;
- a productive instrument registry exists;
- external identifiers are globally unique outside their declared namespace/scope;
- a database, event log or consensus mechanism has been selected;
- operational trading support has been enabled;
- research lineage gaps are closed;
- production is authorized.

---

# 15. Certification cases

The implementation candidate must demonstrate at minimum:

```text
UMI02-CASE-01  Stable economic identity independent of symbol/provider
UMI02-CASE-02  Tradable vs reference-object distinction
UMI02-CASE-03  Multiple listings for one economic identity
UMI02-CASE-04  Provider / venue / standard identifier separation
UMI02-CASE-05  Underlying / reference / currency / series relationships
UMI02-CASE-06  Ordered composite / multi-leg relationships
UMI02-CASE-07  Lifecycle without universal expiry
UMI02-CASE-08  Perpetual / non-expiring identity conformance
UMI02-CASE-09  Versioned effective-dated mapping lineage
UMI02-CASE-10  Historical mapping retention / reproducibility
UMI02-CASE-11  Graph referential integrity / no dangling identities
UMI02-CASE-12  No parallel external mapping authority
UMI02-CASE-13  Deterministic canonical graph ordering
UMI02-CASE-14  Strict runtime type/time validation
UMI02-CASE-15  Legacy compatibility / no silent reinterpretation
UMI02-CASE-16  PR #298 remains HOLD pending compatibility certification
```

No case is `CLOSED` merely because this document or a type exists. Case closure requires exact-head tests, CI, independent adversarial review, Integration Gate, exact-head integration and post-merge verification.

---

# 16. UMI-02 closure gate

```text
IMPLEMENTATION
-> ADVERSARIAL TESTS
-> DIFF / BLAST-RADIUS AUDIT
-> DRAFT PR
-> EXACT-HEAD QUALITY GATE
-> INDEPENDENT ADVERSARIAL REVIEW
-> CORRECTION / EXACT-HEAD RE-REVIEW IF REQUIRED
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> EXPECTED-HEAD MERGE
-> VERIFY MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> MARK UMI02-CASE-01..16 CLOSED
-> MARK UMI-02 CLOSED IN #301
-> DECLARE STAGE-03 CLOSED
```

Only after that closure may the next serialized stage begin.
