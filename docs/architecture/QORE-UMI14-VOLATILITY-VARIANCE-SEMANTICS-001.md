# QORE-UMI14-VOLATILITY-VARIANCE-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — UNR-012 CURRENT-BASELINE GATE-B RECERTIFICATION CANDIDATE — NOT CERTIFIED**

Tracker: #392  
Parent final audit: #363  
Program root: #301  
Target: `UMI13-UNR-012` — `volatility-variance-products`  
Certified starting baseline: `44ad245b8f3c6af8b40f141844c1058227785cf4`  
Starting tree: `b7cea560575cfd10034f02c9bec60c3d71ac7f09`

Historical preparatory PR #393 and head `390f13eaae656ad740fde4c094c19b6c0f130a31` were built from stale baseline `39e1598e91c912f473f9628c3aab30fe7b9cc034`. They remain provenance only and are not integration authority.

---

## 1. Fresh Gate-A reconstruction

Current `main` contains no `src/qore/infrastructure/volatility_variance_semantics.py` owner.

UMI-10 remains observation/valuation authority and retains `ImpliedVolatility` as observation material. It does not define tradeable variance-, volatility-, or correlation-swap contract economics.

UMI-05 remains the generic derivative primitive owner. Its generic swap-leg structure is not a faithful substitute for the single-netted-leg product economics represented by dedicated variance, volatility and correlation contracts.

The UMI-13 unresolved authority therefore remains material:

`UMI13-UNR-012 — volatility-variance-products — variance/correlation contracts — observation != complete tradeable instrument semantics`.

**Adjudication:** `VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`.

---

## 2. Product evidence and semantic collisions

FpML confirmation schemas distinguish `VarianceSwap` / `VarianceLeg`, `VolatilitySwap` / `VolatilityLeg`, and `CorrelationSwap` / `CorrelationLeg` rather than flattening them into generic market observations.

The bounded owner must preserve at least these non-conflations:

- variance swap != volatility swap;
- variance strike != volatility strike;
- variance amount != optional vega notional;
- correlation contract != single-reference variance/volatility contract;
- different correlation constituents/weights != same contract;
- static calculation convention != realized-metric calculator;
- static observation window != observed path;
- tradeable static terms != UMI-10 implied-volatility observation.

---

## 3. Additive owner surface

Fresh candidate surface:

1. `src/qore/infrastructure/volatility_variance_semantics.py`
2. `tests/infrastructure/test_volatility_variance_semantics.py`
3. `tests/infrastructure/test_volatility_variance_semantics_logical_identity.py`
4. `docs/architecture/QORE-UMI14-VOLATILITY-VARIANCE-SEMANTICS-001.md`

The fourth file is required by current Full Closure oracle law. The historical preparatory tests used SUT/nested `.logical_values()` helpers in portions of expected material and therefore are not sufficient as the sole independent logical-identity oracle.

No certified pre-existing file is modified by this bounded candidate.

---

## 4. Static D04 semantics

### 4.1 Typed contractual wrappers

The owner retains:

- `VolatilityObservationScheduleCode`;
- `VolatilityCalculationConventionCode`;
- `VarianceStrike`;
- `VolatilityStrike`;
- `CorrelationStrike`.

Variance/volatility strikes are finite and non-negative. Correlation strike is finite and bounded to `[-1, 1]`.

### 4.2 Observation terms

`VolatilityObservationTerms` retains explicit start/end dates, schedule code, calculation-convention code and optional strict-positive expected observation count.

It is static contract material only. It does not generate schedules, fetch observations, calculate returns, variance, volatility or correlation.

### 4.3 Settlement terms

`VolatilitySettlementTerms` retains settlement economic identity and date only. Settlement date cannot precede the observation end date. No settlement mutation is performed.

### 4.4 Variance swap

`VarianceSwapTerms` retains:

- exact external UMI-05 `DerivativeTermsId`;
- instrument identity;
- reference identity distinct from the instrument identity;
- observation terms;
- typed variance strike;
- variance amount as `DerivativeNotional`;
- optional distinct vega notional;
- settlement terms;
- evidence.

### 4.5 Volatility swap

`VolatilitySwapTerms` retains the same bounded structural material with a typed volatility strike and required vega notional.

### 4.6 Correlation swap

`CorrelationSwapTerms` retains at least two unique `CorrelationConstituent` entries, each containing a reference identity and positive finite contractual weight, together with a bounded correlation strike and correlation amount.

Constituent order is canonicalized by reference identity because caller tuple order is not treated as separate product economics. Weights are preserved exactly and are not forced to sum to one; this owner does not invent a universal normalization law.

---

## 5. Exact-type trust boundary

Current Full Closure hardening distinguishes local semantic ownership from imported certified owners while protecting every virtual-behavior edge used by this D04 owner.

Owner-local values whose virtual `logical_values()` results are trusted by a parent use exact-type boundaries at the parent edge:

