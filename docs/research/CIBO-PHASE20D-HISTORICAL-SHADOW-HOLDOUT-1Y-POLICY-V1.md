# CIBO Phase20D — Historical Shadow Holdout 1Y Policy V1

Status: **PASS / CONSUMED / SEALED**

Phase20D may satisfy its physical-time, population, lineage and temporal-fold
requirements through the fixed historical shadow envelope **2021-07-01 →
2022-07-01** instead of waiting 28 physical days.

The actual seven-lineage fully observed intersection inside that envelope is
**2021-09-23 05:00Z → 2022-06-29 09:00Z**.

## Frozen population gates

The shadow must demonstrate at least 80 decision epochs, 200 terminal candidate
outcomes, 28 calendar days, 20 distinct trading days, 7 lineages with at least
8 outcomes each, four contiguous folds, at least 40 outcomes per fold, at least
4 lineages per fold and 95% candidate-outcome coverage.

The immutable Phase19 population is expected to produce 775 decision epochs,
855 terminal outcomes, 214 trading days, 279 calendar-span days, 7/7 lineages,
minimum 45 outcomes in any lineage and folds of 216 / 216 / 213 / 210 outcomes
with 7/7 lineages in every fold. The workflow must reproduce these facts from
sealed artifacts; documentation alone cannot pass the gate.

## Provider-aware gates are not fabricated

The prior 60 selected-outcome and selected/baseline USD coverage requirements
are **deferred**, not declared passed, because exact historical provider
execution economics are not provable for this burned interval. Current cTrader
terms may not be projected backward and synthetic fills/slippage may not be
relabeled as realized execution.

A passing shadow closes the physical Forward-population wait and allows the
chain to continue to provider-aware Phase21 gates. It does not prove V3 USD
economic superiority by itself.

## Non-negotiable separation

- Evidence kind: `HISTORICAL_SHADOW_HOLDOUT`, never `FORWARD_OBSERVED`.
- Frozen V3 is not retuned.
- No future features or outcome-aware refit.
- Burned research reuse is owner-authorized for this shadow lane only.
- Final `CIBO_USD60_6M_HOLDOUT_2017H1_V1` remains
  **SEALED_UNTOUCHED**.
- No LIVE, production or real-capital authority is granted.


## Consumed evidence

GitHub Actions run `36857676494` completed **SUCCESS** on
`3c7e8c881fca6f18eab25152460bc96b5d329695`.

Artifact: `11160430022`  
Digest: `sha256:cb5991afd27d2b73f4854c4105699744e2aa3c173a58262305d37d4ad083ddce`

Observed result:

- 775 decision epochs;
- 855 terminal candidate outcomes;
- 214 distinct trading days;
- 279 calendar-span days;
- 7/7 lineages;
- minimum 45 outcomes in any lineage;
- four contiguous folds: 216 / 216 / 213 / 210 outcomes;
- 7/7 lineages in every fold;
- candidate-outcome coverage = 100%;
- physical 28-day Forward wait = **SATISFIED_BY_SHADOW**;
- final 2017H1 holdout = **SEALED_UNTOUCHED**.

This closes the Phase20D population/time/lineage/fold dependency. Provider-aware
selected economics and realized execution evidence remain separate downstream
gates and were not fabricated.
