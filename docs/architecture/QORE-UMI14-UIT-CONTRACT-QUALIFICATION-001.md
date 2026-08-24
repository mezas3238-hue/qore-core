# QORE-UMI14-UIT-CONTRACT-QUALIFICATION-001

## 1. STATUS

**PROGRAM D / UMI-14 — UMI13-UNR-016 R2 FULL-CLOSURE CANDIDATE — NOT YET CERTIFIED**

Tracker: #400  
Parent audit: #363  
PR: #401  
Target: `UMI13-UNR-016` — bounded US-style Unit Investment Trust qualification

Current certified predecessor baseline:

`40280e0574ae0e7ac6c9ff37afb7bbe314c6368a`

The earlier preparatory candidate and R1 freeze are historical evidence only. R2 is the bounded correction produced after independent DeepSeek Expert finding `DS-EXPERT-UNR016-R1-01` identified an unguarded root-to-component economic identity collision.

## 2. BOUNDED PURPOSE

This owner provides a bounded identity-rooted Unit Investment Trust qualification over complete UMI-02 `EconomicIdentity`.

It does **not** create:

- a universal/global UIT ontology;
- a sovereign fund vehicle owner;
- a parallel `FundVehicleTerms` owner;
- a generic fund taxonomy rewrite;
- NAV/current holdings authority;
- execution, redemption, liquidation or settlement authority;
- provider or legal/regulatory authority.

`UIT QUALIFICATION != UNIVERSAL FUND TAXONOMY`

## 3. ETF + UIT COEXISTENCE

ETF and UIT are not mutually exclusive in the bounded scope.

QORE may retain ETF form through UMI-06 `FundVehicleTerms(vehicle_kind=ETF)` while this qualifier retains UIT-specific structure on the same complete economic identity.

A non-ETF UIT is also representable because this owner does not require `FundVehicleTerms` or any existing `FundVehicleKind` member.

No `FundVehicleKind.UNIT_INVESTMENT_TRUST` member is added in this lane.

## 4. COMPLETE ECONOMIC IDENTITY ROOT

The root is:

`fund_identity: EconomicIdentity`

not merely `EconomicIdentityId`.

The qualifier preserves complete identity projection: identity ID, kind, family, construction and identity evidence.

The root must be an exact `EconomicIdentity`, exact `TRADABLE_INSTRUMENT`, exact `IdentityFamilyCode("funds-pooled-vehicles")`, and must retain exact nested UUID state.

A tradable UIT identity cannot use `CONTINUOUS_REFERENCE` construction.

## 5. TYPE-ENCODED UIT MATERIAL

Existence of a valid `UnitInvestmentTrustQualification` explicitly means:

- `redeemable-security`;
- `undivided-interest`;
- one or more contractually specified securities.

The first two are type-encoded invariants rather than booleans because `False` would contradict the bounded qualified form.

## 6. SPECIFIED-SECURITY MATERIAL

`UnitInvestmentTrustSpecifiedSecurity` is a local D04 carrier for one contractually specified security identity plus local evidence.

Each component:

- carries a complete exact `EconomicIdentity`;
- must be a tradable instrument;
- retains identity evidence plus local UIT evidence;
- must have an `EconomicIdentityId` different from the root `fund_identity.identity_id`;
- is not a current holding, quantity, weight, allocation, market value or derivative payoff leg.

The tuple is exact, immutable and non-empty. Duplicate component economic identity IDs are rejected. A specified security whose canonical `EconomicIdentityId` equals the root fund identity is also rejected, even when its family/evidence projection differs, because UMI-02 identity authority makes that the same economic instrument. Incidental caller ordering is not contractual authority, so components are canonicalized deterministically by economic identity ID.

A fund-of-funds style specified security remains valid when the nested fund has a distinct `EconomicIdentityId`.

No UMI-09 `StructuredComponentBinding` is reused as a false fund-holdings owner.

## 7. NO INVENTED QUANTITY / WEIGHT LAW

The bounded evidence establishes specified securities but does not establish a universal contract quantity, weight or allocation field for every valid in-scope UIT.

Therefore R2 does not invent quantity/weight semantics and does not claim current portfolio state.

`SPECIFIED SECURITY != CURRENT HOLDING`

## 8. OPTIONAL CONTRACTUAL TERMINATION DATE

`contractual_termination_date: date | None` is optional bounded static material.

When present it must be exact `date`, not `datetime`.

