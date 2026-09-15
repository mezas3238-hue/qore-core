# VT-31 R5/R6 Predecision Regime Walk-Forward

Status: consumed-evidence research only. R5 and R6 remain rejected identities. This report does not approve a new candidate and does not authorize DEMO, LIVE, FundedNext, FTMO, production, or real-capital execution.

## Purpose

The comparative R5/R6 forensic pass established that `risk/reference <= 0.175` is the strongest stable containment found in the original R5/R6 parameter family, but two rolling OOS folds remained negative. This follow-up asks a narrower question:

> Can a feature that is fully observable **before entry** identify the adverse pockets prospectively, without filtering by year, month, market, side, or realized outcome?

The analysis uses only the already-consumed R5 and R6 fresh partitions. No new fresh partition was opened.

## Predecision feature extraction

For every first executable Silver Bullet setup, the replay was instrumented at decision time to retain only information already known before entry. Candidate observables included:

- raid candle minute inside the 10:00-11:00 NY window;
- minutes from initial raid to final raid extreme;
- minutes from raid to structural confirmation;
- raid depth relative to the 09:00-10:00 reference range;
- raid candle body fraction;
- raid candle range / reference range;
- confirmation range / reference range;
- displacement beyond the structural anchor / reference range;
- retracement-entry distance from confirmation close / reference range;
- 10:00 open location inside the reference range;
- reference-range width in basis points;
- existing confirmation body fraction and risk/reference containment.

Market, side, month and year were retained for diagnostics only and were not allowed to act as standalone regime filters.

The stable base for this pass was intentionally narrow and derived from the prior forensic closure:

- signal at or before 10:20 NY;
- `risk/reference <= 0.175`;
- confirmation body >= 0.50;
- 2.0R research target;
- identical configuration across NAS100, SP500 and US30;
- protected-swing management retained;
- 0.05R friction retained.

## Single-feature screen

No single newly extracted observable produced a sufficiently convincing train-selected walk-forward solution. Several retrospective fixed filters were interesting but were not treated as causal merely because they improved the consumed sample.

Two features repeatedly appeared near the top of training-only rankings:

1. **raid body fraction** — weak-body raids were disproportionately represented in the two adverse OOS pockets;
2. **raid-to-extreme duration** — setups where the raid kept extending for many minutes were less stable than raids that resolved quickly.

The second variable is especially important because it describes the geometry of the manipulation itself rather than a calendar or market label.

## Fixed forensic witness: raid body + raid resolution speed

A retrospective fixed witness, used only to understand mechanism, is:

- raid candle body fraction >= 0.35;
- final raid extreme reached within 6 minutes of the initial raid.

Applied on top of the stable base, across the consumed period:

- 256 trades;
- stressed mean about **+0.244R/trade**;
- PF about **1.415**;
- max DD about **9.60R**.

All seven chronological 6-month OOS windows are positive under this fixed witness. Because the exact `0.35 / 6-minute` pair was inspected on consumed evidence, this result is **not** fresh validation and is not by itself sufficient to freeze a new trader.

The mechanism is nevertheless informative. In the previously negative R3 fold (2020-05 through 2020-10), after requiring raid-to-extreme <=6 minutes:

- weak raid body `<0.35`: 18 trades, about **-0.217R/trade**, PF ~0.714;
- stronger raid body `>=0.35`: 26 trades, about **+0.107R/trade**, PF ~1.167.

The weak-body losses are concentrated in breaker/order-block executions and include substantial US30 weakness. In the previously weak R5 fold (2021-05 through 2021-10), the same split is again directionally favorable:

- weak raid body `<0.35`: 11 trades, about **-0.198R/trade**, PF ~0.729;
- stronger raid body `>=0.35`: 51 trades, about **+0.068R/trade**, PF ~1.103.

This supports the hypothesis that a material portion of the R5/R6 losses came from **low-conviction / slow-resolving manipulations**, not simply from SHORT, US30, order blocks, or a particular calendar month.

