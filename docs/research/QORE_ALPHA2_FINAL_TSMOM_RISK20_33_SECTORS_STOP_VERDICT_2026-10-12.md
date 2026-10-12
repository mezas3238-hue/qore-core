# QORE-Alpha 2 — FINAL TSMOM252-RISK: vol 20d scaled, 10% target, 1bp per side, 33 original sources — STOP FAMILY

**2026-10-12. Actual executed last and final TSMOM candidate, strictly prereg before outcomes.**

- **Original prereg** [FINAL_TSMOM_RISKSCALED_AND_XSREV5_FROZEN_PREREG_2026-10-12.md](QORE_ALPHA2_FINAL_TSMOM_RISKSCALED_AND_XSREV5_FROZEN_PREREG_2026-10-12.md), immutable ancestor commit `f9248d42a6cbced3d6e962b24e47c709cb91161c`. ZERO parameter changes after outcome. Original branch PR #840 DRAFT.
- **Real SHA-gated 33 all sources test** [GitHub Actions #38318945616](https://github.com/mezas3238-hue/qore-core/actions/runs/38318945616), exact source code HEAD **`09db573527b5e9f607edf75949902c6319d6ab21`**, **35/35 jobs success**: preflight synthetic and Ruff, Original12 x12 and New21 x21 workers (source 11 years signed RAW/QUALITY), combined 33-panel.
- **Exact original report ZIP** GitHub artifact **#11776789637**, SHA256 `63b27be5ea371e863f7df4587b2a700140455f13096be6733112a14629132bd7`. Downloaded ZIP independently rehashed and verified internal `OUTPUT_SHA256SUMS.txt` entries (**PASS**). Actual JSON `alpha2-final-tsmom-risk33-sector-gross-minus-cost.json`, SHA256 **`de479f7114a66b59160850dc5359c8c1853e28b47471176fecb059e006c318ae`**. No original daily market price ZIP copied to research PR.
- Source scientific inspiration: TSMOM futures [Moskowitz-Ooi-Pedersen 2012, DOI 10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003). This panel is 28 FX (21 crosses, 7 majors) and 5 non-FX (3 equity indices, 2 metals), **NO bond/commodity-sector futures panel**. NOT a canonical 58 futures replication.

## Frozen method recap

Sign of 252 previous eligible session close return, scale signed notional at each weekly entry by `min(3, 0.10/(stdev(previous20 log daily returns)*sqrt(252)))`. Entry = first M5 original weekday OPEN, exit = last M5 original CLOSE of fifth eligible session; both mark prices, not verified first-executable quotes. A trade cannot cross frozen DEV/DIAG periods. Absolute 3x cap non-parametric. Approximate one-way cost **1bp × abs(notional)** on entry + **1bp × abs(notional)** on exit, no costs assumed zero because not known. Assumed-cost PnL is **GROSS_MINUS_ASSUMED_COST_PROXY**, not NET. Weekly portfolio return = sum positions/number of frozen sector slots, calendar zero weeks included. CI by synchronized 4week circular-block bootstrap B2000.

## Results bps/week: after assumed 1bp per side; 95% calendar bootstrap CI

| Frozen universe | DEV 2016–2022 | DEV CI95 | DIAG 2022–2024 | DIAG CI95 |
|---|---:|---|---:|---|
| **FULL33** | **−0.55044** | [−6.14630, +5.00548] | **−5.29240** | [−17.02716, +5.69845] |
| FX_CROSSES21 | −1.31666 | [−7.95948, +5.72782] | −7.92230 | [−22.10199, +4.59083] |
| FX_MAJORS7 | −1.06280 | [−10.77381, +8.99467] | −6.11250 | [−21.28103, +9.58369] |
| **NONFX5** | **+3.38504** | **[−7.79979, +15.16782]** | **+6.90132** | **[−14.06004, +26.19852]** |

**Events (not IID):** DEV FULL33 8,605 signals, 262 active weeks; DIAG 3,427 signals, 104 weeks. Sector counts DEV crosses 5,481, majors 1,827, noFX 1,297; DIAG 2,184, 728, 515. Bounded exposure cap3 triggered 106/8,605 DEV (1.23%) and 57/3,427 DIAG (1.66%). No-FX five signals positive on point mean but both CIs cross zero, no proven sector edge, no opportunistic switching to only nonFX.

**Primary prereg gate FAIL**: full33 after cost must have *positive weekly mean* and **lower CI95 >0** in BOTH DEV and DIAG. Neither qualifies. **Exact status `FINAL_TSMOM_FAIL_CLOSE_FAMILY_ON_EXPOSED_DATA`**. This is the last TSMOM variant on 2016–2024: no 60/120/180d lookbacks, no sector-only cherry pick, no different cap/vol target or 'try another cost'. A positive nonFX5 mean does not reject null and must not be framed as 'documented edge'; another 5 nonFX holdout could require new independent data and multiple-testing safeguard. This also does NOT universally refute all futures trend following or all horizons.

### Statistical caution
Weekly 4week-bootstrap CIs are wide despite >12k event returns because co-movement/market clusters and week dependence reduce effective sample size. Both original source cohorts have unverified contract cash/point and trading calendars, so even volume-scaled return is a **dimensionless mark-to-mark cost scenario**, not realizable portfolio NAV. 1bp per side is a hypothetical fee/spread/slippage budget, not actual broker contract.

**Causal warning unchanged:** first native M5 OPEN can coincide with hypothetical midnight UTC decision, therefore not a physically demonstrated post-decision achievable order fill; current output is reference, not execution. No real BID/ASK, no available_at, commission/slippage/swap/funding or news-PIT and no virgin OOS. No Sharpe net, Profit Factor net, cash drawdown net or UTC001.

## Scientific program action

- CLOSE final TSMOM branch in exposed data regardless of user desire for a positive strategy; do NOT optimize the 2016–2024 panel.
- Independent XSREV5 reversal protocol was preregistered **in the same ancestor** before any of its outcomes; this is the **single complementary test**, not a hidden TSMOM fourth variant. Complete its QA/results separately, without survivor exclusion.
- Original12 and New21 archival legal private vault and restore (#837) remains P0 before first expiry **2026-12-16T00:21:18Z**, broker/source contracts (#868), actual source 33 bid/ask and NET/OOS (#852) remain blocked.
- Research isolated PR #840 DRAFT. **0/3 traders Alpha2 certified; 0 broker orders; NO VPS/MT5/Shared/CIBO/QDLE/PAPER/LIVE/MAIN.**
