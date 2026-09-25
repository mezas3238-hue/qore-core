# VT08 CRT PURE — R2-AC USDJPY WITHIN-REGIME FAILURE FORENSICS 001

**Identity:** `VT08_CRT_PURE_R2AC_USDJPY_WITHIN_REGIME_FAILURE_001`  
**Workflow run:** `35851773984`  
**Status:** COMPLETE / SINGLE-DIMENSION ABLATION SELECTED

Frozen parent regime:

`EFF5D 0.10 <= efficiency < 0.20`

Full 2018-2026 regime:
- 58 trades
- PF 1.93281204
- +14.88068864R
- DD 4.03448045R

Known bad annual slice:
- 2019-2020
- 10 trades
- PF 0.71349245
- -1.14603021R

R2-AC tested already-frozen pre-parent dimensions as explanations only.

Three single-bucket exclusions would make every consumed annual slice positive:

1. exclude `MANIP_0_10_TO_0_25`
   - residual 37 trades
   - +12.60040329R
   - but the removed bucket is +2.28028535R over full 8Y.

2. exclude `RECLAIM_0_25_TO_0_50`
   - residual 36 trades
   - +15.46613177R
   - removed bucket is -0.58544313R over full 8Y.

3. exclude 1D drift `OPPOSED`
   - residual 25 trades
   - +14.95848839R
   - materially lower density.

Adjudication:

`RECLAIM_0_25_TO_0_50` was selected as the only R2-AE hypothesis because it:

- uses one dimension;
- removes a globally negative bucket;
- repairs the consumed annual stability defect;
- preserves more density than the drift alternative;
- avoids deleting a globally profitable manipulation bucket.

This selection was frozen before the 2014-2018 validation window was opened.

No combination with other R2-AC clues is authorized.

No certification / VPS / DEMO / LIVE / production / real capital.
