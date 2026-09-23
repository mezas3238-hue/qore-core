# VT08 CRT PURE — R2-Z USDJPY EIGHT-YEAR ATLAS 001

**Identity:** `VT08_CRT_PURE_R2Z_USDJPY_EIGHT_YEAR_ATLAS_001`  
**Workflow run:** `35850726850`  
**Window:** `2018-09-21 -> 2026-09-21`  
**Status:** COMPLETE / BLOCK-COHERENT BUT NOT ANNUAL-STABLE

## 1. Control

Full 8Y:
- 405 trades
- PF 0.91285350
- -13.27037010R
- DD 29.29791972R

2Y blocks:
- 2018-2020: -0.08090991R
- 2020-2022: -0.02414470R
- 2022-2024: -17.32565723R
- 2024-2026: +4.16034174R

## 2. Only coherent 2Y bucket

`EFF5D_0_10_TO_0_20`

Full 8Y:
- 58 trades
- PF 1.93281204
- +14.88068864R
- DD 4.03448045R

2Y blocks:
- 2018-2020: 13 trades / PF 1.62927083 / +2.81151278R
- 2020-2022: 13 trades / PF 1.64627464 / +2.55823528R
- 2022-2024: 16 trades / PF 1.34383815 / +1.47267670R
- 2024-2026: 16 trades / PF 3.47855180 / +8.03826388R

## 3. Critical contradiction with R2-W

R2-W used the exact same primary band on 2018-2020 and split it annually.

That validation found:
- first year +3.95754299R
- second year -1.14603021R

Therefore:

- the bucket is robust at the 2Y-block level;
- it is **not** robust at the stricter annual-stability gate frozen before R2-W;
- R2-Z does not override or erase the R2-W failure.

## 4. Adjudication

Do not loosen the annual gate after seeing R2-Z.

The existing R2-Q feature family has found a genuine medium-horizon regime effect, but it
is insufficient by itself for USDJPY certification.

Next USDJPY research must explain the within-regime failure rather than move the
EFF5D threshold.

## 5. Governance

- no USDJPY candidate promoted;
- no certification;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
