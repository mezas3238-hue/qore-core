# VT08 CRT PURE — R2-O BTCUSD BLOCK ROBUSTNESS 001

**Identity:** `VT08_CRT_PURE_R2O_BTCUSD_BLOCK_ROBUSTNESS_001`  
**Workflow run:** `35844132171`  
**Evidence HEAD:** `f5d8426c158b9d9969a2aca03511475b20cc7c73`  
**Status:** COMPLETE / TWO ADVANCING CANDIDATES RETAIN STATISTICAL ROBUSTNESS

## 1. Design

R2-O reuses the deterministic circular-block draw stream from QORE Research.

Frozen before results:

- 5,000 resamples per policy;
- block lengths 2 / 4 / 8;
- deterministic seeds derived from base seed 20260923;
- BTC_BEARISH;
- BTC_BODY_GE_050;
- BTC_REF2_PLUS.

No qualification threshold or automatic ranking was imposed.

R2-P subsequently falsified BTC_BODY_GE_050 on independent historical evidence, so that
candidate is retained here as characterization only and does not advance.

## 2. BTC_BEARISH

Source:

- 188 trades
- +21.09040959R
- observed DD 8.77728808R

Positive-terminal fraction:

- block 2: 0.9248
- block 4: 0.9332
- block 8: 0.9508

Terminal-R p05:

- block 2: -3.01350563R
- block 4: -2.34704950R
- block 8: +0.16038702R

p95 max DD:

- block 2: 17.71656694R
- block 4: 17.23121504R
- block 8: 16.66997833R

Interpretation:

The candidate retains a high positive-terminal frequency but still has a negative lower
5% terminal tail under shorter blocks and materially larger resampled drawdown than the
observed chronology.

## 3. BTC_REF2_PLUS

Source:

- 159 trades
- +16.57627409R
- observed DD 6.39114189R

Positive-terminal fraction:

- block 2: 0.9560
- block 4: 0.9508
- block 8: 0.9394

Terminal-R p05:

- block 2: +0.40419102R
- block 4: +0.07766400R
- block 8: -1.15051657R

p95 max DD:

- block 2: 11.90880161R
- block 4: 13.15266843R
- block 8: 13.23747167R

Interpretation:

REF2+ has lower block-resampled drawdown than BEARISH and keeps roughly 94-96% positive
terminal probability across the frozen block family.

## 4. BTC_BODY_GE_050

Block robustness was statistically respectable, but R2-P independently failed this factor
because 2021-2022 was negative.

Therefore it does not advance regardless of the R2-O resampling result.

## 5. Adjudication

The advancing standalone BTC candidates remain:

- BTC_BEARISH
- BTC_REF2_PLUS

R2-O does not choose a winner and does not authorize combining them.

The next evidence chain is earlier historical validation followed by a preserved final
fresh BTC window.

## 6. Governance

- certification FALSE;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
