# VT31 NAS100 — Architect A Admission Baseline + Abstain Forensics 001

**Owner:** Sergio Meza  
**Branch:** `agent/vt31-edge-entry-reasoning-a-001`  
**Status:** CONSUMED-EVIDENCE RESEARCH / NO POLICY PROMOTION

## 1. Reactivation

Architect A had remained at checkpoint:

`b00b28868e7140aeff6c835669f84932ea774f3e`

with no new branch workflows.

The branch has now been reactivated with two edge-only measurements:

1. Pure admission baseline:
   - workflow `37444293991`
   - result: SUCCESS
   - head tested: `ad8ac05f20a1c6825e84f730fec0262ebebcbd88`

2. First-hard-ABSTAIN counterfactual:
   - workflow `37444761376`
   - result: SUCCESS
   - head tested: `f6dae75cf27625b26521afe4223071770e2b1642`

No sizing, leverage, compounding, capital weighting, portfolio allocation,
fresh holdout, LIVE or real-capital authority was used.

## 2. Pure admission baseline

The baseline preserves Architect A's existing causal pre-entry reasoning but
forces every admitted trade to use the same source structural boundary exit.
This removes target/position-management optimization as an explanation.

### R5

- trades: 54
- PF: `2.388390`
- mean: `+0.777755R`
- total: `+41.9988R`
- DD: `11.75R`
- MC positive terminal: `90.34%`
- MC p95 DD: `24.04R`

### R6

- trades: 37
- PF: `2.423350`
- mean: `+1.059819R`
- total: `+39.2133R`
- DD: `13.9444R`
- MC positive terminal: `86.87%`
- MC p95 DD: `22.51R`

### R8

- trades: 33
- PF: `2.492999`
- mean: `+0.963663R`
- total: `+31.8009R`
- DD: `9.7619R`
- MC positive terminal: `87.20%`
- MC p95 DD: `17.05R`

### Recent consumed

- trades: 48
- PF: **`1.099959`**
- mean: **`+0.075073R`**
- total: `+3.6035R`
- DD: **`12.8341R`**
- MC positive terminal: **`54.79%`**
- MC p95 DD: **`28.30R`**

The current A reasoning is therefore historically strong but not regime-robust
enough in the recent consumed block.

## 3. Admission selectivity is already high

Recent consumed status counts include:

- terminal: 48
- intelligence ABSTAIN: 338
- intelligence ABSTAIN after source invalidation: 5
- WAIT observations: 828
- no source setup: 56
- source not executable: 45

This falsifies the idea that the recent weakness exists because Architect A
simply admits too many states.

The brain is already highly selective.

## 4. First-hard-ABSTAIN counterfactual

The counterfactual simulates the already-formed setup at the first hard ABSTAIN
using the same source structural exit. Future outcomes are research labels only
and never runtime inputs.

Denied terminal population:

| Fold | Sample | PF | Mean R | DD |
|---|---:|---:|---:|---:|
| R5 | 236 | 1.0140 | +0.0112R | 51.82R |
| R6 | 227 | 1.3322 | +0.2602R | 36.50R |
| R8 | 180 | 0.9038 | -0.0764R | 46.73R |
| consumed | 216 | 0.8663 | -0.1050R | 51.71R |

Most importantly:

**cross-fold positive denied classes = 0**

Therefore there is no evidence supporting broad relaxation of current ABSTAIN
authority.

## 5. Stable protective denied classes

Examples of denied classes negative across all four burned folds include:

### Breaker + H1 bearish + late state

Mean R:

- R5: `-1.05R`
- R6: `-0.925R`
- R8: `-0.925R`
- consumed: `-0.85R`

### Breaker + H1 bearish + no reference-liquidity state by cutoff

Negative 4/4.

### Breaker + H1 mixed + late state

Negative 4/4.

### Order Block + H1 mixed + CURRENT_PATH_NOT_COMPRESSED

Mean R:

- R5: `-1.05R`
- R6: `-1.05R`
- R8: `-1.05R`
- consumed: `-1.05R`

This is an especially strong causal protection witness.

### FVG + H1 bullish + noncompressed reference outside low-DD gate

Negative 4/4.

### Breaker + late state, independent of H1 subclass

Negative 4/4.

## 6. Interpretation

The next repair must **not** be:

- weaken all ABSTAIN rules;
- reintroduce same-source fallback;
- manufacture more trades;
- use sizing to compensate for weak admissions;
- add capital engineering.

The dominant defect is now narrower:

**Among the small population that already passes full pre-entry reasoning,
recent consumed still contains false-positive EXECUTE states that did not exist
with the same economics in prior folds.**

The next research target is therefore multivariate admitted-state attribution:

- entry family;
- H1/H4;
- volatility regime;
- latest causal structure;
- cash-open / premarket context;
- risk/reference geometry;
- planned target R;
- confirmation latency;
- entry-evidence freshness;
- reclaim age;
- conjunctions of the above.

Special emphasis must be placed on classes that are positive in R5/R6/R8 but
flip sign or PF below 1 in recent consumed.

Those are regime-generalization defects, not reasons for a universal ban.

## 7. Current governance

Nothing in these results authorizes:

- policy promotion;
- candidate freeze;
- fresh holdout;
- merge;
- LIVE;
- real capital;
- production.

The current A runtime policy remains unchanged until a causal cross-fold
admitted-state refinement survives independent consumed testing.
