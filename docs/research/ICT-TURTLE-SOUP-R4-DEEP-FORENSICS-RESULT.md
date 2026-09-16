# ICT Turtle Soup R4 — deep forensics result

Date: 2026-09-16

Parent identity:
`ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL`

Parent run: `35052152001`
Parent software SHA: `8c076a714098704237a97fe992e2e01bf9c69bf0`
Parent aggregate artifact: `10429651883`
Parent holdout: `[2018-07-02T21:00:00Z, 2020-07-01T21:00:00Z)` — CONSUMED.

This document is descriptive post-result forensics only. It does not mutate R4 and does not authorize any filter or parameter inferred from the consumed result.

## 1. Parent result

- 298 trades
- 112 gross winners / 186 gross losers
- gross PF `0.9005586880`
- gross total `-15.9010560985R`
- primary PF `0.8180089360`
- primary total `-30.8010560985R`
- same-window legacy-R3-like signals: 2,424
- R4 frequency reduction: 87.7063%

Adjudication: `R4_REJECTED_FOR_ADVANCEMENT`.

## 2. Exit decomposition

| Exit family | Count | Gross total R | Primary total R |
|---|---:|---:|---:|
| stop | 148 | -148.000 | -155.400 |
| target | 64 | +102.997 | +99.797 |
| gap-target-capped | 1 | +1.246 | +1.196 |
| daily-c3-close | 85 | +27.856 | +23.606 |

Losses are dominated by the stop cohort. Daily-C3 time exits are positive in aggregate and are not the main failure family.

## 3. Stop-path forensics

Stopped cohort: 148.

Conservative pre-stop MFE uses only M5 bars strictly before the stop-containing M5.

- median pre-stop MFE: `+0.3056R`
- reached `+0.25R` before stop: `58.11%`
- reached `+0.50R`: `40.54%`
- reached `+1.00R`: `16.89%`

Using only M5 bars strictly after the stop-containing bar through the same Daily C3:

- recovered original entry: `53.38%`
- later reached `+0.25R`: `43.24%`
- later reached `+0.50R`: `39.19%`
- later reached `+1.00R`: `32.43%`
- later reached original target: `12.84%`
- median final Daily-C3 close outcome: `-1.1291R`

Adjudication: `STOP_PREMATURE_AS_SOLE_CAUSE = NOT_SUPPORTED`.

Many stops first react favorably and later retest, but most do not recover to the original target inside the intended Daily-C3 lifecycle. A wider stop is therefore not authorized.

## 4. Target continuation

Target cohort including one favorable gap-target: 65.

After the target-containing M5 through the remaining Daily C3:

- median additional favorable excursion: `+1.1570R`
- additional `+0.25R`: `89.23%`
- additional `+0.50R`: `67.69%`
- additional `+1.00R`: `52.31%`

Adjudication: `NEAREST_DAILY_DOL_IS_OFTEN_FIRST_OBJECTIVE_NOT_FINAL_ENDPOINT = SUPPORTED`.

This does not authorize a new runner or partial-management rule under R4. TTrades independently documents short-term targets plus higher-timeframe runners; a different management contract would require a new identity.

## 5. Time exits

Daily-C3-close exits: 85.

- median gross: `+0.06234R`
- positive: `55.29%`

Adjudication: `DAILY_C3_LIFECYCLE_AS_PRIMARY_FAILURE = NOT_SUPPORTED`.

## 6. Winner-vs-loser pre-entry diagnostics

Cliff's delta is descriptive only.

| Feature | Winner median | Loser median | Cliff's delta |
|---|---:|---:|---:|
| H4 reclaim depth | 0.5154 | 0.3860 | +0.1736 |
| Daily reclaim depth | 0.4643 | 0.3924 | +0.1043 |
| H4 sweep depth | 0.2205 | 0.2141 | -0.0509 |
| Daily sweep depth | 0.1962 | 0.1889 | +0.0096 |
| M15 CISD latency | 120m | 135m | -0.0144 |
| CISD to entry | 120m | 105m | +0.0144 |
| Daily H1 CISD latency | 840m | 900m | -0.0740 |
| DOL age | 44h | 56h | -0.0368 |
| risk / H4-C2 range | 0.7252 | 0.7104 | +0.0918 |
| projected R | 1.9455 | 2.7468 | -0.2713 |

The strongest source-relevant pre-entry separation is rejection/closure quality, not sweep size, CISD clock latency, DOL age, or projected R.

No numeric reclaim threshold is authorized.

## 7. Projected-R monotonicity

Projected-R deciles are strongly non-monotonic. Gross means from the lowest to highest decile were approximately:

`-0.111, +0.076, +0.022, -0.402, +0.147, -0.215, +0.226, -0.020, +0.197, -0.460R/trade`.

Adjudication: `MINIMUM_PROJECTED_R_AS_REPAIR = CONTRADICTED`.

