# QORE UMI-14 — UNR-018 Futures Final-Settlement Rule Semantics

Tracker: #440  
Parent audit: #363  
Baseline: `470db7333ab08024c002bd0f057b34b0ae30e5e3`

## Decision

UNR-018 is a bounded D04 semantic gap. UMI-05 already owns generic `FuturesContractTerms`: contract month, expiry, multiplier, settlement style, reference/settlement identities, notice/trade dates and evidence. UNR-018 adds only the static product-specific rule material that states **how a contract declares its final-settlement determination procedure**.

The new owner intentionally follows the existing UMI-05 pattern used by contractual fixing/protection-settlement method codes: a method code can be retained as contract material without implementing the engine named by that code.

## Canonical rule material

`FuturesFinalSettlementRule` binds:

- an explicit rule ID;
- exactly one reused UMI-05 `FuturesContractTerms` value;
- a canonical product-specific algorithm code;
- an explicit final-settlement date;
- one or more canonical input declarations;
- optional contractual rounding material;
- an opaque retained evidence reference.

Each input declaration binds an existing UMI-02 `EconomicIdentityId` to a canonical role. It may additionally retain an explicit observation window, sampling interval and/or positive fixed contractual coefficient. A coefficient is retained contract material; UNR-018 neither normalizes coefficients nor evaluates an algorithm.

Observation windows use explicit timezone-aware instants. Equivalent instants canonicalize to UTC. A zero-duration point observation is permitted only without a sampling interval. Windows do not create a scheduler, calendar resolver or market-data subscription.

Input declarations are immutable and deterministically ordered using a total key that handles both absent and present optional material. Exact duplicate logical declarations fail closed. Distinct declarations for the same identity/role remain distinct when their window or fixed coefficient differs.

## UMI-05 composition

The reused `FuturesContractTerms` object and all nested terms/evidence/identity/multiplier/tick leaves are revalidated before UNR-018 emits logical material. UUID and Decimal leaves that influence the UNR-018 projection are required to be exact primitive types, closing reflective/type-confusion paths at the composition boundary.

UNR-018 preserves the exact 13-field UMI-05 futures logical layout. Because legacy UMI-05 multiplier/tick Decimal projection still uses ambient-context `Decimal.normalize()`, the composition projects only those two Decimal text leaves through the context-independent `as_tuple()` canonicalizer already certified by UNR-017. All other UMI-05 fields retain their existing logical semantics.

The same context-independent compact Decimal projection is used for input coefficients and rounding increments. This prevents high-precision A/B collapse, caller `localcontext()` dependence and fixed-notation resource expansion for extreme exponents.

## Chronology boundary

UNR-018 validates `final_settlement_date` as explicit exact contractual material but deliberately does **not** infer a universal ordering relationship against UMI-05 `last_trade_date` or `expiry_date`. Such relationships are product/rule specific unless separately encoded by an authoritative contract rule. The compositor must not reject a valid product merely by inventing a generic chronology.

## Authority boundary

This lane defines a static **rule declaration**, not an executable settlement engine.

It provides no:

- `calculate()` / `compute()` final-settlement engine;
- observed settlement input values or final-settlement result;
- live market-data retrieval, feed subscription or provider symbol mapping;
- valuation methodology engine or D07 computed-valuation authority;
- cheapest-to-deliver selection;
- conversion-factor methodology;
- invoice-price or accrued-interest computation;
- delivery election or notice production;
- execution, order, position, inventory, cash, title-transfer or settlement mutation;
- Risk/account authority;
- Production or real-capital authority.

Downstream D05/D07 components may eventually supply observed values to a separately governed computation boundary. Their existence does not make UNR-018 a market-data or valuation owner.

## Laws

`ALGORITHM CODE != CALCULATION ENGINE`

`OBSERVATION WINDOW != MARKET-DATA RETRIEVAL`

`INPUT DECLARATION != OBSERVED INPUT VALUE`

`FINAL-SETTLEMENT RULE != FINAL-SETTLEMENT RESULT`

`RULE != SETTLEMENT MUTATION`

`FIXED COEFFICIENT != IMPLIED NORMALIZATION`

`UNR-018 != CTD / CONVERSION-FACTOR METHODOLOGY`

`UNR-018 != INVOICE / ACCRUED COMPUTATION`

`UNR-018 != D07 VALUATION ENGINE`

`UNR-018 != PRODUCTION AUTHORITY`
