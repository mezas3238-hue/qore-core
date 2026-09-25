# VT08 CRT PURE — BTCUSD FINAL FRESH FREEZE 001

**Fresh identity:** `VT08_CRT_PURE_R2Y_BTCUSD_FINAL_FRESH_001`  
**Fresh window:** `2017-09-21 -> 2018-09-21`  
**Status:** FROZEN BEFORE FRESH RESULTS

## 1. Consumed evidence

Both standalone factors survived unchanged across the already-consumed 2018-2026 history.

### BTC_BEARISH

8Y consumed:
- 331 trades
- PF 1.49124494
- +49.35394229R
- DD 8.77728808R
- losing streak 8
- positive in every consumed 2Y block

### BTC_REF2_PLUS

8Y consumed:
- 266 trades
- PF 1.57213030
- +36.14926100R
- DD 6.39114189R
- losing streak 6
- positive in every consumed 2Y block

R2-O block robustness also showed lower p95 resampled DD for REF2_PLUS than BEARISH.

## 2. Primary selection

The primary candidate is frozen as:

`BTC_REF2_PLUS_PRIMARY`

Reason:

- both candidates have long temporal continuity;
- REF2_PLUS has higher consumed PF;
- REF2_PLUS has lower observed DD;
- REF2_PLUS has shorter losing streak;
- REF2_PLUS retains meaningful density.

The selection rule is risk/quality first, not maximum consumed Total-R.

## 3. Challenger

Predeclared challenger:

`BTC_BEARISH_CHALLENGER`

It remains informative because it has greater density and also survived every consumed 2Y
regime.

The challenger **cannot replace a failed primary after fresh results are observed**.

## 4. Fresh gate

Frozen before fresh outcomes:

- minimum 12 trades over the 1Y fresh window;
- PF >= 1.05;
- total R > 0;
- max DD <= 12R;
- first half total R > 0;
- second half total R > 0.

The one-year fresh window is split at `2018-03-21`.

## 5. Interpretation rules

- Primary PASS: REF2_PLUS may advance to the next certification chain.
- Primary FAIL: REF2_PLUS is rejected for advancement.
- Challenger PASS with Primary FAIL does not automatically promote BEARISH.
- Both PASS: both retain independent evidence; primary priority remains unchanged.
- Both FAIL: BTC candidate research reopens.

No post-result threshold movement is allowed.

## 6. Governance

- methodology unchanged;
- R2-G competition unchanged;
- no VPS / DEMO / LIVE / production / real capital;
- PR remains DRAFT / UNMERGED;
- fresh validation does not itself equal final certification.
