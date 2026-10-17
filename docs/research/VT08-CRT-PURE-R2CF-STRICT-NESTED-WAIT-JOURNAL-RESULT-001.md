# VT08 CRT PURE — R2-CF strict nested WAIT journal — RESULTS & ADJUDICATION

**Date:** 2026-10-13  
**Status:** CLOSED: diagnostic complete, NO candidate promotion  
**Run:** [38442593863](https://github.com/mezas3238-hue/qore-core/actions/runs/38442593863)  
**Freeze:** `docs/research/VT08-CRT-PURE-R2CF-STRICT-NESTED-WAIT-JOURNAL-FREEZE-001.md`  
**Method:** frozen R2-CC/CD ledgers; initial historical WAIT membership computed only from strictly earlier full 4Y, never from the year whose trade is being classified. Historical warmup missing -> excluded, fail closed. Original entry/stop/target/STOP_FIRST/C3 and protection unchanged, no sizing or volume.

## CI and control reproduction

GitHub Actions successful on both markets and quality gate. Ruff GREEN; strict mypy GREEN; 9 pure unit tests across R2-CE/R2-CF GREEN (5 existing R2-CE, 4 new R2-CF). GitHub original evidence and hashes stored in downloadable workflow artifacts.

Control AUDUSD: exactly 1,067 trades, PF 1.07424084, +28.14400120R, DD 17.00562863R, source report matched.

Control USDJPY: exactly 511 trades, PF 1.01154342, +2.26369481R, DD 15.16258017R, source report matched.

## AUDUSD: strict nested vs control

| Indicator | R2-CC control | R2-CF strict nested |
|---|---:|---:|
| Number of OOS folds | 11 | 11 |
| OOS trades | 1,067 | 1,180 |
| Density/year | 97 | 107.27272727 |
| Original first EXECUTE | 815 | 815 |
| Delayed WAIT EXECUTE | 252 | 365 |
| PF gross | 1.07424084 | 1.07339866 |
| Total gross R | +28.14400120 | +31.10411915 |
| Gross DD R | 17.00562863 | 18.38404156 |
| DOA | 24.179944% | 24.830508% |
| Cost 0.02R PF | 1.01740919 | 1.01717671 |
| Cost 0.02R total | +6.80400120R | +7.50411915R |
| Cost 0.02R DD | 22.15907357R | 26.50837446R |
| Cost 0.05R PF | 0.93833439 | 0.93894651 |
| Cost 0.05R total | -25.20599880R | -27.89588085R |
| Positive OOS years | 8/11 | 8/11 |

The strictly nested version recovers +113 trades from WAIT vs original control, but its PF is flat/slightly worse and DD/DOA increase. Compared with optimistic R2-CE (AUDUSD 1,232 trades, +36.43575727R, 0.02R +11.79575727R) the benefit shrinks appreciably.

OOS chronological caution: 2016 nested fold **-7.17033392R** vs original control **+3.79462578R**; 2024 nested +14.04901905R vs control +7.24756370R. Several folded gains and losses offset; costs remain decisive.

**AUDUSD verdict:** weak thin-friction signal remains but density 107.27/year vs floor 170 and cost 0.05R FAIL. Not candidate ready.

## USDJPY: strict nested vs control

| Indicator | R2-CD control | R2-CF strict nested |
|---|---:|---:|
| Number of OOS folds | 8 | 8 |
| OOS trades | 511 | 564 |
| Density/year | 63.875 | 70.5 |
| Original first EXECUTE | 432 | 432 |
| Delayed WAIT EXECUTE | 79 | 132 |
| PF gross | 1.01154342 | 0.99648702 |
| Total gross R | +2.26369481 | **-0.75836461** |
| Gross DD R | 15.16258017 | 22.79574045 |
| DOA | 24.461840% | 25.354610% |
| Cost 0.02R PF | 0.96054269 | **0.94576607** |
| Cost 0.02R total | -7.95630519R | **-12.03836461R** |
| Cost 0.02R DD | 17.25849732R | 26.81574045R |
| Cost 0.05R PF | 0.88919731 | 0.87482113 |
| Cost 0.05R total | -23.28630519R | -28.95836461R |
| Positive OOS years | 4/8 | 4/8 |

R2-CE same-4Y in-sample cohort had given USDJPY 600 trades, PF 1.10977925, +25.21538718R, cost 0.02R **+13.21538718R**. With strictly previous-4Y historical cohorts, this optimistic gain **does not survive**.

Dominant year-specific exception: 2023 nested **-12.31341274R** vs control -2.48285179R. The total is negative even **before** 0.02R friction, and density is drastically below floor.

**USDJPY verdict:** R2-CE gain cannot be promoted; strict nested model is not economically viable.

## Explicit method limitations

- All these years had already entered historical research, so R2-CF is a causal-integrity check, **not a fresh holdout**.
- The strict nested warmup removes records from early 4Y OOS folds; this is deliberate preregistered honesty, not a discovered threshold to tune.
- Frozen delayed ledger replay measures modeled OHLC/bar economics with original execution assumptions; it does not independently validate actual fill costs on new broker tick/BID/ASK evidence.
- Profit factors near 1 and positive R at only one cost stress are inadequate to prove tradable alpha.
- The strong first-M15 journey conditional atlas describes retrospectively separated outcomes; those figures are **not** an authorized entry rule.
- BTCUSD market research status remains frozen/untouched.

## Scientific closure and next work

**R2-CF technical PASS / economic NO_PROMOTION.** Avoid repeated post-hoc relaxation of 4Y warmup, `WAIT` support or 0.02R costs to rescue the negative result.

Priority next diagnostics before any independent new candidates:
1. Investigate the **year 2023 USDJPY** degradation and **2016 AUDUSD** degradation using already recorded chronological fold, state/transition, and original event identities, without choosing filters from their outcomes.
2. Distinguish support failures (UNKNOWN -> WAIT) from toxic state false promotions (CONFLICTED/PARTIAL -> EXECUTE). Publish full contingency and state/year counts.
3. Quantify the *maximum causal WAIT capacity* and fraction consumed/invalidated before reassessment per market. No activation of more positions from ABSTAIN; no infinite WAIT.
4. Only formulate a **new, mechanistically justified and preregistered** model if diagnostics identify genuinely new information. Otherwise close these market branches as NO_SUPPORT/insufficient post-cost edge.
5. Full QORE certifications, Monte Carlo, fresh holdout and combined three-market validation remain gated until legitimate high-density, post-friction market candidates exist.

**Governance:** no trader sizing/volume/leverage/capital authority; no merge, VPS, DEMO, LIVE, production or real capital. PR #626 remains draft and unmerged.