## 8. Temporal stability

Primary results by substantive quarter change sign repeatedly:

- 2018Q3: `-6.114R`
- 2018Q4: `-13.959R`
- 2019Q1: `-8.237R`
- 2019Q2: `+5.790R`
- 2019Q3: `-0.569R`
- 2019Q4: `+6.338R`
- 2020Q1: `-3.632R`
- 2020Q2: `-11.139R`

Adjudication: `UNIFORM_REGIME_EDGE = NOT_SUPPORTED`.

No quarter/regime may be selected retrospectively.

## 9. Cross-symbol diagnostics

All seven leave-one-symbol-out primary totals remain negative. No single symbol removal repairs the aggregate result.

Entry clusters are non-monotonic: two-pair clusters happened to be positive while singletons and several larger clusters were negative. This does not authorize a cluster-size filter.

Adjudication:

- `SINGLE_PAIR_CAUSE = NOT_SUPPORTED`
- `SIMPLE_CLUSTER_FILTER = NOT_SUPPORTED`

## 10. Tail concentration

- top-1 winner share of gross gains: `5.68%`
- top-5: `18.74%`
- top-10: `30.70%`
- top-10 loss share: `6.25%`

Adjudication: the result is not explained by one or two extreme winners or losers.

## 11. Source re-audit after forensics

A source re-audit found an important naming distinction.

TTrades' standard Fractal Model explicitly supports:

higher-timeframe Candle 2/3 closure -> aligned lower-timeframe CISD -> confirmed/protected swing -> continuation.

This is the family R4 actually implemented at Daily/H1 and H4/M15.

However, TTrades separately defines **Ideal Formation** as a stricter family in which the Candle 2 or Candle 3 closure itself simultaneously creates a protected swing by closing through the opposing same-chart candle series responsible for the swing. TTrades describes Ideal Candle 2 as the strongest version; Candle 3 is then the expected expansion candle.

Primary TTrades sources:

- `https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/`
- `https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/`
- `https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/`
- `https://ttrades.com/why-your-continuations-fail-order-blocks-cisd-explained/`

Therefore:

`R4_IMPLEMENTATION = VALID_STANDARD_FRACTAL_MODEL`

but

`R4_IDENTITY_LABEL_IDEAL_C2 = TOO_STRONG / NOMENCLATURE_DRIFT`.

This is not a reason to rewrite R4. It creates a legitimate new source-derived research family that must receive a new candidate identity and different untouched evidence.

## 12. Descriptive strict-Ideal census inside consumed R4 trades

Using a conservative same-timeframe interpretation solely to understand the naming drift:

- R4 trades with Daily C2 body aligned to reversal direction: 217 / 298
- R4 trades whose Daily C2 also closes through the immediately preceding same-timeframe opposing series: 37 / 298
- R4 trades whose H4 C2 satisfies that same strict same-timeframe Ideal interpretation: 61 / 298
- R4 trades satisfying both Daily and H4 strict same-timeframe Ideal conditions: 5 / 298

These are **census counts only**. Their P&L is not an authorization to choose or reject the Ideal Formation family.

## 13. Root-cause adjudication

1. `SELECTIVITY_CORRECTION_SUCCEEDED` — **STRONGLY SUPPORTED**.
2. `STOP_PREMATURE_AS_SOLE_CAUSE` — **NOT SUPPORTED**.
3. `REVERSAL_CONFIRMATION_NOT_PERSISTENT` — **STRONGLY SUPPORTED**.
4. `NEAREST_DAILY_DOL_AS_FINAL_ENDPOINT_TOO_LOCAL` — **SUPPORTED FOR MANAGEMENT RESEARCH**.
5. `C2/CISD_QUALITY_UNDERFORMALIZED` — **SUPPORTED / SOURCE-PLAUSIBLE**.
6. `CISD_CLOCK_LATENCY_AS_CAUSE` — **NOT SUPPORTED**.
7. `DOL_AGE_AS_SIMPLE_CAUSE` — **NOT SUPPORTED**.
8. `PROJECTED_R_THRESHOLD_AS_REPAIR` — **CONTRADICTED**.
9. `PAIR_OR_SESSION_FILTER_AS_REPAIR` — **NOT AUTHORIZED / NOT SUPPORTED**.
10. `R4_WAS_NOT_TRUE_IDEAL_FORMATION_FAMILY` — **SOURCE AUDIT CONFIRMED**.

## 14. Governance conclusion

R4 remains rejected and immutable.

The only legitimate next mechanics research is source-derived and must use a new identity. The principal source-derived candidate family is the authentic TTrades Ideal Formation, potentially combined with the existing top-down Daily/H4 alignment, without using any numeric threshold learned from this holdout.

The 2018-2020 evidence is consumed permanently for this research line.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