- observation schedule/convention inside `VolatilityObservationTerms`;
- `VolatilityObservationTerms` and `VolatilitySettlementTerms` inside top-level contracts;
- local strike wrappers inside their respective contracts;
- `CorrelationConstituent` entries inside `CorrelationSwapTerms`.

R1/R2 IA falsification then produced concrete counterexamples against permissive imported-owner composition: a subclass of `EconomicIdentityId`, `DerivativeTermsId`, `DerivativeEvidenceRef` or `DerivativeNotional` can satisfy an `isinstance` guard while overriding virtual projection behavior; base/subclass identity equality can also diverge despite identical UUID material. Imported owners can furthermore contain subclassed primitive `UUID` / `Decimal` values where their historical constructors accept subclasses.

Because this is a demonstrated exploit rather than an arbitrary policy preference, the UNR-012 composition boundary requires exact imported wrapper types and exact trusted primitive material for the imported values it projects:

- exact `EconomicIdentityId` with exact `UUID`;
- exact `DerivativeTermsId` with exact `UUID`;
- exact `DerivativeEvidenceRef` with exact `UUID`;
- exact `DerivativeNotional` with exact finite positive `Decimal` and exact validated unit identity.

This is a bounded trust check at the UNR-012 consumer edge. It does **not** change, fork, or claim ownership of UMI-02/UMI-05 semantics, and no certified pre-existing owner source is modified.

---

## 6. Logical identity

Logical material must bind complete static economics, including product discriminant, terms ID, instrument/reference or constituent identities, observation terms, typed strike material, amount/notional material, settlement terms and evidence.

The independent oracle reconstructs expected tuples from primitive UUID/date/Decimal/string fixture constants. Expected material must not be produced from SUT `.logical_values()`, actual output, production sort helpers, production serializers or production enum `.value`.

Correlation caller order must not change logical identity after canonicalization.

---

## 7. Authority map

`UMI-05` -> generic derivative primitive ownership.  
`THIS UNR-012 / D04` -> static variance/volatility/correlation contract qualification.  
`D05` -> retained observations/fixings.  
`D06` -> calendar/schedule resolution and current time state.  
`D07 / UMI-10` -> realized/implied metrics, methodology execution, pricing, calibration and valuation.  
`D08 / D09` -> holdings/exposure/risk.  
`D10 / D18` -> order/execution.  
`D11` -> settlement mutation.

Hard distinctions:

`OBSERVATION != TRADEABLE CONTRACT`

`CALCULATION CONVENTION != CALCULATION ENGINE`

`STATIC OBSERVATION WINDOW != OBSERVED PATH`

`CORRELATION BASKET TERMS != REALIZED CORRELATION`

`CONTRACT NOTIONAL != CURRENT POSITION`

`SETTLEMENT TERMS != SETTLEMENT MUTATION`

---

## 8. Negative space

The owner contains no variance option, dispersion strategy, volatility surface, VIX/index methodology, Greeks, realized-metric calculation, payoff calculator, pricing, calibration, current observation lookup, provider symbol or SDK, network/database I/O, account/position/risk state, execution, settlement mutation, wall-clock lookup, implicit UUID, random source, retry, sleep, thread, scheduler, Production or real-capital authority.

---

## 9. Determinism / immutability

All local semantic values are frozen and slotted. Caller-supplied IDs are explicit. Decimal logical material is canonical. Correlation constituents are canonically ordered by economic reference identity. Dates are explicit contract dates. No implicit wall clock or random identity generation exists.

---

## 10. Gate-B recertification delta versus historical preparation

Historical source/test semantics are retained where compatible with current owners, but fresh Full Closure hardening adds:

- exact `str` code boundary;
- exact local `Decimal` primitive boundary against behavioral subclass spoofing;
- owner-local exact-type child boundaries against behavioral subclass spoofing;
- demonstrated-exploit-driven exact imported-owner composition checks, including nested trusted `UUID` / `Decimal` primitives;
- canonical correlation constituent ordering;
- a dedicated independent logical-identity oracle with adversarial subclass witnesses;
- current-baseline governance/documentation.

These changes are bounded to UNR-012 and do not modify UMI-05 or UMI-10.

---

## 11. Gate state

`GATE A = COMPLETE / REVALIDATED ON CURRENT BASELINE`

`GATE B = COMPLETE / CURRENT-BASELINE CANDIDATE PREPARED`

`GATE C = NOT YET CERTIFIED`

`TRACKER #392 = OPEN`

`HISTORICAL PR #393 = STALE / PROVENANCE ONLY`

`READY = NOT YET ESTABLISHED`

`MERGE = NOT YET ESTABLISHED`

`UNR-012 = NOT CLOSED`

`UMI14 = NOT CLOSED`

`PROGRAM D = NOT DECLARED CLOSED`

`PRODUCTION = CLOSED`

`REAL CAPITAL = NOT AUTHORIZED`

`CI GREEN != ENGINEERING APPROVAL`

`GATE-B CANDIDATE != GATE-C CERTIFICATION`
