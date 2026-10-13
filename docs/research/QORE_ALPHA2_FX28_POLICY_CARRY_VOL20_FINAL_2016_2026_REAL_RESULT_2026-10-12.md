# QORE-Alpha 2 — LAST predeclared FX28 BIS policy-carry VOL20 risk-control experiment: FULL REAL RESULT, 2016–2026

**Fecha de cierre: 2026-10-12 Paraguay / 2026-10-13 UTC.**
**Formal status `POLICY_VOL20_FINAL_SCREEN_FAILED_CLOSE_LINE`**. NOT a universal falsation of FX carry. NEVER broker NET, never portfolio-NAV verified, never a UTC001-certified trader. 0 orders. Research-only GitHub PR #840 **DRAFT**.

## 1. Scientific judgment and genealogy (before outcomes)

- **NEW frozen hypothesis**: `docs/research/QORE_ALPHA2_FX28_POLICY_CARRY_VOL20_SINGLE_LAST_PREREG_2026-10-12.md`, registered ancestor **commit `9c51aa509040ebbd470a9c59d525d86760922c1b`** before ANY original Alpha2 **2024-09–2026-09** OHLC was exposed to this testing branch.
- Earlier BIS-policy pure carry had **`POLICY28_PREDECLARED_MODEL_SCREEN_FAILED_STOP`** over 2016–2024; the positive hypothetical carry accrual was largely mechanical from selecting highest base-minus-quote rates and is **not proof of edge**. The new VOL20 variant is OUTCOME-AWARE on 2016–2024, NOT independent confirmation on DEV or already seen DIAG; years 2024–2026 were restricted from Alpha2 only and are NOT guaranteed to be globally virgin across QORE.
- **Scientific motivation**: Menkhoff et al (2012) https://doi.org/10.1111/j.1540-6261.2012.01728.x associate carry's return shortfall with FX volatility **innovations**. Brunnermeier et al (2009) https://www.nber.org/papers/w14473 documents negatively skewed currency carry and unwind risk. Neither paper proves that our ex-ante realized-20d scaling works in this CFD universe; this one fixed recipe was independently falsifiable.
- **Signal fixed**: eight BIS WS_CBPOL central-bank policy rates monthly previous EOM; two-week lag before first all28 UTC source-day **≥16th** monthly; exactly 28 native FX pairs from 8 currencies (not independent: 28=K8, ≤7 independent rate differentials), LONG 6 highest base-minus-quote interest, SHORT 6 lowest, weights ±1/12. Native original5m first OPEN current/last CLOSE before next16: **price references, NOT fills**.
- **Only one new filter**: 20 prior COMMON FX28 daily *log returns* per pair, sample SD (only fully CLOSED 21 previous daily observations), global `sigma_ann=sqrt(mean_i(sample_stdev20_i²))*sqrt(252)`; scale `s=min(1,0.10/sigma_ann)` with 10% annual target, `0<s≤1`, no leverage boost/floor/cap/stop/VIX. Scale **both spot+policy hypothetical rate accrual and cost**; risk candidate `s * (spot_return + hypot_rate_interest - 4bps)`, paired baseline `spot_return+hypot_rate_interest-4bps`, both SAME calendar eligible trades. Broker forward prices, real swap, actual cash cost and USD portfolio PnL unobserved.
- Inference: calendars DEV [2016-09-17,2022-01-01), DIAG [2022-01-01,2026-09-17), and **held-back-for-Alpha2 date [2024-09-17,2026-09-17)** (operated months **Oct2024–Aug2026**). 3-month circular synchronized B2000 seed20261012; paired difference filtered−pure bootstrap using identical resampling indices. Gates sample ≥24 DEV, ≥24 DIAG, ≥12 held-back; **DIAG model mean>0, 3-month CI95 lower>0 and annualized MODEL Sharpe>0.4, plus held-back mean>0**. Holding and policy EOM as previously preregistered; no post-result tuning.