## Leakage-free finite-family rolling walk-forward

To avoid freezing the retrospective `0.35 / 6` witness directly, a finite train-only rule family was evaluated. Each 12-month training fold selected one pair before the subsequent 6-month OOS segment:

- raid body minimum in `{none, 0.25, 0.35, 0.45}`;
- raid-to-extreme maximum in `{none, 3, 4, 6, 8 minutes}`.

Selection required at least 50 training trades and at least 60% training-sample retention, and penalized drawdown plus market/side instability. The selected rule was frozen before each OOS segment.

| Fold | Train-selected predecision rule | OOS n | OOS mean R | OOS PF | OOS DD R |
|---|---|---:|---:|---:|---:|
| R1 | body none, extreme <=6m | 41 | +0.218 | 1.368 | 6.83 |
| R2 | body >=0.45, extreme <=6m | 9 | +0.283 | 1.486 | 2.10 |
| R3 | body >=0.35, extreme <=6m | 26 | +0.107 | 1.167 | 9.51 |
| R4 | body none, extreme <=6m | 47 | +0.486 | 1.954 | 4.20 |
| R5 | body >=0.35, extreme <=8m | 54 | +0.061 | 1.092 | 10.65 |
| R6 | body none, extreme <=3m | 32 | +0.412 | 1.817 | 4.67 |
| R7 | body >=0.45, extreme <=8m | 8 | +0.450 | 1.857 | 2.10 |

All **7 of 7** rolling OOS folds are positive in aggregate. The concatenated non-overlapping OOS result is:

- 217 trades;
- stressed mean about **+0.264R/trade**;
- PF about **1.453**;
- max DD about **10.65R**;
- NAS100: ~+0.230R/trade;
- SP500: ~+0.227R/trade;
- US30: ~+0.325R/trade;
- LONG: ~+0.296R/trade;
- SHORT: ~+0.238R/trade.

This is materially stronger than the prior rolling walk-forward that varied only cutoff/risk/body/target, where 5/7 OOS folds were positive and two adverse regime pockets remained.

## Interpretation

The strongest new forensic result is not a specific magic threshold. It is the repeated selection of a **fast raid resolution constraint**, often combined with a minimum raid-body conviction requirement.

Across the train-only folds:

- `raid-to-extreme` is repeatedly selected at 3-8 minutes, most often 6-8;
- the body threshold adapts more than the resolution-speed threshold;
- the pair corrects the previously negative R3 and R5 aggregate OOS folds without deleting a market, side, or entry family;
- aggregate OOS remains positive for NAS100, SP500, US30, LONG and SHORT.

The causal hypothesis is therefore now narrower:

> VT-31's weak regimes are associated with raids that do not resolve decisively. A raid that continues searching for an extreme for too long, especially when its initiating candle has a weak body, is more likely to represent noisy two-way auction rather than the clean manipulation/displacement sequence the Silver Bullet model expects.

This is a **predecision, geometry-based hypothesis**. It is materially better founded than filtering September 2020, US30 SHORT, or order-blocks after observing that they lost.

## Remaining limitation before a new candidate

The evidence is strong enough to justify continued candidate engineering research, but not yet to open fresh evidence immediately. Two cautions remain:

1. OOS sample sizes in R2 and R7 are small after the train-selected filter (9 and 8 trades).
2. The exact body threshold is not stable; it changes with the training regime, while raid-resolution speed appears more structurally stable.

Before defining the next candidate identity, the next forensic pass should determine whether a **single fixed, predeclared raid-resolution rule** (possibly with a conservative body condition) can preserve the 7/7 OOS sign stability with adequate per-fold sample and without creating new market/side weakness. That decision must be made entirely on consumed evidence, then frozen before any genuinely earlier fresh partition is opened.

R5 and R6 remain permanently rejected.