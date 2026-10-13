# QORE Futures A — EIA daily F1/F2 zero-dollar predictive-screen PREREGISTRATION

**FROZEN PRIOR TO ANY ECONOMIC/STATISTICAL OUTCOME RUN — 2026-10-13.**
**Source baseline:** research/qore-commodity-futures-mission-a-data-contract-20261013 @ `c8aececffee1e393849eb585740fe919cae01098`.
**Scientific mode:** diagnostic association test **ONLY**, *not* tradable return, Sharpe, profit factor, turnover, roll yield, NAV, backtest or a trader. **Budget USD0**.

## Background: actual known source and caveat

Four EIA public XLSs already fetched, SHA256 audited, 2012-01-03 → **2024-04-05**:
- WTI F1 `RCLC1d.xls`: `a55a70d2438ebdc600a77f9d3f9c46be1e2f480ac5ffec3bb753c61cf21db0c9`.
- WTI F2 `RCLC2d.xls`: `31d8a01ae5bd3cb8753925743802c9e77f11bd54ce1b5e0fd4d91d91940ecea7`.
- NG F1 `RNGC1d.xls`: `1e71a774943c00cdba337c8be1c9888ea1d56b175c446527cc0d94f7dc2b03f1`.
- NG F2 `RNGC2d.xls`: `abf42f8f7c6acc9581d283688d7571336a0ee4850c7ae43e433e37720f655aee`.

Official EIA definitions [WTI rank 1/2](https://www.eia.gov/dnav/pet/TblDefs/pet_pri_fut_tbldef2.asp), [NG rank 1/2](https://www.eia.gov/dnav/ng/TblDefs/ng_pri_fut_tbldef2.asp): rank 1 rolls to a different contract as earliest delivery changes, rank 2 is subsequent delivery. No immutable CME native instrument ID in EIA XLS; first-published-at of historical observations not provided; data revised/as-of snapshots uncertain. Price is daily EIA quoted futures price, **not OHLCV** and not an executable fill. No contract-month price-difference accounting is possible. Even a positive statistical result **is not economic edge**. Negative CL April-2020 permitted.

## Fixed hypothesis (exactly TWO tests, one per independent energy root)

`H1_WTI` and `H1_NG`: when first futures contract is priced **above** second contract (backwardation, `F1_t > F2_t`), the **probability of a positive F1 *reference-price change*** over a later 5-observation day window is greater than when first is below second (contango, `F1_t < F2_t`). One-sided directional test, **NOT** a long-short futures strategy.

Primary observed predictor: binary `X_t = 1[F1_t > F2_t]` (`0` if `F1_t < F2_t`; ties excluded).
Outcome: binary `Y_t = 1[F1_{t+7} - F1_{t+2} > 0]` (`0` if difference strictly negative; zero excluded).
`t`: **first common trade day** of each calendar month *only*, where both F1 and F2 have numeric prices. `t+2` and `t+7` are **indices in the strictly date-ordered intersection of both series**, not calendar offsets. All three dates must occur in the **same calendar month**; otherwise omit the month. `t+7` cannot cross a month boundary, and the window finishes early in each month to limit (NOT eliminate) contract-roll contamination. No intra-month multiple observations => 1 outcome per month per root, avoid overlapping horizons. Delay of **2 trading observations** is a deliberately conservative analytic proxy; EIA historical first-publication timestamp is still UNKNOWN, so never call the result fully causal / executable. If a month has no earlier F1/F2 observation, do not synthesize it. Never use `log(price)`, since WTI may be negative.

Primary estimand `delta = P(Y=1|backwardation)-P(Y=1|contango)`.
Statistical test: `scipy.stats.fisher_exact([[up_back,down_back],[up_contango,down_contango]],alternative="greater")`, one-sided; **no model fitting, hyperparameter search, machine learning, or cross-market pooling**. Fix both roots in advance. Apply **Bonferroni family control** across 2 hypotheses, each needs `p<=0.025` in BOTH DEV and DIAG with `delta>=+0.10`. Binary green not granted unless groups in each window contain **at least 8 months in backwardation and 8 in contango**, otherwise `INCONCLUSIVE_TOO_FEW_MONTHS` rather than falsifying the mechanism. If `delta<=0`, label `NO_POSITIVE_DIRECTION`; if `delta>0` but fails tests, `NO_SUPPORT_UNDER_PREREG`. No "edge absent" claims.

### Predefined partitions

- **DEV:** t (first date month) `2012-01-01 <= t <= 2018-12-31`.
- **DIAG:** t `2019-01-01 <= t <= 2021-12-31`. WTI negative price 20-Apr-2020 may be inside fetched data, but first-day predictor/outcomes do not coerce it to positive.
- **FRESH UNSEEN HOLDOUT:** `2022-01-01 <= t <= 2024-04-05`, **sealed/not read for this test** unless BOTH prereg fixed criteria pass for at least one of the two assets DEV AND DIAG. Even then, require a separate authorization and new one-shot run with same fixed specs, because this user asked first for diagnostic screening; no blind auto-evaluation. No source data on or after 2024-09-17; original FX holdout stays sealed.

### Outcomes / audit

On the FIRST execution:
1. Fetch the **four EIA XLS originals to a temporary Actions runner**. Check exact SHA256 against above hashes before any row parsing; if hashes change `BLOCKED_SOURCE_REVISION` and report only hashes. Reject duplicate dates, non-numeric/NaN/Inf, missing sheets, and datasets absent. Never inject a different data product.
2. Audit sample count and monthly categories DEV/DIAG *only*. Print JSON tables `N_months, n_back, n_cont, up_back, up_cont, down_back, down_cont, delta, Fisher p`, decision. Numeric source levels do **not** get exported/committed.
3. Decision per root: **`CANDIDATE_DESERVES_HOLDOUT_PROPOSAL`** only if DEV and DIAG individually clear conditions. Otherwise `NO_SUPPORT_UNDER_PREREG`, `NO_POSITIVE_DIRECTION`, or `INCONCLUSIVE_TOO_FEW_MONTHS`, whichever applies.
4. This is **not** a certified economic edge regardless of result. `SOURCE_READY_FOR_PREREG` for original 6×2 tradable OHLCV futures remains **FALSE / BLOCKED_DATA_OR_LICENSE** and all trader certification remains 0.
5. No scanning multiple lags, outcomes or alternative horizons after viewing results. No other assets, no tuning. Source-mapping corrections require separate prereg and independent snapshot.

**Execution boundary:** new research branch and draft PR based on earlier Futures-A M0 branch; no merge, no LIVE, VPS, MT5, CIBO, QDLE, shared or brokerage interaction. This experiment does **not** satisfy original Futures A M0 six-market data contract and does not contradict its blocked verdict.