## 2. Original-data verification and independent SHA custody

- [GitHub Actions **#38326753172**](https://github.com/mezas3238-hue/qore-core/actions/runs/38326753172): final **COMPLETED SUCCESS**, HEAD exact `9ad87183b797087cf713cdc4a58a5867b0b2d28e`. Protocol ancestor check PASS, Ruff PASS, **6/6 synthetic no-lookahead/cost/BIS cutoff and source tests PASS**; **7/7 Atlas original +21/21 ICMarkets original FX sources SHA11y original/quality pass**; original source price extension only read after frozen prereg, **through Sep16 2026** with new study-specific `Day` validator; the previously approved legacy Day retains its strict Sep17 2024 cutoff.
- Original BIS `WS_CBPOL` monthly as-of retrospective source SHA256 **`6a616df4397881703cfe2a13cb9e1460b2defd3a26aceb14613fd6da1f3bb773`**. 7/8 country rate series 121 EOM periods (Aug2016–Aug2026), JPY 120 (Sep2016–Aug2026; Aug2016 gap censored). CHF methodology target 3m LIBOR midpoint until Jun2019, SNB own policy afterward; NOT constant homogeneous; BIS no authenticated historical vintage available, 15-day lag mitigates only. No raw BIS rate levels or original M5 OHLC in public uploaded artifact.
- **Source exact common all28 eligible UTC weekdays 2604**, 117 operated monthly portfolios (DEV61, DIAG56 of which 23 Oct2024–Aug2026). Censored reason `EIGHT_POLICY_PRIOR_EOM_MISSING=1`, `ERA_BOUNDARY_OR_SHORT_HOLD_OR_CUTOFF=1`, `NO_COMMON_COMPLETE_MONTH=1`, `PAST_20_GLOBAL_VOL_NOT_AVAILABLE=1`. **2016-10 pure baseline** excluded because risk20 requires 21 fully prior common daily CLOSE observations at decision date.
- GitHub artifact #**11781920651** `alpha2-FX28-BIS-VOL20-FINAL-2026-AGG-9ad87183b797087cf713cdc4a58a5867b0b2d28e`, official ZIP **SHA256 `12ebdb395acc8180c8c36e0a2126aa299f14d118b5150a7cb9e94b2f85b6c0f5`**, independently downloaded; ZIP SHA, the two internal files `OUTPUT_SHA256SUMS.txt` rehashed **PASS**. Source historical raw files and raw BIS rates removed from ephemeral runner before publishing aggregates. Readback 117/117 month 6L/6S disjoint, `s∈(0,1]`, model filtered and unfiltered correctly scaled and 4×s assumed-cost checks PASS, no orders.
- **Critical independent historical benchmark reconciliation:** archive original pure BIS carry artifact #11780900569 original ZIP SHA256 `8ba1746a70956ee42cd8cb5fbd84afda8d37d4c46ea4b67c3d05f546065b5fc6`. **93/93 overlapping monthly records exactly reproduced** in date of entry+exit, long6, short6, gross spot contribution, hypothetical rate accrual and assumed-cost PnL; **ZERO discrepancies** within 1e−8 bps. 94th old baseline month `2016-10` excluded by the new 20-day vol lookback, as preregistered. No price/calendar drift inadvertently attributed to filter.

## 3. Actual risk/return outcomes (bps per FULL calendar month, cash0)

| 2016–2026 source period | DEV 2016–21 | DIAG 2022–26 | Restricted-to-Alpha2 2024–26 |
|---|---:|---:|---:|
| Active complete month portfolios | **61 / 64** | **56 / 56** | **23 / 23** |
| **Pure original policy-carry comparison** assumed cost bps/month | −3.70143 | **+16.12516** | **+14.56813** |
| **VOL20 filtered** assumed cost bps/month | **−4.51227** | **+15.94242** | **+11.96571** |
| **Paired filtered−pure mean bps/month** | **−0.81084** | **−0.18274** | **−2.60242** |
| 95% CI(3-month blocks) filtered bps/month | [−29.47708,+20.24788] | **[−16.76352,+45.16249]** | **[−39.06059,+49.83848]** |
| 95% CI(3-month blocks) paired improvement | [−2.04544,0.00000] | [−3.43838,+2.85429] | [−7.80726,0.00000] |
| Annualized **MODEL Sharpe** filtered | −0.12785 | **+0.46388** | +0.38734 |
| Annualized **MODEL Sharpe** original pure | −0.10424 | +0.45808 | **+0.45853** |
| MODEL max drawdown filtered (not real NAV) | 8.2006% | **5.8168%** | 5.0917% |
| MODEL max drawdown pure (not real NAV) | 8.1551% | 6.2089% | **5.0611%** |
| Model filtered monthly skewness | −0.2842 | **−0.6984** | **−1.2695** |
| Months filtered scale s<1 | **5/61** | **5/56** | **1/23** |
| Mean factor s, active months | 0.98771 | 0.98114 | 0.98420 |

**Mechanistic explanation:** the annualized global realized 20d FX threshold of 10% rarely triggered: **only 5 of 56 diagnosis months and 1 of 23 held-back months**. It did reduce modeled maximum drawdown **slightly** in full diagnostic (6.21%→5.82%) but the held-back segment **worsened slightly** (5.06%→5.09%). It did **not** improve mean monthly model returns: DEV−0.81, DIAG−0.18, retained−2.60 bps/month. Diagnostic MODEL Sharpe 0.464 clears the user's >0.4 portion but **CI lower−16.764 bps <0**; FAIL the locked multi-condition gate. The retained 2024–26 mean is positive but its **CI95 spans −39.06 to +49.84bps**; too imprecise to certify.

Downside diagnostic worst month **March 2025 −322.78bps** on original and filtered (**s=1**), because prior FX vol20=0.0812 annual <0.10 target; tail remains. Other large original diagnostic loss July2024 −311.48bps also s=1 (global vol20=0.0560). In retained segment only **April2025** scaled (s≈0.637) which *cut a positive +164.69bps month to +104.83bps*; the large negative March2025 remained unscaled. The −0.698 diagnostic and −1.269 retained monthly skewness are **consistent with** downside asymmetry but **do NOT identify causal crash events**, which would require independent VIX/liquidity innovations, real funding and exogenous information. No risk-off cherry-picked threshold after seeing results.

## 4. Stop and scientific decision

**FINAL STATUS: `POLICY_VOL20_FINAL_SCREEN_FAILED_CLOSE_LINE`.** This one preregistered volatility-control hypothesis does **not** demonstrate an incremental economic edge or the locked diagnostic model CI95 positive criterion; sample-size gates DEV,DIAG,retained all passed. The pure reference positive 2022–26 modeled mean and Sharpe are EXPLORATORY and NOT executable proof, not Sharpe NET. No overclaim that "carry does not exist" or all crash filters fail.

- **Stop further adaptive variants on 2016–2026**: no 5/10/60d, other vol targets, VIX or drawdown gate, alternate FX universes, 4/8/10 selection, hand-picked 2025 or favorable sub-periods, posthoc stops. A truly new independent market mechanism can be preregistered only with separate empirical hypothesis and fresh source/period; cannot treat known 2016–26 as virgin.
- Original F1M-forward-prices carry remains `CARRY_NOT_IDENTIFIABLE_SPOT_ONLY`, distinct from this BIS policy proxy (policy accrual hypothetical, no actual funding and cross-currency basis). **0 Alpha2 traders certified / 0 real broker orders / no broker Sharpe/PF/DD NET**, original account alias #868, historic PIT BID/ASK and financing #852, source legal 728MB custody #837 remain parallel P0 without reopening this filter test.
- Research PR #840 remains DRAFT; no merge MAIN, no VPS/MT5, CIBO/Shared/QDLE, PAPER or LIVE.
