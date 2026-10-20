# VT08 CRT PURE — R2-X AUDUSD SIX-YEAR MULTI-REGIME ATLAS 001

**Identity:** `VT08_CRT_PURE_R2X_AUDUSD_MULTI_REGIME_ATLAS_001`  
**Workflow run:** `35850451195`  
**Evidence HEAD:** `75692aa30270f3bf8bd8991ee598d55bdc23ea29`  
**Window:** `2020-09-21 -> 2026-09-21`  
**Status:** COMPLETE / ONE CROSS-REGIME STATE FOUND

## 1. Control

Full 6Y:
- 339 trades
- PF 0.95352386
- -5.63378781R
- DD 20.95951948R

By 2Y block:
- 2020-2022: 123 trades / PF 0.91093633 / -4.04336795R
- 2022-2024: 101 trades / PF 0.95575856 / -1.47945647R
- 2024-2026: 115 trades / PF 0.99738169 / -0.11096339R

The broad AUDUSD control remains negative in every block.

## 2. Only coherent positive bucket

`EFF1D_0_10_TO_0_20`

Full 6Y:
- 123 trades
- PF 1.37145125
- +13.64694272R
- mean +0.11095075R
- DD 5.29896246R
- losing streak 5

2020-2022:
- 40 trades
- PF 1.45652078
- +5.86755720R
- DD 3.59653339R

2022-2024:
- 41 trades
- PF 1.09749480
- +1.19842844R
- DD 5.29896246R

2024-2026:
- 42 trades
- PF 1.56759177
- +6.58095708R
- DD 3.63732912R

## 3. Interpretation

The data supports one engineering regime hypothesis:

AUDUSD Model #1 behavior is materially better when the preceding one-day path has
moderate directional efficiency:

`0.10 <= efficiency_1d < 0.20`.

This is not a Romeo rule. It is a QORE market-state gate discovered with the same
pre-parent feature family already frozen for regime research.

## 4. Next validation

Freeze the exact primary candidate:

`AUD_EFF1D_010_020`

and validate unchanged on `2018-09-21 -> 2020-09-21`.

No neighbor band may replace the primary if the primary fails.

## 5. Governance

- no certification yet;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
