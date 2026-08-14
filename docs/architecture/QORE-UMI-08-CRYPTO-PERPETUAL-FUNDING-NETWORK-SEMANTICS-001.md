# QORE-UMI-08-CRYPTO-PERPETUAL-FUNDING-NETWORK-SEMANTICS-001

## Status

**PROGRAM D / UMI-08 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #330  
Master roadmap: #303  
Universal Markets / Instruments: #301  
Certified starting baseline: `c7173ab0b21969c8d836127999f70c10ad66707c`  
Predecessor UMI-07 / #328 / PR #329: CERTIFIED/CLOSED.

## 1. Constitutional boundary

```text
ECONOMIC / REFERENCE IDENTITY -> UMI-02 / D04
NETWORK_NATIVE EXTERNAL IDENTIFIER -> UMI-02 / D04
GENERIC IDENTITY RELATIONSHIP -> UMI-02 / D04
GENERIC LIFECYCLE EVENT -> UMI-02 / D04

DERIVATIVE MULTIPLIER / TICK PRIMITIVES -> UMI-05
PERPETUAL CONTRACT != DATED FUTURES CONTRACT
NO FAKE CONTRACT MONTH
NO FAKE EXPIRY

MARK / INDEX / LAST PRICE ROLE != OBSERVED PRICE
FUNDING INTERVAL / SIGN != OBSERVED FUNDING RATE
OBSERVED PRICE / FUNDING VALUE -> D07 / UMI-10

NETWORK QUALIFICATION != NETWORK IDENTITY GRAPH
NETWORK_NATIVE IDENTIFIER != ECONOMIC IDENTITY
CEX / AMM / OTC / ON-CHAIN TOPOLOGY -> UMI-11

COLLATERAL IDENTITY != COLLATERAL BALANCE
COLLATERAL IDENTITY != MARGIN / LIQUIDATION STATE
SETTLEMENT IDENTITY != SETTLEMENT MUTATION
FUNDING PAYMENT IDENTITY != PAYMENT EXECUTION

REFERENCE / SETTLEMENT / COLLATERAL / FUNDING-PAYMENT ROLES
MAY COINCIDE WHEN PRODUCT ECONOMICS REQUIRE
NO FALSE UNIVERSAL EQUALITY OR INEQUALITY

EVIDENCE REF != EVIDENCE CONTENT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

This stage does not implement provider support, observations, valuation, wallets, custody,
chain RPC, oracle ingestion, margin/liquidation, settlement, execution, productive Cloud or
real capital.

## 2. Exact-baseline audit

### 2.1 UMI-02 is already identity/network/lifecycle authority

Direct inspection at the certified baseline establishes that UMI-02 already owns:

- `EconomicIdentityId`;
- `IdentityRelationshipId` / `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- `ExternalIdentifierKind.NETWORK_NATIVE`;
- perpetual identity without forced expiry.

Therefore UMI-08 must not create another crypto identity, network graph, relationship graph,
lifecycle history or artificial expiry.

### 2.2 FND-04 leaves perpetual economics open

FND-04 explicitly identifies these crypto-perpetual distinctions:

- perpetual/economic identity;
- venue/network identity;
- token/base quantity;
- mark/index/last prices;
- funding rate and interval;
- collateral asset;
- provider/account terms.

It explicitly rejects conflating funding rate with quote spread and collateral asset with an
assumed settlement currency.

### 2.3 UMI-05 primitives are reusable; FuturesContractTerms is not

UMI-05 owns reusable `DerivativeContractMultiplier` and `DerivativeTickValue`.

Its `FuturesContractTerms` necessarily contains `contract_month` and `expiry_date`.
A perpetual cannot reuse that aggregate without false semantics.

```text
REUSE UMI-05 MULTIPLIER / TICK
!=
FORCE PERPETUAL INTO FuturesContractTerms
```

### 2.4 Observation boundary

UMI-08 may define the roles `mark-price`, `index-price`, `last-price` and the funding
convention. It may not retain current mark/index/last/funding numeric observations.

D05 owns observed provider/on-chain evidence.
D07/UMI-10 owns canonical observations, valuation and methodology.

### 2.5 Topology boundary

UMI-08 may retain a network qualification bound to existing UMI-02 material.
It does not decide CEX vs AMM vs OTC vs other topology. UMI-11 owns topology.

