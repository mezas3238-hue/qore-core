# QORE UMI-14 — UNR-017 Futures Deliverable Basket / Conversion Factor

Tracker: #438  
Parent audit: #363  
Baseline: `72716234db4638fd4293dcaf4c66e36e28cf8541`

## Decision

UNR-017 is a bounded D04 semantic gap. Generic UMI-05 futures terms already own contract month, expiry, multiplier, settlement style, first-notice and last-trade material. This lane adds only the static eligibility basket required by physically deliverable futures whose eligible deliverables carry contract-defined conversion factors.

## Canonical composition

`FuturesDeliverableBasketTerms` composes exact `FuturesContractTerms`; it does not duplicate generic futures validity semantics. Each `FuturesDeliverableBasketEntry` binds an existing UMI-02 `EconomicIdentityId` to one positive finite `FuturesConversionFactor`.

Entries are immutable and canonically ordered. Duplicate economic deliverable identities fail closed even when supplied with different factors. The futures contract's own `instrument_identity_id` cannot re-enter the basket as an eligible deliverable. Logical material retains both deliverable identity and conversion factor, preventing distinct contractual basket material from collapsing. Conversion-factor logical material is canonicalized from the exact Decimal tuple without ambient-context rounding and uses compact scientific form when fixed notation would expand materially.

The composed UMI-05 futures contract and its nested terms ID, economic identities, contract month, multiplier/unit identity, evidence reference and optional tick value are revalidated through their canonical validators before UNR-017 emits logical material. At this composition boundary, reused UUID and Decimal leaves that can affect logical material are additionally required to be exact primitive types rather than subclasses, preventing type-confusion or custom string/normalization behavior from collapsing distinct contractual states. Because legacy UMI-05 Decimal projection for multiplier/tick uses ambient-context normalization, UNR-017 preserves the exact UMI-05 futures field layout and validators while projecting only those two Decimal leaves through the same context-independent compact canonicalizer used for conversion factors. This keeps the composed basket deterministic without changing UMI-05 validity semantics or granting new authority. Entry identity/factor plus basket ID/evidence are likewise revalidated, so post-construction reflective corruption fails closed. Only `PHYSICAL` futures may carry this basket.

## Authority boundary

A conversion factor is retained contractual material. It is not a valuation result and this module does not derive it.

This lane provides no:

- cheapest-to-deliver selection;
- invoice-price or accrued-interest computation;
- conversion-factor calculation methodology;
- final-settlement algorithm (UMI13-UNR-018 remains open and separate);
- delivery election or notice production;
- execution, order, position, inventory, title-transfer or settlement mutation;
- market-data/provider capability;
- risk/account authority;
- Production or real-capital authority.

## Laws

`DELIVERABLE BASKET != SINGLE REFERENCE IDENTITY`

`FUTURES CONTRACT IDENTITY != ELIGIBLE DELIVERABLE IDENTITY`

`DELIVERABLE IDENTITY != CONVERSION FACTOR`

`CONVERSION FACTOR != VALUATION`

`ELIGIBILITY != CHEAPEST-TO-DELIVER SELECTION`

`PHYSICAL CONTRACT TERMS != DELIVERY / SETTLEMENT MUTATION`

`UNR-017 != UNR-018`
