# QORE Capitalizer — V3 Master Diagnostic Ledger

Checkpoint: 23-Sep-2026  
Owner: Sergio  
PR: #623 (DRAFT)  
Branch: agent/qore-capitalizer-cognitive-v1-001

## Governance

This document is diagnostic evidence only.

- V3 remains frozen.
- No market/session is removed because of consumed outcomes.
- No threshold or selector rule is promoted from this 1Y sample.
- No VPS, LIVE, demo, real-capital or merge action is authorized.
- Any causal rule derived below must be frozen before out-of-sample validation.

## Sources

Frozen development window:

- `[2025-09-17, 2026-09-17)`
- immutable native M1 source run `35548099334`
- source SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`

Master Funnel Forensics:

- run `35800023274`
- research SHA `10555e508f81dc61c8de2d0968146980fe70f840`
- aggregate artifact `10726115684`
- digest `sha256:23a4a8939cd5455f3d765a6d5f1e5206df5ea6d4ca7b55ed7c3e891b9eeb367d`

Post-H1 FVG observation:

- run `35800916835`
- research SHA `106ca04a6c8c62c10b26d1936247a233e7f7b7eb`
- aggregate artifact `10725414916`
- digest `sha256:55f79d4e43d0b8ec750e7c20d1b258b2ed91352edf586000949e826a49133e13`

## 1. Frozen V3 control

- MAX3 trades: **226**
- PF: **1.29791191**
- Total: **+23.380560R**
- Mean: **+0.103454R/trade**
- DD: **7.349677R**
- losing streak: **8**

Exit mix:

- STOP: 66
- TARGET: 29
- TIME_EXIT: 93
- SESSION_EXIT: 38

## 2. Master funnel

- M5 closebacks: **4,039**
- valid V3 M3 MSS: **621**
- causal FVG: **526**
- fill inside H1: **268**
- valid stop geometry: **227**
- MAX3 selected: **226**

Loss after valid MSS:

- no FVG: 95
- FVG but no H1 fill: **258**
- fill with invalid stop geometry: 41
- portfolio MAX3 block: **1**

Therefore MAX3 is not the V3 density bottleneck.

The dominant post-MSS bottleneck is the FVG fill lifecycle:
**526 FVG -> 268 fills**.

## 3. Post-H1 observation of the 258 no-fill FVGs

The study does not create trades. It observes the same frozen FVG for 60 additional minutes, same-session only.

- total cohort: **258**
- touch <=5 min: **46**
- touch <=15 min: **66**
- touch <=30 min: **85**
- touch <=60 min: **103**
- no touch within 60 min: **155**
- valid stop geometry at delayed touch: **90**
- observationally clean touch: **39**
- touches blocked by frozen V3 MAX3: **0**
- simultaneous delayed-touch groups: **0**

Touch mode:

- OB/FVG retest: 59
- FVG CE50: 44

Key conclusion:

A simple lifecycle extension cannot recover hundreds of high-quality trades. Although 103 no-fill FVGs touch later, only 39 remain structurally clean under the observational checks. Even before economic testing, the upper bound of this clean delayed-touch population is small.

## 4. Market personality ledger — consumed development evidence

| Market | V3 trades | PF | Total R | Stop rate | H1 no-fill FVG | <=60m later touch | Clean touch |
|---|---:|---:|---:|---:|---:|---:|---:|
| AUDJPY | 16 | 1.5665 | +2.3906 | 25.00% | 24 | 6 | 2 |
| AUDUSD | 29 | 0.8215 | -1.6218 | 24.14% | 28 | 16 | 4 |
| EURUSD | 41 | 1.5318 | +6.1329 | 24.39% | 36 | 17 | 6 |
| GBPJPY | 27 | 0.8583 | -1.5509 | 37.04% | 19 | 5 | 3 |
| GBPUSD | 35 | 1.3618 | +5.0435 | 34.29% | 30 | 13 | 5 |
| NAS100 | 19 | 1.0021 | +0.0195 | 47.37% | 37 | 11 | 5 |
| USDCAD | 23 | 2.9330 | +10.8787 | 21.74% | 38 | 12 | 6 |
| USDJPY | 21 | 1.2597 | +2.0204 | 23.81% | 25 | 14 | 4 |
| XAUUSD | 15 | 1.0109 | +0.0677 | 26.67% | 21 | 9 | 4 |

These numbers are personality diagnostics, not permission to remove losing markets.

### Stop-geometry concentration

Of 41 fills rejected by invalid V3 stop geometry:

- NAS100: 21
- XAUUSD: 17
- AUDJPY: 1
- EURUSD: 1
- USDCAD: 1
- all other markets: 0

NAS100 + XAUUSD therefore account for **38/41** invalid-stop cases. This is a market-specific geometry clue and should be investigated as structure, not fixed by widening stops.

## 5. Drawdown root forensics

The exact V3 raw trade artifacts were reconstructed and portfolio MAX3 reapplied.

### Maximum drawdown

Peak:

- equity: **+22.899800R**
- entry time at peak: `2026-04-20 01:33 UTC`

Trough:

- equity: **+15.550123R**
- trough entry: `2026-05-05 14:25 UTC`

Observed DD:

- **7.349677R**

Trades after peak through trough:

- 13 trades
- session contribution:
  - Asia: **-1.946970R**
  - London: **-4.000000R**
  - New York: **-1.402707R**

Only one overlapping-position event occurred inside the entire max-DD interval:
EURUSD and GBPUSD entered at the same minute on 1-May-2026 and both stopped, producing -2R.

### Portfolio overlap

Across all 226 selected trades:

- 214 entries opened with **0** previous V3 positions alive
- 11 entries opened with **1** previous V3 position alive
- 1 entry opened with **2** previous V3 positions alive
- total overlap pairs: 13

Conclusion:

The 7.35R DD is primarily a **sequential loss-cluster problem**, not a general over-exposure/concurrency problem.

### Longest losing streak

- 8 consecutive negative trades
- 2-Oct-2025 through 10-Oct-2025
- total: approximately **-6.013R**
- spread across EURUSD, NAS100, GBPJPY, XAUUSD, USDCAD, GBPUSD, USDJPY and EURUSD again

This again argues against attributing the problem to one market alone.

## 6. Causal timing hypotheses — development only

The existing cognitive `Session Journey` / causal-expiration modules have a concrete clue.

### MSS position inside the H1

First half of H1 (<30 min):

- 89 trades
- PF **1.8716**
- Total **+27.6377R**
- DD **4.0117R**

Second half of H1 (>=30 min):

- 137 trades
- PF **0.9090**
- Total **-4.2572R**
- DD **15.9446R**

### M5 closeback -> valid MSS latency

MSS within <=30 minutes of closeback:

- 186 trades
- PF **1.4031**
- Total **+25.9256R**
- DD **6.6655R**

MSS after >30 minutes:

- 40 trades
- PF **0.8203**
- Total **-2.5450R**
- DD **6.1488R**

Interpretation:

There is a strong development-sample hypothesis that **causal freshness/expiration matters**. This is structurally different from deleting a market or loosening M3 filters. It is information available before entry and fits the already-built cognitive architecture.

However, neither the 30-minute boundary nor the H1-half observation is promoted from this consumed sample. They require a predeclared out-of-sample validation.

## 7. Current root picture

### Density

- D1: more density, edge diluted.
- D2: later MSS cohort negative.
- MAX3: almost irrelevant at current V3 density.
- post-H1 FVG touches: some recoverable structure exists, but clean population is only 39.
- largest unresolved density reservoir remains upstream at M3 discrimination, which cannot be loosened blindly because V4 already falsified that approach.

### PF

A causal freshness signal is now visible:
late/stale confirmation is materially weaker in the consumed year.

### DD

DD is driven mainly by sequential multi-market loss clusters, not persistent concurrent exposure.

### Market depth

The markets are demonstrably heterogeneous in:
- stop geometry;
- fill availability;
- stop rate;
- delayed-touch behavior;
- development economics.

This should feed Market Brain / Session Journey research, not retrospective market deletion.

## 8. Next validation protocol

Do not consume another period without freezing the question first.

Recommended next research contract:

1. Keep V3 unchanged.
2. Freeze a **causal-expiration diagnostic hypothesis**, not an economic promotion:
   - primary natural boundary: closeback -> MSS <=30 minutes vs >30 minutes;
   - no market filtering;
   - no session filtering;
   - no outcome-aware runtime input.
3. Validate that relationship on a previously unused historical window before binding it to cognition.
4. Preserve a separate untouched period for eventual candidate holdout.
5. Continue stop-geometry root forensics for NAS100/XAUUSD without widening stops.
6. Treat the 39 clean delayed FVG touches as a bounded density research population; do not enable them until a lifecycle contract is declared and validated.

No strategy promotion is authorized by this document.


## 9. Historical freshness audit

A project-level freshness audit was completed before opening another validation window.

The existing workflow:

`QORE Capitalizer Native M1 5Y Dev Holdout V1`

predeclared:

- DEVELOPMENT: `[2016-09-17, 2021-09-17)`
- FRESH_HOLDOUT: `[2021-09-17, 2026-09-17)`

The workflow was executed successfully:

- commit: `e7cc3ed4497cb5e51303de374d7e3c6eedaebcdd`
- run: `35548659988`
- quality: GREEN
- all 9 development jobs: GREEN
- development aggregate: GREEN
- contract freeze: GREEN
- all 9 holdout jobs: GREEN
- holdout aggregate: GREEN
- development/holdout comparison: GREEN

Therefore the entire currently available CIBO 10Y historical span has already been exposed to Capitalizer research at project level.

### Governance consequence

No sub-window inside `[2016-09-17, 2026-09-17)` may now be described as a genuinely fresh historical holdout for the current V3 causal-expiration hypothesis.

Any additional work on those dates must be labeled:

`CONSUMED_TEMPORAL_VALIDATION`

and may establish temporal consistency / falsification evidence only. It cannot, by itself, satisfy the future certification requirement for a sealed fresh holdout.

A genuinely fresh test now requires data not previously exposed to Capitalizer research (for example future forward data or an independently sealed external historical source with proven non-exposure).

## 10. Frozen temporal-validation hypothesis

Before looking at additional fold outcomes, the following single diagnostic hypothesis is frozen:

`M5_CLOSEBACK_TO_VALID_M3_MSS_CAUSAL_FRESHNESS_30M`

Comparison:

- FRESHNESS cohort: closeback -> first valid V3 MSS <= 30 minutes
- STALE cohort: closeback -> first valid V3 MSS > 30 minutes

Invariants:

- V3 entry trigger remains M1 causal OB+FVG.
- V3 M3 CISD / swing / body / ATR filters remain unchanged.
- stop remains M3 broken/protected swing + 5-pip buffer.
- target remains fixed 2R / next-H1-open lifecycle.
- MAX3 remains portfolio ceiling.
- no market or session is removed.
- outcomes are labels only and are not runtime admission features.
- the 30-minute boundary is fixed before the 10Y temporal fold results are read.

The 10Y study is diagnostic only and must report all annual folds, including failures.
