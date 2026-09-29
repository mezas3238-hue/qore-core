# QORE Shared AGRI-2 — UMI-Composed Agricultural Identity Contract 001

## Status

**AGRI-2 — ARCHITECTURE / QUALIFICATION CONTRACT IMPLEMENTED; NO REAL AGRICULTURAL IDENTITY PROMOTED**

Primary PR: #635  
Governance: DRAFT / research-only / no LIVE / no Production / no capital / no Risk or execution authority.

This contract implements the second Owner deliverable after AGRI-0/AGRI-1:

> build canonical agricultural sensor identities without creating a second identity system.

The current governed provider catalogue still exposes zero agricultural/soft/livestock
candidates, so AGRI-2 builds the lawful composition and validation surface only.
It does **not** fabricate Corn/Wheat/Soy/Coffee/Cattle provider mappings.

## 1. Owner authority reuse

AGRI-2 composes the exact owner surfaces frozen in:

`docs/shared/evidence/QORE_SHARED_AGRI2_UMI_DEPENDENCY_MANIFEST_001.json`

Authority remains:

```text
UMI-02
  -> economic identity
  -> listing / venue identity
  -> native / composite / synthetic / continuous-reference construction

UMI-05
  -> dated futures contract month
  -> expiry
  -> multiplier
  -> tick value
  -> settlement style
  -> first notice
  -> last trade

UMI-07
  -> commodity reference
  -> commodity class
  -> measurement unit
  -> grade
  -> delivery location / method / window
  -> physical-delivery alternatives
  -> commodity futures composition
```

Shared AGRI-2 owns none of those primitives.

## 2. Agricultural specialization added

The additive Shared qualification layer provides:

- `AgriculturalCommodityClass`: bounded agriculture / softs / livestock qualifier;
- `AgriculturalCropYearCode`: opaque crop-year code, not a global crop calendar;
- `AgriculturalCropYearReference`: crop-year context bound to a UMI region identity and retained evidence;
- `AgriculturalCommodityReferenceQualification`: proves that a UMI-02 commodity reference and UMI-07 commodity terms agree;
- `AgriculturalFuturesContractQualification`: proves exact consistency among UMI-02 contract identity, listing, UMI-05 futures identity and UMI-07 commodity futures composition;
- `assert_agricultural_native_execution_identity`: prevents reference/composite/continuous identities from masquerading as native executable contracts.

## 3. Identity laws

```text
PROVIDER SYMBOL != CANONICAL ECONOMIC IDENTITY

COMMODITY REFERENCE IDENTITY
!=
DATED FUTURES CONTRACT IDENTITY

DATED FUTURES CONTRACT
!=
CONTINUOUS RESEARCH REFERENCE

CROP YEAR
!=
CONTRACT MONTH

CROP YEAR
!=
UNIVERSAL CALENDAR

LISTING / VENUE IDENTITY
!=
ECONOMIC IDENTITY
```

A base agricultural commodity reference is a UMI-02 `REFERENCE_OBJECT` in the
`commodities` family.

A dated agricultural futures contract is a UMI-02
`TRADABLE_INSTRUMENT`, `NATIVE` construction, in the `futures` family.

The contract's UMI-05 reference identity and UMI-07 commodity reference must
point to the exact same UMI-02 reference object.

## 4. Crop-year semantics

Crop year is represented only when independently evidenced and region-scoped.

AGRI-2 deliberately does **not** hardcode:

- one universal crop-year calendar;
- one planting/harvest schedule;
- one region for a commodity;
- one crop-year interpretation for every contract.

Those belong to later AGRI-8 crop-cycle/seasonality work.

## 5. Continuous-series firewall

UMI-02 already requires `CONTINUOUS_REFERENCE` to be a reference object.

AGRI-2 adds a defensive execution-identity guard:

```text
EXECUTION CONTRACT
=
TRADABLE_INSTRUMENT
+
NATIVE
```

Therefore:

```text
CONTINUOUS RESEARCH SERIES
!=
EXECUTION IDENTITY
```

The actual continuous-series construction method, roll dates and adjustment
provenance remain AGRI-6 work and are not implemented here.

## 6. Provider boundary

AGRI-2 contains no provider symbol, provider ID or broker discovery logic.

Provider candidates remain in AGRI-1 and must pass independent identity evidence
before being mapped to these UMI-composed identities.

At the current cTrader DEMO baseline:

```text
AGRICULTURAL PROVIDER CANDIDATES = 0
REAL AGRICULTURAL IDENTITIES PROMOTED = 0
```

This is intentional fail-closed behavior.

## 7. Currentness limitation

UMI currentness is preserved exactly rather than exaggerated:

- UMI-02 current status is governed by its Full Closure/currentness record and #301;
- UMI-07 semantic owner exists, while its current Full Closure ledger reports Gate B complete with exact-candidate qualification pending;
- UMI14 is a Gate-B recertification candidate and is not Gate-C certified.

AGRI-2 compatibility with these owner surfaces does not self-certify those programs
and does not imply productive provider support.

## 8. Non-claims

AGRI-2 does not claim:

- Corn, Wheat, Soybeans or any other agricultural market is available from the current provider;
- a CME/ICE contract has been mapped;
- crop-year values have been populated from official evidence;
- exchange calendars are mapped;
- roll mechanics exist;
- data quality is verified;
- continuous series exist;
- relation science is authorized;
- Shared is certified.

## 9. Exit posture

AGRI-2 architecture can be considered **contractually ready** only when:

- tests prove UMI identity/reference/listing consistency;
- tests prove contract/reference identity mismatch fails closed;
- tests prove agricultural-class mismatch fails closed;
- tests prove continuous reference cannot be execution identity;
- exact UMI dependency blobs remain unchanged;
- no provider symbol is promoted automatically;
- no real identity is manufactured from the conceptual discovery universe.

Actual agricultural identity population remains blocked on AGRI-1 provider
discovery plus governed independent identity/contract evidence.

Next scientific dependency:

```text
AGRI-3
CONTRACT CHAIN
+
ROLL STATE
+
LIQUIDITY MIGRATION
```

But no real contract-chain instance can be populated until a governed provider
or source exposes actual agricultural contracts.
