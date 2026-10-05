# VT31 NAS100 — Architect B Early No-Progress Edge-Only Findings 001

**Status:** GLOBAL RULE FALSIFIED / POST-HOC SUBSTATE FOUND / NO POLICY PROMOTED  
**Owner:** Sergio Meza  
**Run:** `37380981555` — SUCCESS  
**Head tested:** `e087d106d8704fd86eb4b1d653386377c7150c85`

## 1. Certification basis

All results are:

- equal normalized structural R;
- no sizing;
- no leverage;
- no compounding;
- no capital weighting;
- no absolute volume advantage;
- no admission change;
- no fresh holdout.

## 2. Baseline vs 5M / 8M early no-progress

Early no-progress contract:

- after 5 or 8 fully closed M1 bars post-fill;
- MFE remains < +0.25R;
- checkpoint close <= -0.25R;
- if original stop/target has not already terminated the trade, exit at next M1
  open.

### R8

Baseline:

- 257 trades
- PF 0.99876
- mean -0.00096R
- total -0.246R
- DD 43.43R

5M:

- PF 1.00670
- mean +0.00512R
- total +1.315R
- DD 42.45R
- scratch count 7
- winner count preservation 97.62%
- winner-R preservation 99.60%

8M:

- PF 1.00113
- mean +0.00087R
- total +0.225R
- DD 42.96R
- scratch count 1
- winner preservation 100% / 100%

### R6

Baseline:

- 299 trades
- PF 1.58570
- mean +0.41949R
- total +125.43R
- DD 29.06R

5M:

- PF 1.54817
- mean +0.39077R
- total +116.84R
- DD 28.45R
- scratch count 11
- winner count preservation 92.86%
- winner-R preservation 97.17%

8M:

- PF 1.56446
- mean +0.40342R
- total +120.62R
- DD 28.51R
- scratch count 5
- winner count preservation 96.43%
- winner-R preservation 98.45%

R6 decisively rejects both global scratch policies because PF, mean R and total
R deteriorate.

### R5

Baseline:

- 328 trades
- PF 1.09384
- mean +0.06999R
- total +22.96R
- DD 61.30R

5M:

- PF 1.10875
- mean +0.08002R
- total +26.25R
- DD 58.76R
- scratch count 7
- winner preservation 100% / 100%

8M:

- PF 1.09456
- mean +0.07049R
- total +23.12R
- DD 61.14R
- scratch count 1
- winner preservation 100% / 100%

### Consumed 2Y

Baseline:

- 290 trades
- PF 0.74133
- mean -0.20047R
- total -58.14R
- DD 74.59R

5M:

- PF 0.75362
- mean -0.18783R
- total -54.47R
- DD 71.52R
- scratch count 9
- winner preservation 100% / 100%

8M:

- PF 0.74472
- mean -0.19694R
- total -57.11R
- DD 73.56R
- scratch count 2
- winner preservation 100% / 100%

## 3. Decision on global early scratch

- `SCRATCH_5M`: **REJECTED AS GLOBAL POLICY**
- `SCRATCH_8M`: **REJECTED AS GLOBAL POLICY**

Reason: neither is a cross-fold non-degrading improvement. R6 loses too much
winner edge.

## 4. Why R6 deteriorates

The harmful 5M scratches are not ordinary losing trades. They include trades
whose baseline later reached structural target or finished positive.

Examples in R6:

- 2018-07-24: baseline +2.629R -> scratch -0.258R
- 2018-11-13: baseline +2.815R -> scratch -0.422R
- 2019-08-29: baseline +1.806R -> scratch -0.280R
- 2020-06-16: baseline +2.544R -> scratch -0.634R

Therefore "no progress in five minutes" is not itself thesis invalidation.

## 5. Cross-fold cognition diagnostic

New diagnostic authority:

`scripts/vt31_nas100_edge_only_early_no_progress_cross_fold_v1.py`

It groups only scratch-changed trades by causal fields already available in the
entry cognition.

Among single-field states appearing in all four folds, one state has positive
delta 4/4:

`last_structure_event_family == reference-liquidity-sweep`

Changed-trade evidence:

| Fold | Changed | Mean delta | Total delta | Harmful |
|---|---:|---:|---:|---:|
| consumed | 2 | +0.6854R | +1.3708R | 0 |
| R5 | 2 | +0.4722R | +0.9444R | 0 |
| R6 | 3 | +0.4815R | +1.4445R | 0 |
| R8 | 1 | +0.2703R | +0.2703R | 0 |

This state was discovered after reading consumed outcomes and is therefore
**post-hoc**. It is not eligible for direct runtime promotion.

## 6. Whole-population diagnostic if only reference-sweep scratches are changed

For research attribution only, replacing baseline outcomes only on those
already-burned reference-sweep 5M scratch events yields:

| Fold | PF baseline | PF diagnostic | DD baseline | DD diagnostic |
|---|---:|---:|---:|---:|
| consumed | 0.74133 | 0.74588 | 74.59R | 73.21R |
| R5 | 1.09384 | 1.09807 | 61.30R | 60.36R |
| R6 | 1.58570 | 1.59647 | 29.06R | 28.66R |
| R8 | 0.99876 | 1.00012 | 43.43R | 43.16R |

Every touched half-year is non-degrading in the burned evidence.

This is useful as a mechanism clue, not as validation.

## 7. Interpretation

The evidence rejects:

> "If VT31 has not progressed after five minutes, exit."

The narrower causal hypothesis is:

> "If the latest pre-entry structural event was a reference-liquidity sweep,
> and the admitted trade then shows almost no favorable excursion and closes
> materially adverse after five complete M1 bars, the specific liquidity thesis
> may have failed."

That hypothesis now needs a predeclared independent test before promotion.

## 8. Certification consequence

Even the best management diagnostics do not bring the current admitted
population close to the Owner certification gates.

Therefore the primary certification blocker remains **entry/admission edge**,
not sizing and not capital management.

No runtime policy, candidate freeze, fresh holdout, merge, LIVE or production
authority is granted.
