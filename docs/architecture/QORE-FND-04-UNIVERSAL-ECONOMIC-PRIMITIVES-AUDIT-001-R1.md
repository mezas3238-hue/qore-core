# QORE-FND-04-UNIVERSAL-ECONOMIC-PRIMITIVES-AUDIT-001-R1

## Status

**STAGE-04 / FND-04 — INDEPENDENT REVIEW CORRECTION R1; RE-REVIEW REQUIRED**

Tracking: #310  
PR: #311  
Primary artifact: `QORE-FND-04-UNIVERSAL-ECONOMIC-PRIMITIVES-AUDIT-001.md`  
Certified starting baseline: `89705ed8c5cc3e4bf39a74ec2c37111a52285f8f`  
Previous reviewed head: `ac3a8f973b96896fb106e406acea9b10ed2a994d` — historical only after this correction.

This addendum is a normative correction to the primary FND-04 audit. The certifiable FND-04 set is the primary artifact plus this R1. Where an explicit R1 statement conflicts with the primary artifact, R1 governs. R1 changes no production code, tests, runtime, provider adapter, or UMI-03+ implementation.

---

## R1-01 — Rate / yield / spread invariant

Supersede:

`RATE != YIELD WITHOUT EXPLICIT SEMANTICS`

with:

```text
RATE != YIELD != SPREAD
RATE, YIELD, AND SPREAD ARE DISTINCT ECONOMIC SEMANTIC CLASSES
NUMERIC EQUALITY DOES NOT ESTABLISH SEMANTIC INTERCHANGEABILITY
```

Tenor, day-count, compounding, reference, methodology and evidence make a fact reproducible; they do not erase the semantic distinction between rate, yield and spread. `DEC-FND04-06` is interpreted accordingly.

---

## R1-02 — Price versus valuation output

The primary rule `Price != ValuationResult` remains authoritative. `DEC-FND04-05` must not be read as classifying every listed value as a market/execution price.

Market/execution/reference price semantics may include trade/last, bid/ask/mid, clean, dirty, mark, index/reference and settlement price.

Valuation/derived-output semantics may include NAV, accrued amount, model-derived price/valuation and other future UMI-10 typed outputs.

```text
NAV != EXCHANGE MARKET PRICE
VALUATION OUTPUT != MARKET OBSERVATION BY NUMERIC COINCIDENCE
```

A valuation output may be price-like or use the same currency-per-unit dimension as a market price while retaining different methodology, input, source, time and evidence authority.

---

## R1-03 — FND04-CASE-15: Repo / Securities Financing Transaction

Potential distinctions:

- repo transaction identity;
- collateral-security `EconomicIdentityId`;
- collateral role and provenance;
- security quantity or face/par amount;
- cash principal / money amount;
- repo/funding rate;
- haircut or margin ratio where applicable;
- initial settlement date;
- repurchase/termination date;
- settlement currency;
- counterparty/account/custody scopes where applicable.

UMI-02 has one singular `kind: EconomicIdentityKind` per `EconomicIdentity`. A tradable security used as collateral remains a `TRADABLE_INSTRUMENT` identity when that is its certified kind. Referencing it in a collateral role does not reclassify that same identity as `REFERENCE_OBJECT`, and identity kind does not grant collateral/account/risk authority.

```text
REPO/FUNDING RATE != BOND YIELD != CREDIT SPREAD
SETTLEMENT DATE != REPURCHASE DATE != MARKET TIMEFRAME
```

Pass condition: the architecture can reference a tradable security in a collateral role without changing its identity kind; keeps collateral role/state under its owning downstream authority; keeps repo funding rate distinct from security yield; and never reduces settlement/repurchase dates to `Timeframe(seconds)`.

---

## R1-04 — FND04-CASE-16: ETF primary market / NAV versus market price

Potential distinctions:

- ETF economic identity;
- ETF listing/venue identity;
- constituent identities;
- basket weights/quantities;
- retail share quantity;
- creation/redemption unit quantity;
- exchange bid/ask/last market prices;
- NAV or other derived valuation;
- valuation methodology/time/evidence.

```text
ETF MARKET PRICE != ETF NAV
RETAIL SHARE QUANTITY != CREATION/REDEMPTION UNIT SEMANTIC BY ASSUMPTION
ETF IDENTITY != CONSTITUENT IDENTITY
```

NAV is a valuation/derived-output semantic, not an exchange `MarketPrice` merely because both may be currency-per-unit values.

Pass condition: ETF identity, constituent identities, basket composition, exchange market observations, NAV/derived valuation, and creation-unit conventions remain explicitly distinct.

---

## R1-05 — PR #298 ProviderMarginTerms promotion constraint

PR #298 remains HOLD. Before provider-catalog promotion:

1. FND-05 / UPR-01 must freeze authoritative provider/server/provider-account identity relationships;
2. `ProviderMarginTerms` and associated provider-native catalog facts must bind to that typed provider scope instead of unqualified raw provider/server/account strings as canonical scope;
3. provider-native leverage/margin/tier evidence remains provider fact and must not define Core Risk policy;
4. the rebased PR requires independent compatibility review, exact-head CI and Integration Gate.

```text
NO TYPED PROVIDER SCOPE -> NO PROVIDER-CATALOG PROMOTION
PROVIDER-NATIVE MARGIN TERMS != CORE RISK POLICY
```

---

## R1-06 — Review evidence and temporal obligation

The first independent review remains useful evidence, but two review statements are explicitly corrected for certification:

- one `EconomicIdentity` is not simultaneously both identity kinds; collateral is a role/reference relationship, not a second kind on the same identity;
- NAV is not automatically a market-price kind; it is a valuation/derived-output semantic unless a later certified contract defines a more specific typed relationship.

`GAP-FND04-TIME-01` remains a verified cross-cutting obligation. No production timestamp helper is introduced here, no blind `.isoformat()` replacement is authorized, and FND-08 may not certify broad Levels 0–3 temporal determinism while required remediation remains unresolved.

---

## R1 closure discipline

This addendum does not self-certify. After this correction the required sequence is:

```text
NEW EXACT HEAD
-> FULL PR BLAST-RADIUS VERIFICATION
-> NEW EXACT-HEAD QORE CI
-> INDEPENDENT CORRECTION RE-REVIEW
-> VERIFY PRIMARY + R1 COMPOSITION
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> MERGE(expected_head_sha)
-> VERIFY MERGE COMMIT/PARENTS
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> FND-04 CLOSED
```

Previous head `ac3a8f973b96896fb106e406acea9b10ed2a994d` and QORE CI #976 are historical review evidence after the branch advances.
