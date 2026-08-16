# QORE-UMI14-VOLATILITY-VARIANCE-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — LANE 9 / UMI13-UNR-012 — PREPARATORY CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracker: #392  
Parent audit: #363  
Starting certified baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

This artifact closes only the bounded static D04 representation gap for tradeable
variance, volatility and correlation swap terms. It does not implement realized
metric calculation, valuation, observation, provider integration, execution,
settlement mutation, Production or real-capital authority.

## 1. Evidence boundary

Exact QORE baseline evidence:

- UMI-05 source: `src/qore/infrastructure/derivative_contract_semantics.py`;
- UMI-05 source blob: `36e4d672459c489573eabc7ba5413bb5ef99c3a6`;
- UMI-10 source: `src/qore/infrastructure/universal_valuation_observation.py`;
- UMI-10 source blob: `daa67c2903e9a5c95b55313b5d3c2667a4c180ae`;
- UMI-13 architecture blob: `ec51c900c2701f885053141601a7792cdf74856e`.

UMI-13 retains:

`UMI13-UNR-012 — variance/correlation contracts — observation != complete tradeable instrument semantics`.

Mechanical reconstruction shows:

- UMI-10 owns `ImpliedVolatility` as valuation-observation material;
- UMI-05 swap legs are fixed-rate, floating-rate, reference-return, exchange or protection;
- UMI-05 `SwapContractTerms` requires at least two legs and both PAY and RECEIVE.

Therefore a single-netted-leg variance, volatility or correlation swap cannot be
faithfully represented by the existing generic swap owner without an external
convention or false structural translation.

External primary evidence used for financial falsification is FpML 5.12 Confirmation
View, which exposes distinct `VarianceSwap`, `VolatilitySwap` and `CorrelationSwap`
product structures and distinguishes their strike/notional material.

## 2. Adjudication

`VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`

The surviving material collisions are:

1. variance swap != volatility swap;
2. variance strike != volatility strike merely because both may be decimals;
3. variance amount != vega-notional semantics;
4. correlation swap != single-reference volatility/variance swap;
5. different correlation baskets/weights != the same contract;
6. static observation/calculation convention != calculated realized metric;
7. tradeable contract terms != UMI-10 implied-volatility observation.

## 3. Candidate inventory

The candidate adds:

- `VolatilityObservationScheduleCode`;
- `VolatilityCalculationConventionCode`;
- `VarianceStrike`;
- `VolatilityStrike`;
- `CorrelationStrike`;
- `VolatilityObservationTerms`;
- `VolatilitySettlementTerms`;
- `CorrelationConstituent`;
- `VarianceSwapTerms`;
- `VolatilitySwapTerms`;
- `CorrelationSwapTerms`.

It reuses UMI-05 `DerivativeTermsId`, `DerivativeEvidenceRef` and
`DerivativeNotional`, plus UMI-02 `EconomicIdentityId`.

It intentionally does not extend or weaken certified UMI-05/UMI-10 files.

## 4. Observation and calculation convention boundary

`VolatilityObservationTerms` retains only static contractual material:

- observation start date;
- observation end date;
- typed schedule qualification;
- typed calculation-convention qualification;
- optional expected observation count.

The observation interval must be forward. An expected count, when present, is a strict
positive integer. The object does not generate dates, retrieve prices, decide market
holidays, inspect current time, or calculate any metric.

`STATIC OBSERVATION WINDOW != OBSERVED PATH`

`CALCULATION CONVENTION != CALCULATION ENGINE`

D05 owns retained observations. D06 owns current time/calendar/schedule resolution.
D07 owns realized/implied metric calculation and valuation methodology.

## 5. Typed strikes

`VarianceStrike` and `VolatilityStrike` are distinct typed values even when the same
numeric magnitude is supplied. Both are finite, non-negative contractual values.

`CorrelationStrike` is finite and restricted to the closed interval `[-1, 1]`.

No strike wrapper represents an observed or calculated current value.

## 6. Variance swap semantics

`VarianceSwapTerms` retains:

- derivative terms identity;
- instrument economic identity;
- distinct reference economic identity;
- observation terms;
- typed variance strike;
- explicit variance amount as UMI-05 `DerivativeNotional`;
- optional, separately retained vega notional;
- static settlement target/date;
- evidence reference.

