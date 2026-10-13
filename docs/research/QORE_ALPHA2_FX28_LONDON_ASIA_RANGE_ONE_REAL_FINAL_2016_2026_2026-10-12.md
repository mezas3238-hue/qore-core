# QORE-Alpha 2 — FX28 Asia range -> London expansion: one PREDECLARED native intraday model, genuine original-M5 economic test, FINAL

**Closure: 2026-10-12 Paraguay / 2026-10-13 UTC.**

**FINAL SCIENTIFIC STATUS: `SESSION_EXPANSION_PREDECLARED_SCREEN_FAILED_STOP`.** This is a failure of the **specific frozen 00–07 London-local Asian range / 08–09:45 first confirmed close breakout / 10min price reference entry / 12:00 exit** mechanism under the frozen 2bps each-side assumed cost, not a proof every London intraday mechanism has no alpha. QORE Alpha2 still has **zero broker-NET demonstrated edges, zero certified traders, zero real orders**. Source period is already exposed, no virgin OOS. PR #840 remains DRAFT (unmerged).

## 1. Before outcome: one hypothesis with irreversibility

**PRE-RESULT freeze ancestor Git commit `b0133535d6adb89724b827e9151c4ab7a109c154`**, [original prereg](QORE_ALPHA2_FX28_LONDON_ASIA_RANGE_EXPANSION_ONE_FROZEN_PREREG_2026-10-12.md). New *intraday session liquidity* investigation, separate from the closed **TSMOM**, **XSREV5** and **BIS FX policy carry** families. Reference academic grounding for regional FX intraday return/volatility features: Zhang 2018 doi:10.1016/j.frl.2018.02.017, **NOT** an empirical claim this precise London breakout is profitable nor a TTrades/ICT reproduction.

- Exactly **28 source FX pairs** (K8 complete graph AUD,CAD,CHF,EUR,GBP,JPY,NZD,USD); 7 original Atlas +21 original ICMarkets; **11-year historical native M5 SHA + QUALITY originals** verified against previously signed original33 archive before any OHLC processing, source prices never uploaded.
- **IANA `Europe/London`** DST-aware clock for each UTC-native M5 source timestamp, local weekday. Asian high/low from exactly **84 original 5min bars 00:00–06:55** London; trading/exit evidence exactly **48 native 5min bars 08:00–11:55**. Missing any bar => day untradeable, **no imputation**, no posthoc missing-date selection. Ignore 07:00–07:55.
- Scan bar START 08:00→09:45, first **COMPLETED M5 close** outside Asian range; close above high => LONG, close below low => SHORT, **one position per symbol/day**, never both. Entry **next+one additional M5 OPEN at breakout bar START+10minutes** (breakout close at START+5, 5min causal delay), exit close of **11:55 native M5** (12:00 London). No stop/TP/sweep/ICT discretionary condition.
- Exactly **fixed 1/28 nominal per market ex ante**, not retrospectively dividing by the set of active signals. Ineligible/nonbreakout pairs remain uninvested cash. Per reference event `gross_bps=direction*10000*(M5_EXIT_CLOSE/M5_ENTRY_OPEN−1)`; portfolio daily return `Σ(events_gross−4bps)/28`. Hypothetical 2bps each side =4bp RT symbol event, stress5bp each side=10bp RT; realized spread, margin, FX quote base-USD normalization, slippage, stop and broker NAV missing. Zero swaps presumed in intraday hold, NOT broker verified. Neither gross nor gross−assumed cost qualifies as broker NET.
- Calendar London-local ISO weeks including **cash=0 weeks**; synchronized **circular blocks of four consecutive ISO weeks** B2000 seed `20261012+i` by era; **52 active-signal week minimum in DEV and DIAG**; provisional exploratory PASS required `weekly portfolio mean after cost >0` **and lower CI95 >0 in both eras**. DEV original 2016-09-17..2021-12-31, DIAG 2022-01-01..2026-09-16. Prior Alpha2-retained 2024-09-17..2026-09-16 separately, **not true OOS**, since FX carry VOL20 already read it.

## 2. Authenticated executable research facts and historical data integrity