### 2.6 Gap conclusion

No inspected canonical contract closes the bounded perpetual/funding/price-role/network
semantics without violating the authorities above.

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-08 CONTRACT DELTA REQUIRED`

## 3. Candidate inventory

The candidate adds only:

- `CryptoTermsId`;
- `CryptoEvidenceRef`;
- `CryptoFundingScheduleCode`;
- `CryptoNetworkBindingRoleCode`;
- `CryptoPerpetualPriceRole`;
- `CryptoFundingSignConvention`;
- `CryptoFundingInterval`;
- `CryptoFundingTerms`;
- `CryptoNetworkBindingTerms`;
- `CryptoPerpetualPricingTerms`;
- `CryptoPerpetualContractTerms`.

No provider, observation, account, wallet, settlement, risk or execution type is introduced.

## 4. Local IDs and evidence

`CryptoTermsId` is local terms identity only.
`CryptoEvidenceRef` is opaque retained-evidence reference only.

Neither is `EconomicIdentityId`. Neither generates UUIDs implicitly.

## 5. Price-role semantics

`CryptoPerpetualPriceRole` distinguishes exactly:

- `MARK_PRICE`;
- `INDEX_PRICE`;
- `LAST_PRICE`.

`CryptoPerpetualPricingTerms` binds those roles to an existing UMI-02
`IdentityRelationshipId`, retains no source/target/effective fields and contains no observed
price value. Retaining the relationship ID proves local referential binding only; governed
composition with the UMI-02 graph must verify the relationship endpoints and effective scope.

All three roles are required so a generic "price" cannot collapse them.
Duplicates fail. Caller order is canonicalized.

```text
ROLE VOCABULARY != OBSERVATION
```

## 6. Funding convention

`CryptoFundingInterval` requires exactly one mode:

- positive strict `fixed_seconds`; OR
- typed `CryptoFundingScheduleCode`.

A fixed cadence is not assumed universal. A schedule code does not grant scheduler authority;
D06 remains clock/schedule authority.

`CryptoFundingSignConvention` distinguishes whether a positive rate means long pays or short
pays.

`CryptoFundingTerms` retains payment `EconomicIdentityId` but no funding-rate magnitude.

```text
FUNDING CONVENTION != FUNDING OBSERVATION
FUNDING PAYMENT ASSET != PAYMENT EXECUTION
```

## 7. Network qualification

`CryptoNetworkBindingTerms` binds an existing UMI-02 `IdentityRelationshipId`, a bounded role,
evidence ref and optional existing `ExternalIdentifier`.

If the identifier is present, its kind must be `NETWORK_NATIVE`.

The UMI-08 type deliberately owns no source/target endpoints, effective interval or graph
mutation. Retaining a relationship ID or NETWORK_NATIVE identifier does not prove endpoint
kind, current effectiveness or operational network support; governed UMI-02 composition owns
those checks.

It implements no wallet, custody, signing, RPC or transaction submission.

## 8. Perpetual contract

`CryptoPerpetualContractTerms` retains:

- local terms ID;
- perpetual instrument identity;
- reference identity;
- settlement identity;
- collateral identity;
- UMI-05 multiplier;
- optional UMI-05 tick value;
- funding terms;
- pricing terms;
- optional network binding;
- evidence ref.

It has no contract month, expiry, first notice, last trade or duplicated settlement-style
field.

The instrument identity must differ from reference, settlement, collateral and
funding-payment identities.

Reference, settlement, collateral and funding-payment identities may legitimately coincide
with each other, preserving inverse-style products. They may also differ.

No universal multiplier-unit equality is imposed because linear/inverse contract conventions
differ.

## 9. Lifecycle

No UMI-08 lifecycle-event type is added.

A perpetual has no forced expiry, but suspension/migration/delisting or other lifecycle facts
remain UMI-02 evidence-bearing lifecycle events.

```text
NO EXPIRY != NO LIFECYCLE
```

## 10. Collateral / risk / settlement

`collateral_identity_id` is contractual role identity only.

It is not collateral amount, leverage, initial/maintenance margin, liquidation price/state,
exposure or capacity. D08/D09 own those facts.

Settlement/payment identities do not mutate cash, positions or custody. D11 owns mutation.

## 11. Determinism and safety

All candidate dataclasses use `frozen=True, slots=True`.

Candidate requires:

- explicit local UUIDs;
- typed `EconomicIdentityId`;
- typed `IdentityRelationshipId`;
- typed code wrappers;
- canonical lowercase codes;
- strict positive int for fixed funding cadence, rejecting bool;
- exactly one funding cadence mode;
- typed funding sign convention;
- `NETWORK_NATIVE` external identifier when present;
- exact unique mark/index/last role set;
- deterministic role sorting;
- deterministic `logical_values()`;
- no wall clock, uuid4, random, global mutable state, retry, sleep, thread or scheduler.

## 12. PRE-CHK targets

### PRE-CHK-UMI08-00 — Dated-futures laundering

Attack fake `contract_month`, `expiry_date`, first/last-trade fields or reuse of
`FuturesContractTerms`.

PASS requires no dated-futures lifecycle semantics and reuse only of valid UMI-05 primitives.

### PRE-CHK-UMI08-01 — Observation authority leakage

Attack numeric mark/index/last/funding fields and observe/calculate methods.

PASS requires roles/conventions only.

### PRE-CHK-UMI08-02 — Network identity duplication

Attack copied relationship endpoints/effective dates or second network graph.

PASS requires existing relationship ID + optional NETWORK_NATIVE identifier only.

### PRE-CHK-UMI08-03 — Funding cadence flattening

Attack no mode, both modes, zero/negative/bool fixed seconds and raw schedule strings.

PASS requires exactly one typed mode.

### PRE-CHK-UMI08-04 — False linear/inverse constraints

Attack `reference == settlement == collateral == funding-payment`.

PASS requires it remain valid when the instrument identity is distinct.

Attack instrument collision with each economic role.

PASS requires all such self-role collisions fail closed.

### PRE-CHK-UMI08-05 — Topology/custody/execution leakage

Search for wallet, custody, RPC, signing, oracle, AMM topology, liquidation, margin,
settlement or execution authority.

PASS requires none.

## 13. Authority map

| Material | Authority |
|---|---|
| Economic/reference identity | UMI-02 / D04 |
| Network-native external identifier | UMI-02 / D04 |
| Relationship endpoints/effective scope | UMI-02 / D04 |
| Lifecycle fact | UMI-02 / D04 |
| Derivative multiplier/tick primitive | UMI-05 |
| Perpetual/funding/network contractual qualification | UMI-08 |
| Provider/on-chain evidence | D05 |
| Funding schedule/clock resolution | D06 |
| Mark/index/last/funding observations + valuation | D07 / UMI-10 |
| Account/collateral balances | D08 |
| Margin/liquidation/risk/capacity | D09 |
| Execution | D10 / D18 |
| Position/cash/custody/settlement mutation | D11 |
| Market topology | UMI-11 |

## 14. Required adversarial tests

At minimum attack:

- local IDs masquerading as economic identity;
- raw UUID economic identity laundering;
- mark/index/last collapse, missing/duplicate/wrong role material and caller ordering;
- funding no/both modes, zero/negative/bool seconds, raw schedule;
- wrong funding payment/sign types;
- raw relationship ID;
- non-NETWORK_NATIVE external identifier;
- copied relationship endpoints;
- fake expiry/month/notice fields;
- instrument collision with each economic role;
- valid inverse-style role coincidence;
- multiplier/tick reuse without quantity reinterpretation;
- observed value leakage;
- hidden wallet/custody/RPC/oracle/liquidation/settlement/execution behavior;
- mutation of frozen values;
- nondeterministic or secret-bearing logical material.

## 15. Security / non-claims

UMI-02 external identifiers already reject credential-like public identifier material.
UMI-08 evidence refs are references only.

UMI-08 does not certify any provider, exchange, blockchain, oracle, wallet, custody, funding
observation, price observation, margin/liquidation system, settlement system, execution path,
production environment or real capital.

## 16. Carry-forwards

Remain unchanged:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH.

## 17. Gate discipline

`CERTIFIED BASELINE -> AUDIT -> MINIMUM ARCHITECTURE -> IMPLEMENTATION -> ADVERSARIAL TESTS -> DIFF AUDIT -> DRAFT PR -> EXACT-HEAD CI -> FREEZE -> CLAUDE REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE VERIFICATION -> BASELINE FREEZE -> UMI-08 CLOSED`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT REVIEW -> NO READY -> NO MERGE`

`MERGED != CERTIFIED`