It does not create:

- wall-clock/currentness evaluation;
- scheduler/timer;
- lifecycle-event generation;
- liquidation execution;
- settlement mutation.

UMI-02 `IdentityLifecycleEvent` is historical/evidence-bearing lifecycle material and cannot substitute a future contractual termination date.

## 9. EXACT-TYPE / MALFORMED-STATE LAW

R2 treats composition boundaries as untrusted even when an imported type name is correct.

It therefore revalidates:

- local wrapper exact types and nested exact UUIDs;
- exact `EconomicIdentityId` plus nested UUID;
- exact kind/family/construction/evidence types;
- exact family string and imported family-code validation;
- exact component types and their complete retained child state;
- root-to-component economic identity separation;
- exact `date` for optional termination.

Every local `logical_values()` re-runs local validation. A frozen dataclass is not trusted forever: reflective/fabricated or post-construction-corrupted state must fail closed rather than project a valid logical identity.

`TYPE NAME EXISTS != VALID INTERNAL STATE`

## 10. LOGICAL IDENTITY

Qualifier logical material includes, in deterministic order:

- discriminator;
- qualification ID;
- complete fund economic identity;
- `redeemable-security` marker;
- `undivided-interest` marker;
- canonical complete specified-security projections;
- optional contractual termination date;
- local evidence reference.

Specified-security logical material includes:

- discriminator;
- complete security economic identity;
- local evidence reference.

Material differences in retained static state must not collapse. Caller component order alone must not split an otherwise identical logical contract. The root fund cannot re-enter the specified-security set under the same canonical UMI-02 identity.

## 11. NAV / OBSERVATION BOUNDARY

UMI-06 retains fund structural semantics and UMI-10 retains valuation-observation carriers. This owner does not import or duplicate current NAV, NAV calculation, redemption price, current holdings or valuation methodology.

`STATIC UIT QUALIFICATION != NAV OBSERVATION`

## 12. NEGATIVE AUTHORITY SURFACE

This module owns no:

- current NAV/value/calculation;
- current holdings/positions;
- quantity/weight/allocation/market value;
- redemption request or execution;
- cash/in-kind distribution;
- liquidation execution;
- listing/venue authority;
- provider symbol/capability;
- order/trade/receipt;
- settlement mutation;
- legal eligibility or governance determination;
- wall clock, random UUID, network, I/O, retry, scheduler, thread or timer;
- Production enablement;
- real-capital authorization.

## 13. R1 HARDENING / R2 EXPERT CORRECTION

After UNR-015 integration, the preparatory candidate was reconstructed directly over certified `main`. R1 hardened local wrapper and child revalidation and made every local `logical_values()` re-run validation before projection.

DeepSeek Expert R1 then identified `DS-EXPERT-UNR016-R1-01`: the qualifier rejected duplicate component IDs but did not reject a component carrying the root fund's own canonical `EconomicIdentityId`. R2 adds that single identity-separation invariant plus adversarial regressions for exact self-reference, same-ID/different-projection collision, and a distinct-ID nested-fund acceptance witness.

This correction does not expand semantic or downstream authority.

## 14. FILE SURFACE

R2 remains bounded to the UIT owner, its tests and its architecture evidence. Relative to the certified predecessor baseline the changed surface is:

1. `src/qore/infrastructure/uit_contract_qualification.py`
2. `tests/infrastructure/test_uit_contract_qualification.py`
3. `tests/infrastructure/test_uit_contract_qualification_r2.py`
4. `docs/architecture/QORE-UMI14-UIT-CONTRACT-QUALIFICATION-001.md`

No certified UMI-02/06/09/10 owner is modified. No UMI-13 registry mutation. No UMI-12 conformance-harness mutation.

## 15. GATE

R2 remains uncertified until the exact final HEAD completes:

`FULL CI -> DIFF AUDIT -> FREEZE -> EXACT SYNTHETIC BINDING -> DEEPSEEK EXPERT -> IA -> DEEPSEEK CODER -> IA -> CLAUDE CODE -> IA -> IA FINAL -> READY -> MERGE(expected_head) -> POST-MERGE VERIFY -> CLOSE #400`

Any HEAD mutation after freeze invalidates the external-review round and requires a new exact binding.

CI green is necessary but not semantic certification. No self-certification is permitted.

No UMI-14 / Program-D closure is authorized by this lane alone. Production remains closed and real capital remains unauthorized.