- [**GitHub Actions #38330184319**](https://github.com/mezas3238-hue/qore-core/actions/runs/38330184319): **COMPLETED SUCCESS**, complete workflow SHA exactly `b8488541db771cefce0591cccae3e618f711a569`, tests + M5 market panel jobs green; synthetic causality/London DST/entry latency/missing M5/static1/28/cost/cutoff suite **8/8 PASS** and Ruff PASS. Original 28 11-year provider original RAW and QUALITY SHA validated, 7/7 Atlas &21/21 ICMarkets extraction green. **0 orders**.
- Source ingestion always original M5 with `opened_at` UTC, original integer relative OHLC `open_relative/high_relative/low_relative/close_relative`; no synthetic time expansion, forward points or provider fill. `src/qore/research/alpha2_fx28_london_range_one.py` produces only signed derived per-London-session events in **ephemeral** private GitHub Actions runner directory, source archive itself not uploaded.
- Original **final artifact #11782641612** `alpha2-FX28-LONDON-ASIA-ONE-2016-2026-AGG-b8488541db771cefce0591cccae3e618f711a569`; GitHub official ZIP **SHA256 `43c4ced2dd1c36566b46696228790d9c12cb5ed95ecf67ff3565ed1a2c482b09`**, independent download and actual ZIP SHA verification **PASS**. ZIP CRC `testzip()` PASS; JSON inside SHA256 **`862c026265b4ccc289f309753908e63c49ddcc7cf811f22d1826586007ed512c`** and exact source head text SHA256 **`a97ce7862180a6c6109db656421ad80a4d17492e3433ecb04d6e6f131e277229`** both independently rehashed PASS vs original `OUTPUT_SHA256SUMS.txt`; actual head text matches code commit `b8488541...`.
- **Independent analysis of every exported ISO week**, all 277 DEV/247 DIAG/105 retained records: no mismatch between (gross−4×sum(active static weights)) and net-cost proxy, nor between gross−10×static event weights and stress proxy; count positive-signal weeks and trade counts matched engine summary exactly; per-era weekly arithmetic means recomputed from weekly arrays, and **all three CI95 recomputed from the raw derived weekly portfolio vector with a fresh Python implementation of the exact 4week circular bootstrap B2000 seeds** agreed to <1e−8bps. Data and code audit is independent of the report.
- Earlier [Actions #38329353444](https://github.com/mezas3238-hue/qore-core/actions/runs/38329353444) achieved the same historical negative PnL computation but failed *after economics* due an incorrect output SHA folder `policy-panel` rather than `session-panel`; the only later edits were output derived weekly vector publication and workflow path fix. The two original economic means **exactly reproduced** at `b8488541...`, no signal, cost or parameter was changed as a function of outcome.

## 3. REAL 11year economic outcomes — bps per **whole calendar ISO week**, original 28 concurrent sources

| Predeclared outcome | DEV 2016–21 | DIAG 2022–26 | Previously exposed 2024–26 |
|---|---:|---:|---:|
| **calendar ISO weeks incl zero cash** | **277** | **247** | **105** |
| **weeks with ≥1 genuine M5 reference signal** | **276** | **246** | **105** |
| Intraday **trade reference events** | **28,172** | **24,083** | **10,043** (included in DIAG) |
| London days with any signal | 1,362 | 1,201 | 515 |
| Market-symbol days censored missing full M5 sessions | 500 | 783 | 186 |
| Market-symbol days with complete M5 but no breakout-close | 9,912 | 9,489 | 4,358 |
| **Portfolio GROSS reference mean bps/week** | **+0.46794** | **−0.32934** | **−1.66809** |
| **Gross minus assumed 2bp/side mean bps/week** | **−14.06120** | **−14.25820** | **−15.33203** |
| **Independent synchronized block4 CI95 bps/week** | **[−15.90402,−12.33552]** | **[−16.79919,−11.75644]** | **[−18.29051,−12.38564]** |
| 5bp/side **stress** mean bps/week | −35.85491 | −35.15149 | −35.82795 |
| **Model-only** compounded peak-to-trough weekly drawdown | 32.3963% | 29.7326% | 14.9304% |
| Worst model weekly bps | −58.56479 | −101.24801 | −96.60008 |
| Frozen minimum 52 active weeks DEV/DIAG | PASS | PASS | descriptive |
| Mean + CI95 lower >0 | **FAIL** | **FAIL** | **FAIL** |

**All predeclared signal sample gates PASS**. There is no underpower excuse. **Both** pre-cost reference means in the full 2016–26 primary split are close to zero (+0.47 DEV; −0.33 DIAG); *assumed* transaction costs swamp the tiny or negative gross reference. All three after-cost CIs are **entirely negative**, not just crossing zero. Even if broker pricing were cheaper than 2bp/side, this concrete delayed-entry trade has not shown a strong **gross** premium either, so cost refinement cannot rehabilitate the original gate. Stress 5bp per side worsens losses substantially.

**Important economic limitation:** Because nominal =1/28 per market, event counts measure candidate reference signal frequency, not 52,255 real venue fills or independent currency-risk bets. The 28 pairs share only 8 currencies and quote currencies differ; the bps summation is a dimensionless reference portfolio **not a USD equity broker backtest**. **Model drawdown** is an exploratory return-compounding statistic, *not* certified account drawdown or live expected risk. Missing M5 session days are excluded without imputing, which can introduce source-quality selection bias. No historical PIT BID/ASK or time-to-fill.

## 4. Decision / next architect

**`SESSION_EXPANSION_PREDECLARED_SCREEN_FAILED_STOP`**. The precise 00–07 London range, confirmed break 08–09:45 + causal 10min entry and noon exit in 28 native FX does **NOT** exhibit economically positive follow-through after assumed 2bps/side, despite ample observations. Closed irrevocably on consumed source 2016–26: do not optimize breakout timestamp, Asia end, entry delay, gross weight, per-market subsets, EUR crosses only, no-GBP filter, week segment, 2bps cost, adding discretionary ICT / TTrades conditions, or select profitable 2024 weeks posthoc. This does **not** prove all intraday session anomalies false, nor establish a universal effect-zero claim. The literature that FX regional returns vary by trading hour is not a claim of net profitability of an Asian-range London breakout.

**Strategic direction:** QORE-Alpha2 has exhausted more than one precisely scoped FX-native mechanism on 2016–2026. Document economically negative evidence and consider (i) truly new independent data/future OOS with a tightly justified *new* mechanism and broker cost feasibility, or (ii) a distinct diversified universe aligned with literature risk premia — decision requires economic/practical owner authorization, not endless retrospective feature scans. Legacy carried hypotheses / forward1m still retain their own explicit statuses, and are not overwritten. No newly certified trader, no PROD, VPS/MT5/CIBO/Shared/QDLE/PAPER/LIVE.

Scientific tracking [issue #891](https://github.com/mezas3238-hue/qore-core/issues/891) and Alpha2 research [PR #840](https://github.com/mezas3238-hue/qore-core/pull/840) (DRAFT). Original licenses/custody [#837](https://github.com/mezas3238-hue/qore-core/issues/837), broker execution/points [#852](https://github.com/mezas3238-hue/qore-core/issues/852) and instrument identities [#868](https://github.com/mezas3238-hue/qore-core/issues/868) are distinct source safety requirements, not reasons to relabel this failed PnL as success.