Variance amount and optional vega notional are deliberately separate fields. QORE does
not infer one from the other and does not execute a variance/vega conversion formula.

The product is not forced into generic UMI-05 `SwapContractTerms`, because doing so
would falsely manufacture two directional legs for a product represented by the
primary standard as a single netted leg.

## 7. Volatility swap semantics

`VolatilitySwapTerms` retains:

- derivative terms identity;
- instrument economic identity;
- distinct reference economic identity;
- observation terms;
- typed volatility strike;
- mandatory vega notional;
- static settlement target/date;
- evidence reference.

No realized volatility, implied volatility, price, Greek or payout is calculated.

## 8. Correlation swap semantics

`CorrelationSwapTerms` retains:

- derivative terms identity;
- instrument economic identity;
- at least two explicit constituent references;
- each constituent's positive finite contractual weight;
- observation terms;
- bounded correlation strike;
- explicit correlation amount;
- static settlement target/date;
- evidence reference.

Constituent identities must be unique and the correlation-swap instrument itself may
not be used as one of its own references.

Weights are deliberately **not normalized to sum to one**. Primary and market contracts
may preserve scaling conventions, and D04 must not invent a universal normalization
law without evidence. What matters here is preserving the supplied contractual weights
and preventing silent constituent collapse.

This owner does not calculate pairwise correlations, basket correlation, realized
correlation or dispersion.

## 9. Settlement boundary

`VolatilitySettlementTerms` retains only settlement economic identity and settlement
date. Settlement date may equal the observation-end date but cannot precede it.

The settlement identity is not forced to equal the unit identity of every contractual
amount; doing so would create an unverified universal law. Downstream settlement and
cash mutation remain D11 authority.

`STATIC SETTLEMENT TERMS != SETTLEMENT MUTATION`

## 10. Authority map

| Material | Authority |
|---|---|
| Generic derivative IDs/notional/evidence | UMI-05 / D04 |
| Variance/volatility/correlation static contract terms | this bounded UMI-14 owner |
| Market observations/fixings | D05 |
| Current calendars/time/schedule resolution | D06 |
| Realized/implied variance/volatility/correlation | D07 / UMI-10 |
| Pricing, valuation, calibration, Greeks | D07 |
| Current holdings/exposure/capacity | D08 / D09 |
| Order/execution | D10 |
| Settlement/cash/position mutation | D11 |

## 11. Fail-closed invariants

- typed code wrappers reject raw/invalid strings;
- strikes require finite `Decimal` values;
- variance/volatility strikes reject negatives;
- correlation strike remains within `[-1, 1]`;
- observation dates are exact `date` values and strictly forward;
- expected observation count uses strict positive-int semantics;
- settlement cannot precede observation end;
- instrument/reference identities remain distinct for variance/volatility swaps;
- correlation requires at least two typed, unique constituents;
- correlation constituent weights are finite and positive;
- correlation instrument cannot be its own constituent;
- frozen/slotted deterministic values;
- deterministic `logical_values()`;
- no wall clock, UUID generation, random state, provider or secret material.

## 12. Explicit exclusions

This candidate implements no:

- variance option;
- dispersion strategy;
- volatility/correlation surface;
- VIX or other index methodology;
- Greeks;
- realized variance/volatility/correlation calculation;
- implied-volatility calculation;
- pricing/valuation/calibration;
- current market observation or fixing retrieval;
- provider symbol, adapter or SDK;
- order/execution;
- settlement mutation;
- portfolio/risk calculation;
- UMI-12 conformance-harness changes;
- productive Cloud or real-capital authority.

## 13. Gate discipline

This candidate is preparatory because Lane 3 / PR #376 remains the integration-order
gate.

Required eventual sequence:

`PREPARATORY CANDIDATE -> EXACT-HEAD CI -> FREEZE -> WAIT FOR PRECEDING LANES -> SYNC TO NEW CERTIFIED MAIN -> NEW EXACT SHA -> FULL CI -> INDEPENDENT REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE CERTIFICATION`

`OBSERVATION != TRADEABLE CONTRACT`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT EXACT-HEAD REVIEW -> NO MERGE`

`NO LANE-ORDER BYPASS`
