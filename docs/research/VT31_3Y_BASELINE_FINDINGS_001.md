# VT31 NAS100 — OWNER 3Y BASELINE FINDINGS 001

**Date:** 2026-10-07  
**Owner:** Sergio Meza  
**Repository:** `mezas3238-hue/qore-core`  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## 1. Authority

This document records the first successful replay on the Owner-designated
single contiguous three-year VT31 base.

This supersedes R5/R6/R8 stitched economics as the current operating research
baseline.

Canonical base:

```text
BASE_ID = VT31_NAS100_OWNER_3Y_BASE_001
NAS100
2023-10-01 inclusive
2026-10-01 exclusive
1096 calendar days
```

The base is now consumed research/development evidence. It must not be called a
fresh independent certification holdout.

## 2. GitHub evidence

First successful 3Y Trader Lab:

```text
run      = 37569578605
head     = 8f91ee489d33c1fa0b90972270d4ac6c32fcca32
status   = SUCCESS
```

Canonical 3Y evidence artifact:

```text
artifact_id = 11459859004
name        = qore-vt31-nas100-owner-3y-base-v1
```

3Y replay/adjudication artifact:

```text
artifact_id = 11459439466
name        = qore-vt31-nas100-single-3y-trader-lab-8f91ee489d33c1fa0b90972270d4ac6c32fcca32
```

## 3. Current exact density

```text
market days                           936
eligible sessions                     769
current admitted trades                55
Owner target trades                   450
gap to target                         395
target fraction                    12.22%
```

Trades by year:

```text
2023 partial (Oct-Dec)   8
2024                    18
2025                    17
2026 partial (Jan-Sep)  12
```

The current stack is therefore far below the Owner's reasonable density target.

## 4. Attrition map

The specialist classified the 769 eligible sessions as:

```text
terminal structural trades                         79
no-fill                                            29
censored-fill-bar-path                             16
source-not-executable                              57
no-source-setup                                    86
intelligence-abstain                              496
intelligence-abstain-source-invalidated             6
-----------------------------------------------------
eligible sessions                                 769
```

Reasoning observations:

```text
ABSTAIN   502
EXECUTE   124
WAIT     1310 observation-level states
```

After the downstream Comparator-009 admission stack:

```text
structural terminal population = 79
admitted population            = 55
admission removals             = 24
```

The dominant density loss is therefore pre-entry cognitive abstention, not
missing data and not H4 plumbing.

## 5. Current 3Y economics — exact control

At 0.05R friction:

```text
trades              55
wins                11
losses              44
total R          +25.4956512133R
mean R           +0.4635572948R
profit factor       1.6326693583
max drawdown        21.3585957183R
max losing streak   23
payoff ratio         6.5306774333
```

Risk-adjusted:

```text
annualized Sharpe    0.5619175332
annualized Sortino   2.3569608716
```

Monte Carlo:

```text
positive terminal probability   0.8147
p95 max drawdown               27.5956317826R
```

Cost stress:

```text
0.10R friction PF = 1.5352101839
```

## 6. Hard-gate disposition

PASS:

- PF >= 1.50;
- expectancy >= +0.15R;
- payoff >= 1.20;
- Sortino >= 2.00;
- degraded 0.10R PF > 1.

FAIL:

- reasonable density >= 400 trades;
- observed DD <= 6R;
- Sharpe >= 1.50;
- Monte Carlo positive probability >= 0.90;
- Monte Carlo p95 DD <= 15R.

Therefore:

```text
VT31 CERTIFIED = FALSE
```

## 7. Drawdown episode

The dominant observed drawdown begins after the trade on:

```text
2024-05-07 — breaker LONG
```

and reaches the trough on:

```text
2025-11-20 — breaker SHORT
```

with:

```text
DD = 21.3585957183R
```

This episode must not be repaired with sizing or leverage. Only entry/exit edge,
causal cognition and methodology-native position management are permitted.

## 8. Immediate research implication

Current source-executable capacity inferred from session classification:

```text
eligible sessions          769
no source                   86
source not executable       57
source-executable days     626
```

To reach 450 trades using no more than one trade per source-executable day,
VT31 would need an effective conversion rate of approximately:

```text
450 / 626 = 71.88%
```

Current final conversion is:

```text
55 / 626 = 8.79%
```

This is why the next work is not small parameter tuning.

Required investigation order:

1. causal admission-ablation frontier;
2. true distinct-opportunity capacity audit;
3. determine whether one-trade-per-day capacity can physically reach ~450;
4. if not, measure genuine structural rearm / additional methodology-native
   Silver Bullet opportunity capacity;
5. economically replay only the causal density mechanisms that preserve edge;
6. simultaneously reduce DD toward <=6R.

## 9. Governance

Still forbidden:

- sizing rescue;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital weighting;
- outcome-aware entry;
- duplicate-signal density;
- artificial micro-entry splitting.

Current 3Y base only. No return to R5/R6/R8 operating folds.
