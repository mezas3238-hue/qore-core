# VT08 CRT PURE — R2-L USDJPY PRE-PARENT REGIME FORENSICS 001

**Identity:** `VT08_CRT_PURE_R2L_USDJPY_PRE_PARENT_REGIME_FORENSICS_001`  
**Workflow run:** `35843044300`  
**Evidence HEAD:** `5448737bba63f419067e03bdd7bbc0b334330cae`  
**Window:** `2022-09-21 -> 2026-09-21`  
**Regime fold:** `2024-09-21`  
**Status:** COMPLETE / REGIME CANDIDATE FOUND / NOT PROMOTED

## 1. Objective

R2-K showed that USDJPY entry-context filters invert between the older and recent
periods. R2-L moved one causal layer upward and measured only information known before
C3 opens.

Frozen dimensions:

- recent/slow M15 realized-range ratio;
- recent directional efficiency;
- directional drift alignment with the parent CRT;
- C1 range relative to recent H4-like ranges;
- C1 body fraction;
- C2 range relative to C1;
- C2 body fraction;
- C2 manipulation depth;
- C2 reclaim depth;
- selected low-complexity cross dimensions.

No filter was promoted by R2-L itself.

## 2. Validation

Final run `35843044300`: SUCCESS.

- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- 4Y USDJPY forensics: SUCCESS
- Cognitive Gate: SUCCESS

The initial R2-L test correctly exposed an invalid trend-efficiency denominator that could
produce values above 1. The metric was fixed before economic evidence was consumed.

## 3. Control

Four-year R2-G NEWEST control:

- 194 trades
- PF 0.83174641
- -13.16531549R
- mean -0.06786245R
- DD 22.62769992R

Older 2022-2024:

- 90 trades
- PF 0.58459292
- -17.32565723R

Recent 2024-2026:

- 104 trades
- PF 1.11385968
- +4.16034174R

The regime inversion is real and material.

## 4. Strongest cross-regime clue

The only bucket with at least 12 trades in each 2Y side and positive total R in both sides
was:

`C1BODY_0_25_TO_0_50`

Full 4Y:

- 47 trades
- PF 1.93579761
- +12.99367065R
- DD 2.83684032R

Older 2022-2024:

- 23 trades
- PF 1.21643168
- +1.99672260R

Recent 2024-2026:

- 24 trades
- PF 3.36012303
- +10.99694805R

## 5. Neighboring C1-body regions

The surrounding buckets do not share that behavior.

`C1BODY_LT_0_25`:
- 48 trades
- PF 0.47775549
- -12.34538463R
- negative in both 2Y regimes

`C1BODY_0_50_TO_0_75`:
- 69 trades
- PF 0.62120671
- -11.16495835R
- negative in both regimes

`C1BODY_GE_0_75`:
- 30 trades
- PF 0.76451427
- -2.64864316R
- older negative / recent positive

This makes the 0.25-0.50 C1-body band materially more specific than a generic
"larger body is better" explanation.

## 6. Secondary observations

`VOL_LT_0_80`:
- 19 trades
- PF 2.01697169
- +3.50377535R
- older +1.51777862R / recent +1.98599673R

This is interesting but sparse and is not promoted.

Other apparent recent winners such as large C1 range, reclaim depth and opposed drift
continue to invert across regimes and therefore do not explain the full history.

## 7. R2-N assignment

The next validation is frozen before reading an earlier window:

`2020-09-21 -> 2022-09-21`

with fold:

`2021-09-21`

R2-N will validate a small C1-body family:

- CONTROL
- C1 body 0.25-0.50 — PRIMARY
- C1 body 0.20-0.50 — lower-bound neighborhood
- C1 body 0.25-0.55 — upper-bound neighborhood
- C1 body 0.20-0.55 — broad neighborhood

No arm may be automatically selected by best PnL.

The binary research gate is frozen before results:

- at least 20 trades;
- PF >= 1.05;
- total R > 0;
- DD <= 12R;
- both 1Y halves > 0R.

This is an R2-N research gate, not a CRT certification threshold.

## 8. Governance

- PR DRAFT / UNMERGED.
- No VPS.
- No DEMO.
- No LIVE.
- No production.
- No real-capital authority.
