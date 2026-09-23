# VT08 CRT PURE — R2-M SURVIVOR ROBUSTNESS 001

**Identity:** `VT08_CRT_PURE_R2M_SURVIVOR_ROBUSTNESS_001`  
**Workflow run:** `35843318990`  
**Evidence HEAD:** `0f8a35dbdbe135c5167ab1009993cf3475c16147`  
**Window:** `2022-09-21 -> 2026-09-21`  
**Status:** COMPLETE / BTC ROBUSTNESS STRONG / AUD EDGE THIN

## 1. Objective

R2-M reuses the R2-J survivor definitions unchanged and applies existing QORE robustness
families:

- `START_SUBWINDOW`;
- `COST_PERTURBATION`.

No candidate properties are combined.

Frozen candidates:

- AUDUSD: `AUD_G1`
- BTCUSD: `CONTROL`
- BTCUSD: `BTC_BEARISH`
- BTCUSD: `BTC_BODY_GE_050`
- BTCUSD: `BTC_REF2_PLUS`

Frozen cost stresses:

- 0.02R/trade
- 0.05R/trade
- 0.10R/trade

Frozen subwindows:

- four 1Y windows;
- three rolling 2Y windows.

## 2. Validation

Run `35843318990`: SUCCESS.

- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD robustness: SUCCESS
- BTCUSD robustness: SUCCESS
- Cognitive Gate: SUCCESS

## 3. AUDUSD — AUD_G1

Full 4Y:

- 101 trades
- PF 1.15196939
- +4.53563963R
- mean +0.04490732R
- DD 5.24027467R
- losing streak 4

Temporal robustness:

- positive annual windows: **4 / 4**
- positive rolling-2Y windows: **3 / 3**

Annual totals:

- 2022-23: +0.13731069R
- 2023-24: +2.51339776R
- 2024-25: +0.97320077R
- 2025-26: +0.91173041R

Cost perturbation:

- +0.02R/trade: PF 1.08202249 / +2.51563963R
- +0.05R/trade: PF 0.98391849 / -0.51436037R
- +0.10R/trade: PF 0.83755765 / -5.56436037R

### Adjudication

AUD_G1 shows genuine temporal persistence but its margin is thin.

It must **not** be promoted as robust yet because a 0.05R adverse per-trade perturbation
removes the edge.

The correct next question for AUDUSD is execution-cost realism / entry quality, not adding
more density.

## 4. BTCUSD — CONTROL

Full 4Y:

- 390 trades
- PF 1.10911091
- +14.78889559R
- DD 15.45977995R

Temporal:

- positive annual windows: 3 / 4
- positive rolling-2Y windows: 3 / 3

Cost:

- +0.02R: +6.98889559R / PF 1.05029821
- +0.05R: -4.71110441R
- +0.10R: -24.21110441R

The unfiltered control is not robust enough to cost perturbation.

## 5. BTCUSD — BEARISH

Full 4Y:

- 188 trades
- PF 1.34065430
- +21.09040959R
- mean +0.11218303R
- DD 8.77728808R

Temporal:

- positive annual windows: **4 / 4**
- positive rolling-2Y windows: **3 / 3**

Cost:

- +0.02R: PF 1.27312856 / +17.33040959R
- +0.05R: PF 1.17754442 / +11.69040959R
- +0.10R: PF 1.03266569 / +2.29040959R

## 6. BTCUSD — BODY >= 0.50

Full 4Y:

- 186 trades
- PF 1.43811761
- +23.15093638R
- mean +0.12446740R
- DD 8.23106944R

Temporal:

- positive annual windows: **4 / 4**
- positive rolling-2Y windows: **3 / 3**

Cost:

- +0.02R: PF 1.35763082 / +19.43093638R
- +0.05R: PF 1.24450864 / +13.85093638R
- +0.10R: PF 1.07484238 / +4.55093638R

## 7. BTCUSD — REF2+

Full 4Y:

- 159 trades
- PF 1.41153497
- +16.57627409R
- mean +0.10425330R
- DD 6.39114189R

Temporal:

- positive annual windows: **4 / 4**
- positive rolling-2Y windows: **3 / 3**

Cost:

- +0.02R: PF 1.32332034 / +13.39627409R
- +0.05R: PF 1.19952714 / +8.62627409R
- +0.10R: PF 1.01453463 / +0.67627409R

## 8. Adjudication

R2-M materially separates the BTC candidate family.

The BTC single-factor candidates:

- `BTC_BEARISH`
- `BTC_BODY_GE_050`
- `BTC_REF2_PLUS`

all retain:

- positive 4Y economics;
- 4/4 positive annual windows;
- 3/3 positive rolling-2Y windows;
- positive total R under +0.10R/trade stress.

This is substantially stronger than the BTC control.

No ranking or combination is authorized yet.

The next BTC stage should use block-bootstrap / Monte-Carlo and a fresh historical
validation window, retaining the three candidates separately.

## 9. Governance

- no candidate certified;
- no automatic winner ranking;
- no candidate combination;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
