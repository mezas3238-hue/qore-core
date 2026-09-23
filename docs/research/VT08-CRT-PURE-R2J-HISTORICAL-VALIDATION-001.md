# VT08 CRT PURE — R2-J MARKET CONTEXT HISTORICAL VALIDATION 001

**Identity:** `VT08_CRT_PURE_R2J_MARKET_CONTEXT_VALIDATION_001`  
**Workflow run:** `35812979513`  
**Evidence HEAD:** `7b99cc7ae14a8adf906e00bf2dca49a2d6ef8c43`  
**Validation:** `2022-09-21 -> 2024-09-21`  
**Status:** COMPLETE / PARTIAL SURVIVAL

## 1. Validation design

R2-J candidate arms were frozen from R2-I development forensics before historical
validation results were observed.

The validation gate was binary:

- at least 24 trades;
- PF >= 1.05;
- total R > 0;
- DD <= 12R;
- Year 1 total R > 0;
- Year 2 total R > 0.

No arm was ranked or selected by best PnL.

## 2. Validation integrity

Run `35812979513`: SUCCESS.

- Quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD: SUCCESS
- USDJPY: SUCCESS
- BTCUSD: SUCCESS
- Cognitive Gate: SUCCESS

Artifacts:

- AUDUSD: `sha256:98b179bfe7c32d0f1fd4db3be2ab9519649146bb09493b1fc6cde7ab17267293`
- USDJPY: `sha256:e2aab09fb44d6c3d28458230f8e93f43af2476687df039e37bd01d020d5a5a3a`
- BTCUSD: `sha256:6d2c929db06d6c560361d9a8e432a29f32cbf096d81265c435cc45aabab8a6d0`

## 3. AUDUSD

Control:
- 101 trades
- PF 0.95575856
- -1.47945647R
- DD 10.93787884R
- Year 1 +3.29053333R
- Year 2 -4.76998980R
- FAIL

### Survivor: AUD_G1

- 44 trades
- PF 1.22758570
- +2.65070845R
- DD 5.24027467R
- Year 1 +0.13731069R
- Year 2 +2.51339776R
- **SURVIVED**

Rejected:
- REF2+: PF 0.9224 / -1.046R
- source range >= 0.30 C1: PF 0.5730 / -8.781R
- T1 bullish: PF 0.6141 / -5.351R

Interpretation:

Generation 1 is the only AUDUSD development clue in this family that generalized to the
historical validation window. The more visually attractive development clues did not.

## 4. USDJPY

Control:
- 90 trades
- PF 0.58459292
- -17.32565723R
- DD 18.39568042R
- Year 1 -11.51715744R
- Year 2 -5.80849979R
- FAIL

Candidate arms:

- T1: 55 trades / PF 0.57879630 / -11.44818361R
- D2: 28 trades / PF 0.34257231 / -9.83866901R
- body 0.50–0.75: 28 trades / PF 0.42379294 / -6.95752299R

**No USDJPY candidate survived.**

Interpretation:

The apparently stable 2024–2026 USDJPY clues are regime-local. The older 2022–2024
window falsifies them as universal market rules.

USDJPY therefore remains an unresolved context/regime problem and must not inherit a
recent-window filter.

## 5. BTCUSD

Control:
- 160 trades
- PF 1.18831328
- +10.16291506R
- DD 8.89327623R
- Year 1 +6.63360385R
- Year 2 +3.52931121R
- **SURVIVED**

### Survivor: BTC_BEARISH

- 71 trades
- PF 1.63600133
- +13.49175746R
- DD 3.83922905R
- Year 1 +2.97347518R
- Year 2 +10.51828228R
- **SURVIVED**

### Survivor: BTC_BODY_GE_050

- 71 trades
- PF 1.43813915
- +9.13554312R
- DD 3.26729843R
- Year 1 +3.00883987R
- Year 2 +6.12670325R
- **SURVIVED**

### Survivor: BTC_REF2_PLUS

- 61 trades
- PF 1.37321754
- +6.07191985R
- DD 2.80950266R
- Year 1 +2.58794743R
- Year 2 +3.48397242R
- **SURVIVED**

Rejected:
- D2: PF 0.8983 / -1.810R
- T1 bearish: failed Year 1 despite positive full-window result

Interpretation:

BTCUSD has genuine cross-window stability. Three independent pre-entry properties
generalized, while D2 did not. The base control also survived the older window.

## 6. Current candidate status

Research survivors eligible for the next robustness stage:

- AUDUSD: `AUD_G1`
- BTCUSD: `CONTROL`
- BTCUSD: `BTC_BEARISH`
- BTCUSD: `BTC_BODY_GE_050`
- BTCUSD: `BTC_REF2_PLUS`

USDJPY:
- no survivor;
- requires a separate regime/context investigation.

Survival is **not certification**.

## 7. Next chain

1. Run robustness / bootstrap / stress on AUD_G1 and BTC survivors.
2. Use parameter-neighborhood and start-subwindow stress where meaningful.
3. Do not combine BTC survivor properties until single-factor evidence is characterized.
4. Open a historical USDJPY context forensics lab across 2022–2024 and compare it directly
   with R2-I 2024–2026.
5. Freeze any USDJPY regime hypothesis before its next validation window.

## 8. Governance

- PR DRAFT / UNMERGED.
- No VPS mutation.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
