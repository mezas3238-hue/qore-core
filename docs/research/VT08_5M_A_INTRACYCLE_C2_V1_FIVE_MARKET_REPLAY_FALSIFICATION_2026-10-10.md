# VT08 5M — P0-A M15 Intracycle C2 V1 — RESULTADO EXPERIMENTAL / FALSIFICATION

**2026-10-10 | Evidence state:** consumed development; no independent holdout; no broker cost measurement; **NO cognitive-on replay; NOT CERTIFIED**.

- Pre-registered before economics: [VT08_5M_A_P0_M15_INTRACYCLE_C2_REVERSAL_PREREG_2026-10-10.md](VT08_5M_A_P0_M15_INTRACYCLE_C2_REVERSAL_PREREG_2026-10-10.md), first prereg commit `584c6bb04a89bf74bfeee7774f771722314b4833`.
- Branch `agent/vt08-5m-methodology-source-20261010`, PR [#765](https://github.com/mezas3238-hue/qore-core/pull/765) DRAFT.
- **Actual GitHub Actions** [run 38071818606](https://github.com/mezas3238-hue/qore-core/actions/runs/38071818606), `SUCCESS` 5/5, exact tested SHA **`8813ded3eaca42e28196ca08191975e79772af02`**.
- Input: original consumed 1095D M15 evidence [run 35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), source SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. **Sealed older 7Y archive not read**.
- Source method: [TTrades 4H PO3](https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/); [Trading Candle 2](https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/); [TTrades protected swing SL](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/), video/framebook primary full hash still pending.
- Research-only implementation: `src/qore/infrastructure/trader_lab/vt08_5m_m15_intracycle_c2_reversal_research_v1.py` and independent adversarial tests. M15 new-C2 wick sweep, CISD close-through, Protected Swing, next M15 open **as QORE OHLC model**, PS-exact SL, 2R target and same-H4 close **as QORE containments**, first chronological eligible event per NY date, stop-first OHLC ambiguous bar. Prior daily bias helper frozen; no future bars required for source PS eligibility.

## What actually happened (exactly measured)

| Market | Baseline old B01 mechanical (previous replay) | New V1 causal source-supported next-open events | Daily conflicts | NY days selected / terminal simulated | Raw equal-risk PF | Raw total R | Max DD R |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 88 | 368 | 67 | 301 | 0.817084 | -27.030737 | 32.796578 |
| USDCHF | 88 | 373 | 66 | 307 | 0.712344 | -49.531124 | 53.102287 |
| NZDUSD | 126 | 370 | 72 | 298 | 0.975219 | -3.695872 | 20.997802 |
| CADJPY | 88 | 352 | 63 | 289 | 1.113055 | +14.822909 | 11.245748 |
| USDCAD | 98 | 411 | 92 | 319 | 1.139160 | +21.641606 | 21.295356 |
| **TOTAL** | **488** | **1,874** | **360** | **1,514** | *not aggregated* | *not aggregated* | *not aggregated* |

No incomplete exit windows in this research run. The average is 302.8 simulated terminal trades per market in the ~3Y corpus, against 97.6 **mechanical candidates** per market in the baseline. This is **~3.10x observed count**, **not proof that 1,026 profitable trades were "recovered"**. The new family is a different model with a different entry timestamp and discretionary-source formalizations, not a strict superset of the baseline trades.

**Critical rejection:** ALL FIVE FAIL the PF>=1.80 research gate. ALL FIVE FAIL observed DD<=6R. EURJPY, USDCHF, NZDUSD have negative raw total R in this contract. AUDIT RESULT: **M15_INTRACYCLE_C2_REVERSAL_QORE_FILL_2R_V1 = REJECTED_AS_CERTIFICATION_CANDIDATE** despite count recovery. The baseline 488/457 was too sparse; this first density-expanded variant is **not a profitable replacement**. DO NOT promote or hide failures. A new hypothesis requires its own source-provenance/preregistration, not in-place threshold tuning.

### Counts per NY year (2023 and 2026 partial coverage)

| Market | 2023* | 2024 | 2025 | 2026* |
|---|---:|---:|---:|---:|
| EURJPY | 18 | 103 | 109 | 71 |
| USDCHF | 25 | 104 | 106 | 72 |
| NZDUSD | 29 | 102 | 97 | 70 |
| CADJPY | 21 | 99 | 95 | 74 |
| USDCAD | 30 | 106 | 113 | 70 |
| **Total** | **123** | **514** | **520** | **357** |

The historical baseline B01 mechanical count per comparable NY year was 41/179/157/111 (2023/2024/2025/2026 partial); no union or retrospective PF-based selection is allowed.

### Distinct limits / honesty requirements

1. Results are M15-only under a provisional source-supported/replay-execution QORE hybrid. They **are not** a finalized reproduction of all six TTrades entry identities.
2. The 1,514 "terminal trades" are **OHLC simulated trades** under exact next-M15-open fills, stop-first ambiguous bar, exact PS stop, fixed 2R and same-H4 exit. No bid/ask, spread, swap, commission, broker size/lotage or latency was modeled. Actual broker-valid fills may be fewer.
3. This engine has **ZERO full cognitive consumption**; any real cognitive WAIT/ABSTAIN can reduce filled density. Never attribute these R/PF/DD to Trader Cognitive V1 or CIBO.
4. No capital weighting; no stop/profit tuning; no market-hour/winner selection. All five tested at once on same development corpus, not fresh sealed data.
5. The C2 classification shallow/deep, contextual target, POI significance, C3 continuation, six family entry/SL/TP/expiry priorities remain source ambiguities/next independent contracts. Fixed2R is not the universal author target.
6. Owner policy one filled per market/NY date enforced; source 13:00 timing is NOT Owner-authorized extra entry.
7. No user-approved replacement numeric executable density gate yet; older 50/2Y gate retired.

### Machine-readable audit artifacts

[Run 38071818606](https://github.com/mezas3238-hue/qore-core/actions/runs/38071818606) uploaded per-market JSON full event/selection/terminal trade rows and summaries:
- EURJPY `11676688424`, digest `sha256:95947d93f6b19d89da7e0810c6bfbf8637bf7469c5bc9da595ebb3333c8552e2`;
- USDCHF `11677052888`, digest `sha256:3a8674a8ae9a20e09bb9e1c07fbb9f2631b80a395f9a3b7d3692a8afa6a6f4dc`;
- NZDUSD `11676653576`, digest `sha256:8eddd94712fd6bf1c83306037fc55d3c455d107e30b2a02e1e89ae344ba23fef`;
- CADJPY `11676823141`, digest `sha256:a8b112b39b4299030576ebf77211046ea8c1a9c50f00ce72049c431ed7bada4f`;
- USDCAD `11676973037`, digest `sha256:62cfb9c3b7795367f352782ad4f5c7805fe40b5240810040950338fd09907cb3`.
Retention in workflow 30 days; save immutable evidence before expiry if future audit requires.

## Next methodological actions — independent hypotheses, no old-PnL retuning

- Reconstruct TTrades' **contextual target** and C2 small-vs-deep wick logic from official newer clarifications; no invented numeric shallow threshold.
- Deep audit underlying source-day / daily bias and first-vs-many PS; still unsupported to lift them blindly.
- Source-justified, independent continuation-entry C3 and POI-continuation entry bundles, full SL/target/expiry and causal as-of, then preregister/replay consumed for density+economics.
- The first source-authorized intracycle family must be reviewed by B #763 for event adapter. B cannot interpret `SOURCE_SUPPORTED_QORE_FILL_EXPERIMENT` as fully certified machine methodology, or silently use post-outcome features in cognition. Separate source-event candidate→cognitive WAIT/ABSTAIN→executed (simulated) fill→position updates, 100% trace.
- Candidate failing PF/DD is marked failed for this V1 identity; only new source-justified identity can proceed. Do not open sealed older holdout until new numeric density gate approved and candidate frozen.

**Outcome: frequency root cause partially solved, edge NOT solved. No promotion, no VPS, no live money, no merge.**
