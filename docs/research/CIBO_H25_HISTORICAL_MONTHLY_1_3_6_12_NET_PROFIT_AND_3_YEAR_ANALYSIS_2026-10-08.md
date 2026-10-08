# CIBO H25 — NET EARNINGS AFTER 1, 3, 6, AND 12 CALENDAR MONTHS

**Date**: 2026-10-08  
**Status**: GitHub Actions full historical replay **SUCCESS** / research only, not live-certified.  
**Verifiable run**: https://github.com/mezas3238-hue/qore-core/actions/runs/37785232285  
**Artifact**: `11553932025`, `qore-cibo-h25-historical-gains-calendar-37785232285`, including both 3,368-trade replay ledgers and complete JSON horizon report.  
**Source**: unchanged canonical CIBO code, same frozen historical 2019-07 through 2022-06 manifest; nominal 5% stop-risk research, USD60 starting capital. H21=highest terminal-capital sovereign-valid; H24=lowest observed drawdown sovereign-valid.

## Question answered — profits accumulating from July 1, 2019

The period endpoints are UTC calendar boundaries. Every entry is actually managed by original CIBO, provider costs in the original simulator already subtracted, money from `trade_receipts[].realized_net_pnl_usd` grouped by `realized_exit_at`. Capital is *realized-settlement-only* proxy: it ignores floating PnL at the boundary.

| Horizon | H21 NET USD | H21 SETTLED BALANCE USD | H24 NET USD | H24 SETTLED BALANCE USD | Closed receipts |
|---|---:|---:|---:|---:|---:|
| First **1 month** (July 2019) | **+$8.50** | $68.50 | **+$8.50** | $68.50 | 83 |
| First **3 months** (Jul–Sep 2019) | **+$30.67** | $90.67 | **+$31.58** | $91.58 | 265 |
| First **6 months** (Jul–Dec 2019) | **+$32.39** | $92.39 | **+$31.83** | $91.83 | 544 |
| First **12 months** (Jul 2019–Jun 2020) | **+$408.14** | $468.14 | **+$407.87** | $467.87 | 1,109 |

**Important**: These are NOT four separate USD60-funded replays. These are four cumulative elapsed horizons in **the same full continuously compounded original 3-year CIBO replay**. PnL cannot be interpolated, extrapolated linearly or presented as guaranteed monthly earnings. First-year profits vary drastically within the year.

## Three distinct consecutive annual profits in that same running account

| Calendar year of the replay | H21 NET USD | H24 NET USD |
|---|---:|---:|
| Year 1, July 2019–June 2020 | **+$408.14** | **+$407.87** |
| Year 2, July 2020–June 2021 | **+$892.23** | **+$864.97** |
| Year 3, July 2021–June 2022 | **+$2,228.89** | **+$1,971.52** |
| **Three-year total** | **+$3,529.26** | **+$3,244.37** |
| Ending cumulative account after starting $60 | **$3,589.26** | **$3,304.37** |

Profits for year 2 and year 3 depend on the balance already compounded from earlier years; these are not independent fresh USD60-funded tests.

## Month-to-month variation: why first month is not a predictable monthly wage

Across 36 months, **9 months recorded net losses** in each version:
- H21: median rolling 1-month profit **+$43.73**, worst **−$455.13** in May 2022, strongest **+$733.39** in March 2022.
- H24: median rolling 1-month profit **+$40.23**, worst **−$431.12** in May 2022, strongest **+$676.63** in April 2022.

These rolling windows **do not restart from $60**. They describe the running historical account at very different sizes. Every month trades its prevailing available capital. No annual income promises.

Other overlapping rolling-window medians (not independent fresh accounts):

| Rolling window | H21 median net | H24 median net | Windows with negative PnL |
|---|---:|---:|---:|
| 1 month | $43.73 | $40.23 | 9/36 (both) |
| 3 months | $198.26 | $195.16 | H21 2/34, H24 3/34 |
| 6 months | $489.43 | $491.21 | 0/31 (both) |
| 12 months | $941.19 | $949.88 | 0/25 (both) |

## Risk integrity and why results are NOT real funded profits

- H21: **3368/3368 managed**; max DD **34.35372258%**, internal bank floor breach **0**.
- H24: **3368/3368 managed**; max DD **33.54132539%**, internal bank floor breach **0**.
- Both **FAIL** owner's target DD <=25% (ideal <=20%). More research and blind validation are required.
- These are original CIBO USD60 historical *research* provider expenses, **NOT** a confirmed FundedNext Stellar Instant $2000 account, $14/lot round-trip broker fees or authentic margin/leverage/minimum lot / MTM liquidation. Do not report as real tradable dollars.
- The repeated optimization history uses the same 2019–2022 set, and is NOT independently fresh out-of-sample certification.
- Compounding is already inside the original CIBO methods; no new mathematical ROI simulation was substituted.
- At calendar boundary, unrealized PnL of open trades is **not** observed by this closed-settlement report. The displayed account balances are closed-settlement proxies, not actual broker equity snapshots.

## Reproducibility
- The new H25 workflow `.github/workflows/cibo-trader-lab-h25-realized-gains-by-period.yml` reruns **both full 3368-entry original-engine cases** from source inputs and includes original Atlas, and verifies matching terminal balances and zero internal sovereign breach.
- The new script `scripts/cibo_h25_historical_time_horizon_audit.py` computes date-bounded receipt aggregation, calendar-rolling windows, 3 annual partitions, checks no missing receipt and verifies `USD60 + sum(net receipts) == ending capital` with Decimal precision.
- Workflow stdout: **`CIBO_H25_HORIZONS_RECONCILED_TWO_FULL_REPLAYS=YES`**, and action conclusion SUCCESS.
- Artifact `h25-1-3-6-12-month-net-performance.json` contains 36 months and all rolling windows, and both full source replay JSONs.

**Executive conclusion:** At the initial $60 over the first 12 calendar months, CIBO produced about **+$408 net modeled** (ending around $468), with limited first 6mo +$32, a large year-one ramp, zero bank-floor breach but unacceptable ~33–34% max 3-year DD. These are conditional historical model outputs, not assured/real funded income.
