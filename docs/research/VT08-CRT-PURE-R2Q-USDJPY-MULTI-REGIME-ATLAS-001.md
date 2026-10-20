# VT08 CRT PURE — R2-Q USDJPY SIX-YEAR MULTI-REGIME ATLAS 001

**Identity:** `VT08_CRT_PURE_R2Q_USDJPY_MULTI_REGIME_ATLAS_001`  
**Workflow run:** `35844460458`  
**Evidence HEAD:** `d5caf70542ccb83e96d855894e7af0a95cb83c5a`  
**Window:** `2020-09-21 -> 2026-09-21`  
**Status:** COMPLETE / ONE CROSS-REGIME STATE FOUND

## 1. Objective

R2-N falsified the local C1-body solution. R2-Q therefore expanded the state model to
short/medium/long pre-C3 volatility, trend efficiency, drift and parent geometry across
three non-overlapping 2Y blocks.

No filter was promoted automatically.

## 2. Control

Full 6Y:
- 306 trades
- PF 0.88679637
- -13.18946019R
- DD 28.55452472R

2020-2022:
- 112 trades
- PF 0.99936900
- -0.02414470R

2022-2024:
- 90 trades
- PF 0.58459292
- -17.32565723R

2024-2026:
- 104 trades
- PF 1.11385968
- +4.16034174R

## 3. Coherent cross-regime bucket

Only one frozen bucket satisfied:

- at least 8 trades in every 2Y block;
- positive R in every 2Y block.

`EFF5D_0_10_TO_0_20`

Full 6Y:
- 45 trades
- PF 2.05089948
- +12.06917586R
- mean +0.26820391R
- DD 4.03448045R

2020-2022:
- 13 trades
- PF 1.64627464
- +2.55823528R

2022-2024:
- 16 trades
- PF 1.34383815
- +1.47267670R

2024-2026:
- 16 trades
- PF 3.47855180
- +8.03826388R

## 4. Interpretation

The current evidence supports a regime hypothesis:

USDJPY Model #1 behavior is materially better when the preceding five-day market path has
moderate directional efficiency rather than being highly noisy or strongly one-directional.

This is an engineering regime hypothesis, not a Romeo rule.

## 5. Next validation

Freeze a primary candidate:

`EFF5D 0.10 <= efficiency < 0.20`

and small predeclared neighborhoods before reading 2018-2020.

The primary candidate must survive independently; a neighboring band cannot replace a
failed primary after results.

## 6. Governance

- no promotion yet;
- no certification;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
