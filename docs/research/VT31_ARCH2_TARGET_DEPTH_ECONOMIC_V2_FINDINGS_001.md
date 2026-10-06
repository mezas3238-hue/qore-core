# VT31 NAS100 — Target-Depth Economic V2 Findings 001

**Owner:** Sergio Meza  
**Status:** DOL2 PROMISING / NO SURVIVOR YET / DOL3 REJECTED  
**Workflow:** `37442469140` — SUCCESS  
**Head tested:** `c9e961939886693248184d82ac8a382d26b6e469`

## Critical correction

This run is the first V2 economic result in which full cognition actually
activated target extensions.

The earlier run `37441800341` is superseded as target-depth evidence because
its full-cognition variants activated zero extensions.

## DOL2 full-cognition results

### SOFT3_DOL2_FULL_COGNITION

Actual extensions across folds: 16.

Economic direction:

- PF non-degrading: **4/4**
- mean-R non-degrading: **4/4**
- DD non-degrading: 3/4
- winner floor: PASS all folds

Fold economics:

- R5 PF 1.9169 -> **1.9582**, mean 0.7488R -> **0.8012R**
- R6 PF 2.3035 -> **2.3469**, mean 1.1097R -> **1.1467R**
- R8 PF 2.6708 -> **2.9066**, mean 1.3291R -> **1.5166R**
- consumed PF 1.0464 -> **1.1392**, mean 0.0406R -> **0.1249R**

However consumed DD worsens:

- 13.8341R -> **16.80R**

and winner-count preservation in consumed is 87.5%.

Therefore it is not a research survivor under the frozen gate.

### SOFT5_DOL2_FULL_COGNITION

Actual extensions: 17.

- PF non-degrading: **4/4**
- mean-R non-degrading: **4/4**
- DD non-degrading: 3/4
- winner floor: PASS all folds

Economics:

- R5 PF 1.9169 -> **1.9834**
- R6 PF 2.3035 -> **2.4523**
- R8 PF 2.6708 -> **2.9157**
- consumed PF 1.0464 -> **1.1320**

Mean-R also improves 4/4.

Again consumed DD worsens to **16.80R**, and some historical half-years degrade.

Result: promising mechanism, not survivor.

## DOL3

Full-cognition DOL3 extension degrades too much winner preservation and DD.

Examples for SOFT5:

- consumed DD 13.83R -> 17.69R
- R6 DD 12.74R -> 17.25R
- R8 winner-R preservation ~75.4%

DOL3 is rejected for the current architecture.

## Mechanism interpretation

The DOL2 cognition is doing something economically real:

- actual extensions occur;
- PF and mean-R improve in all four folds;
- R6/R8 DD does not worsen;
- recent consumed expectancy improves substantially.

The remaining defect is extension downside protection / giveback, especially
in recent consumed evidence.

The correct repair is therefore **not**:

- reduce volume;
- shorten DOL2;
- globally cap R;
- abandon extension.

The next frontier will keep the same cognition-selected DOL2 and test
market-native protection after DOL1 acceptance:

- first confirmed improving M1 swing;
- two-confirmation M1 swing;
- protection active only from the next M1.

No future outcome label may select protection.

## Decision

Retain DOL2 full-cognition extension as a research mechanism.

Reject DOL3 for now.

Do not promote DOL2 until post-acceptance structural protection fixes DD and
temporal instability without sacrificing winner-R.

No fresh holdout, policy promotion, candidate freeze, merge, LIVE, or real
capital authority.
