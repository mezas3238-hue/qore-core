# VT-31 R5/R6 Predecision Regime Walk-Forward

Status: consumed-evidence research only. R5 and R6 remain rejected identities. This report does not approve a new candidate and does not authorize DEMO, LIVE, FundedNext, FTMO, production, or real-capital execution.

## Purpose

The comparative R5/R6 forensic pass established that `risk/reference <= 0.175` is the strongest stable containment found in the original R5/R6 parameter family, but two rolling OOS folds remained negative. This follow-up asks whether a feature fully observable before entry can identify the adverse pockets prospectively without filtering by year, month, market, side, or realized outcome. Only the already-consumed R5/R6 fresh partitions are used.

## Stable research base

- signal at or before 10:20 NY;
- `risk/reference <= 0.175`;
- confirmation body >= 0.50;
- 2.0R research target;
- identical configuration across NAS100, SP500 and US30;
- protected-swing management retained;
- 0.05R friction retained.

## Predecision feature extraction

For every first executable Silver Bullet setup, decision-time instrumentation retained raid minute, minutes from initial raid to final raid extreme, raid-to-confirmation duration, raid depth/reference, raid candle body fraction, raid range/reference, confirmation range/reference, structural displacement/reference, retracement distance/reference, 10:00-open location, reference-range width, confirmation body fraction and risk/reference. Market, side and calendar labels were diagnostic only.

The strongest mechanism was the pair of raid-body conviction and raid-resolution speed. Weak-body raids and raids that kept extending for many minutes were disproportionately represented in the adverse OOS pockets.

## Fixed forensic witness

The predeclared witness before neighborhood testing was:

- raid candle body fraction >= 0.35;
- final raid extreme reached within 6 minutes of the initial raid.

Across consumed evidence it produced 256 executable trades, stressed mean +0.2438R/trade, PF 1.415, max DD 9.60R. All seven chronological six-month windows were positive. Fold results `(n, mean R, PF, DD R)` were: `(35,+0.349,1.644,5.48)`, `(15,+0.150,1.238,3.45)`, `(26,+0.107,1.167,9.51)`, `(34,+0.456,1.878,3.15)`, `(51,+0.068,1.103,9.60)`, `(34,+0.421,1.845,5.48)`, `(10,+0.450,1.857,3.15)`.

Market stability under the fixed witness: NAS100 93 trades, +0.240R/trade, PF 1.402; SP500 68, +0.231R/trade, PF 1.384; US30 95, +0.257R/trade, PF 1.454. Side stability: LONG 117, +0.284R/trade, PF 1.500; SHORT 139, +0.210R/trade, PF 1.348. Entry-family stability: breaker 120, +0.302R/trade, PF 1.524; fair-value-gap 110, +0.205R/trade, PF 1.345; order-block 26, +0.141R/trade, PF 1.232.

## Leakage-free finite-family rolling walk-forward

A train-only family over raid body minimum `{none,0.25,0.35,0.45}` and raid-to-extreme maximum `{none,3,4,6,8}` was selected on each 12-month training fold and frozen for the next six-month OOS segment. It produced 7/7 positive OOS folds, 217 concatenated OOS trades, about +0.264R/trade, PF 1.453 and DD 10.65R. NAS100, SP500, US30, LONG and SHORT were all positive in aggregate. Raid-resolution speed was more stable than the exact body threshold.

## Fixed-rule threshold-neighborhood robustness

After the `0.35 / 6-minute` witness had already been declared, a denser fixed-rule neighborhood was tested on consumed evidence only: body minimum `{none,0.25,0.30,0.35,0.40}` crossed with raid-to-extreme maximum `{4,5,6,7,8}` minutes. The purpose was robustness adjudication, not selection of the best in-sample point.

The central neighborhood is materially stable rather than a single-point optimum:

| Fixed rule | Trades | stressed mean R | PF | DD R | positive 6m windows |
|---|---:|---:|---:|---:|---:|
| body >=0.35, extreme <=4m | 213 | +0.265 | 1.459 | 8.70 | 7/7 |
| body >=0.35, extreme <=6m | 256 | +0.244 | 1.415 | 9.60 | 7/7 |
| body >=0.35, extreme <=7m | 261 | +0.242 | 1.412 | 10.56 | 7/7 |
| body >=0.35, extreme <=8m | 270 | +0.237 | 1.404 | 10.65 | 7/7 |
| body >=0.30, extreme <=4m | 223 | +0.233 | 1.396 | 9.75 | 7/7 |
| body >=0.30, extreme <=6m | 267 | +0.213 | 1.356 | 10.65 | 7/7 |
| body >=0.30, extreme <=7m | 272 | +0.212 | 1.354 | 10.65 | 7/7 |
| body >=0.30, extreme <=8m | 281 | +0.208 | 1.349 | 11.70 | 7/7 |

The isolated 5-minute boundary is less stable (for example body >=0.35 / <=5m gives 6/7 positive windows). That discontinuity argues against claiming a magic duration threshold. Instead, the broader 0.30-0.35 body / 4-8 minute neighborhood, excluding the isolated 5-minute path-sensitive boundary, supports the mechanism that decisive raids have better economics. The original predeclared `0.35 / 6` witness remains the fixed candidate rule; it was not replaced by the ex-post best cell.

## Censoring/sample-selection adjudication

The apparent benefit is not explained by a lower same-bar-censoring rate. On the pre-execution base, the unfiltered research set had 1,063 potential setups, 387 executable 2R outcomes and a 63.6% censored/non-executable rate. The fixed `0.35 / <=6m` rule had 764 potential setups, 256 executable outcomes and a 66.5% censored/non-executable rate. Nearby robust rules had essentially the same ~66.3-66.6% rate. The filter therefore does not manufacture its edge by selectively reducing censoring.

Among already executable base trades, the fixed `0.35 / <=6m` subset averages +0.244R/trade while the 131 executable trades it excludes average about -0.055R/trade. The `0.35 / <=7m` subset averages +0.242R while excluded executable trades average about -0.063R. This is consistent with genuine predecision path-quality separation rather than a favorable change in censoring cardinality.

## Forensic adjudication and consumed-evidence freeze

The fixed raid-resolution rule is **ROBUSTLY CONFIRMED on consumed evidence** for candidate engineering purposes. This does not constitute fresh validation or trader approval.

The causal working interpretation is that low-conviction / slow-resolving raids are more likely to be noisy two-way auction rather than the decisive manipulation/displacement sequence expected by the Silver Bullet model. The rule repairs the previously adverse R3/R5 pockets without deleting a market, side, or entry family and remains stable across markets, sides, entry families and a meaningful threshold neighborhood.

The next candidate identity is now predeclared as `VT31_R7_SILVER_BULLET_RAID_RESOLUTION_001`. Its fixed research-to-fresh rule inherits the stable base above and adds exactly `raid_body_fraction >= 0.35` and `raid_to_extreme <= 6 minutes`. R5 and R6 remain permanently rejected. R7 must be implemented and frozen on a new candidate branch, pass Full QORE, and then receive one genuinely earlier one-shot fresh partition with the existing stress, market, side, sample, drawdown and Monte Carlo gates. No fresh evidence may be inspected before that exact candidate freeze.