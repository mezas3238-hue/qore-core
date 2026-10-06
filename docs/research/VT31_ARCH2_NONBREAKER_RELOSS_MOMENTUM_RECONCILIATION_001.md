# VT31 NAS100 — Non-Breaker Reloss Momentum Fold Reconciliation 001

**Owner:** Sergio Meza  
**Status:** OFFICIAL AGGREGATE PASS / SUPPORTED CONSUMED RESEARCH WITNESS  
**Frozen experiment head:** `8de1d5ee87979664db76d9b4ce7031da555ac4a9`  
**Run:** `37398899265`

## Predeclared rule

`NONBREAKER_RELOSS_MOMENTUM_SWING_ONCE`

Breaker trades are unchanged.

Only Fair Value Gap / Order Block trades may improve the stop once when:

- a confirmed M1 protective swing exists;
- momentum has stopped progressing in trade direction;
- closed price has re-lost the source confirmation structure;
- the stop improvement is effective next M1;
- the stop never widens.

No R, sizing, volume, leverage, compound or capital weighting is a runtime
input.

## Immutable GitHub fold artifacts

- R5 artifact `11384539181`
  - digest `sha256:a99a7d0b46393f56f22ead0e58510a5cc976a91bdeaaf76d90de56b9c2b88048`
- R6 artifact `11385170028`
  - digest `sha256:47469ecb2aca6ca5680c62bbd7d7d37945c55c4bc1cc2863623c5b7780b637ee`
- R8 artifact `11384499268`
  - digest `sha256:22d385d7df36c25b5cafbb22e346fefbe1f2097b7b54f851fdc303d44e562112`
- recent consumed 2Y artifact `11384333514`
  - digest `sha256:8ae53f2b461b15c578038bbf7c19d113c794e98a0b434c953b32a1f8202db88c`

All four fold jobs completed SUCCESS including governance gates.

## Fold results after 0.05R evaluation friction

| Fold | Baseline PF | Candidate PF | Baseline mean | Candidate mean | Baseline DD | Candidate DD | Changed | Winner count / R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R5 | 1.9169 | **2.0186** | +0.7488R | **+0.7899R** | 12.60R | **12.30R** | 7 | 100% / 100% |
| R6 | 2.3035 | **2.3035** | +1.1097R | **+1.1097R** | 12.74R | **12.74R** | 0 | 100% / 100% |
| R8 | 2.6708 | **2.8247** | +1.3291R | **+1.3724R** | 11.66R | **10.32R** | 3 | 100% / 100% |
| recent 2Y | 1.0464 | **1.1326** | +0.0406R | **+0.1077R** | 13.83R | **13.53R** | 5 | 100% / 100% |

Totals:

- 15 trades changed;
- 0 Breaker trades changed;
- every changed trade was FVG or Order Block;
- no changed trade degraded;
- no baseline winner became a loser;
- winner count preservation = 100% in every fold;
- winner-R preservation = 100% in every fold.

## Temporal gate reproduction

The exact aggregate gate logic was reproduced over the four immutable artifact
JSONs.

Every reported half-year passes:

- same sample;
- total R non-degrading;
- mean R non-degrading;
- PF non-degrading;
- DD non-degrading.

Notable recent 2Y blocks:

### 2023H1

- PF 1.1745 -> **1.2186**
- DD 6.30R -> **6.00R**

### 2023H2

- PF 1.0611 -> **1.1162**
- DD 5.38R -> **4.86R**

### 2024H1

- PF 1.9864 -> **2.4746**
- DD 6.30R -> **4.20R**

2022H2 and 2024H2 are unchanged.

R8 2017H2 also improves:

- total -10.50R -> **-9.27R**
- DD 10.50R -> **9.27R**

## Deterministic frozen-gate adjudication

Reproduction of the workflow aggregate contract:

- R5: PASS
- R6: PASS
- R8: PASS
- recent consumed 2Y: PASS
- cross-fold survivor: **TRUE**
- changed trade total: **15**
- reproduced adjudication:
  **`SUPPORTED_CONSUMED_RESEARCH_WITNESS`**

The GitHub aggregate job `112063764667` completed **SUCCESS**.

Official aggregate artifact:

- artifact `11384966427`;
- digest `sha256:bb5c6f9d33b042f3c3f8c910d13820ab9cfe82af7515104a046ac37ef7d419c3`.

Official aggregate adjudication:

`SUPPORTED_CONSUMED_RESEARCH_WITNESS`

Official fields:

- `cross_fold_survivor = true`;
- `changed_trade_count_total = 15`;
- runtime R decision authority = false;
- runtime volume decision authority = false;
- fresh holdout opened = false;
- candidate frozen = false;
- policy promoted = false.

## Certification meaning

This mechanism is a valid consumed-evidence research witness, but it is **not**
a certified trader and is not sufficient to certify VT31:

- recent 2Y PF rises only to 1.1326, below Owner PF gates;
- recent 2Y DD remains 13.53R, above the <=10R target;
- admission quality remains the primary blocker;
- expanded-reference and non-Breaker entry defects remain Architect-1 work.

No policy promotion, candidate freeze, fresh holdout, merge, LIVE, real capital
or production authority is granted.
