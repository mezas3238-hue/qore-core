# VT08 CRT PURE — R2-K USDJPY HISTORICAL CONTEXT 001

**Identity:** `VT08_CRT_PURE_R2K_USDJPY_HISTORICAL_CONTEXT_001`  
**Workflow run:** `35842406459`  
**Evidence HEAD:** `a409677874b55c8c4a1836f6ac457c9fa96fd800`  
**Window:** `2022-09-21 -> 2024-09-21`  
**Status:** COMPLETE / CURRENT FEATURE SET INSUFFICIENT

## 1. Objective

R2-J falsified the 2024-2026 USDJPY development clues on the older 2022-2024
validation window.

R2-K re-ran the same causal pre-entry feature taxonomy on the older window without
promoting any filter. The purpose was to determine whether the apparent failure could be
explained by one stable subset already present in R2-I.

## 2. Validation

Run `35842406459`: SUCCESS.

- Quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- Historical context forensics: SUCCESS
- Cognitive Gate on the same final HEAD: SUCCESS

The earlier R2-K failures were only Ruff F401/I001 defects and were corrected before
this successful run.

## 3. USDJPY historical control

- parent CRT: 244
- trades: 90
- PF: 0.58459292
- total: -17.32565723R
- mean: -0.19250730R
- DD: 18.39568042R
- longest losing streak: 7
- Year 1: -11.51715744R
- Year 2: -5.80849979R

The older regime is not merely weak. The current R2-G NEWEST execution is materially
negative in both halves.

## 4. Direct falsification of recent-window clues

### Confirmation delay D2

2024-2026 development:
- 21 trades
- PF 1.76695178
- +5.17655241R
- positive in both halves

2022-2024:
- 28 trades
- PF 0.34257231
- -9.83866901R
- Year 1 -9.15242264R
- Year 2 -0.68624637R

### Source body 0.50-0.75

2024-2026 development:
- 35 trades
- PF 2.28263528
- +7.52340822R
- positive in both halves

2022-2024:
- 28 trades
- PF 0.42379294
- -6.95752299R
- negative in both halves

### Triplet 1

2024-2026 development:
- 72 trades
- PF 1.29236281
- +7.14407860R
- positive in both halves

2022-2024:
- 55 trades
- PF 0.57879630
- -11.44818361R
- negative in both halves

These features are therefore regime-dependent, not universal USDJPY gates.

## 5. Search for a stable subset inside the current feature set

Among buckets with at least 8 trades, only three older-window slices had positive
full-window R:

- `G1|D1`: 11 trades / PF 1.620333 / +2.48133202R
- `PEN_0_50_TO_0_75`: 16 trades / PF 1.29646852 / +1.28994559R
- `RR_LT_0_50`: 18 trades / PF 1.40708666 / +1.15236839R

None is positive in both historical halves.

Therefore no existing R2-I dimension supplies a temporally stable repair for USDJPY.

## 6. Root-cause adjudication

The current feature family is insufficient.

Do **not** continue by combinatorially joining:

- timing;
- D1/D2/D3;
- source-body buckets;
- generation;
- penetration;
- projected RR;
- reference count.

That would be post-hoc search inside a feature set already shown to invert by regime.

The next causal layer is the market state **before the parent CRT**.

## 7. R2-L assignment

R2-L should characterize pre-parent USDJPY regime using only information known before
the selected parent trade opportunity:

- recent realized-volatility ratio;
- C1 range relative to recent typical M15 range;
- directional/trend efficiency;
- recent directional drift aligned/opposed to the parent direction;
- C1 body geometry;
- C2 range relative to C1;
- C2 manipulation depth;
- C2 close location inside C1;
- selected low-complexity cross dimensions.

The objective is to explain why the same M15 trigger family changes sign across
2022-2024 and 2024-2026.

R2-L is forensic first. No regime filter is promoted automatically.

## 8. Governance

- PR remains DRAFT / UNMERGED.
- No VPS mutation.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
