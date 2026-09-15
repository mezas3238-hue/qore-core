# VT-31 R5/R6 Comparative Forensics + Walk-Forward

Status: research evidence only. R5 and R6 remain rejected identities. No DEMO/LIVE/FundedNext/FTMO/production authorization is granted by this report.

## Frozen evidence

- R5 candidate: `VT31_R5_SILVER_BULLET_QUALITY_001`
  - exact SHA: `c62f37c3b35324022011e6dabacbf29872708332`
  - fresh run: `34925899014`
  - fresh artifact: `10380044761`
  - artifact digest: `sha256:828335b99cd51c663e3f0f095df5137e881da3d7e8da741da8ca116a0400edf8`
- R6 candidate: `VT31_R6_SILVER_BULLET_DD_CONTROL_001`
  - exact SHA: `20c7f11e1a5b295b0b9cb5347c4fb29f834f17e7`
  - fresh run: `34949011914`
  - fresh artifact: `10389112524`
  - artifact digest: `sha256:9b0f3a05dc76b5dd83e5e3610266484bee1b79595dbbaacdff1d799115ad58b9`

The raw fresh market-evidence files and trade-level replays were reproduced locally before walk-forward analysis. The reproduction matches the published fresh metrics exactly.

## Reproduced fresh baselines

| Candidate | Trades | Stressed mean R | PF | Max DD R |
|---|---:|---:|---:|---:|
| R5 | 220 | +0.107435 | 1.170925 | 16.2630 |
| R6 | 124 | +0.023805 | 1.038713 | 13.4776 |

Applying the old R5 geometry to the earlier R6 partition produces 154 trades, stressed mean about -0.09734R, PF about 0.85736 and DD about 22.04R. R6 therefore materially improved the earlier regime, but did not restore enough edge to pass its frozen gates.

## Factorial forensic ablation

A complete `2 x 2 x 2 x 2` same-evidence ablation was run over:

- signal cutoff: 10:15 vs 10:20 NY;
- initial risk / 09:00-10:00 reference: 0.25 vs 0.175;
- confirmation body fraction: 0.50 vs 0.60;
- target: 1.7R vs 2.0R.

All comparisons retain identical market set, side set, entry families and protected-swing management.

Across the two disjoint consumed partitions, the strongest repeatable effects were:

1. `risk/reference <= 0.175` improved all paired comparisons in the first three major chronological windows and 6/8 paired comparisons in the final window. This is the most stable lever.
2. 10:20 cutoff generally outperformed 10:15, but failed consistently in the 2020H2-2021H1 window. It is regime-dependent rather than universally causal.
3. 2.0R generally outperformed 1.7R, but also failed consistently in the 2020H2-2021H1 window. It is regime-dependent.
4. body >= 0.60 is unstable. Its sign changes by window and cannot currently be treated as a robust causal filter.

For the R6 geometry specifically, restoring 2.0R on the earlier R6 partition yields 138 trades, stressed mean +0.09120R, PF 1.14488 and DD 8.168R versus frozen R6 at 1.7R: 124 trades, +0.02380R, PF 1.03871 and DD 13.478R. This is forensic evidence only; it does not retune R6.

## Leakage-free anchored walk-forward

Finite search space: the 16 predeclared factorial configurations above. Parameters are selected only from the training period and frozen before the subsequent OOS period.

| Fold | Frozen config `(cutoff,risk,body,target)` | OOS n | OOS mean R | OOS PF | OOS DD R |
|---|---|---:|---:|---:|---:|
| A1: train through 2019-06, test 2019-07..2020-06 | `(20,0.175,0.60,2.0)` | 58 | +0.0746 | 1.118 | 7.73 |
| A2: train through 2020-06, test 2020-07..2021-06 | `(20,0.175,0.60,2.0)` | 84 | +0.0650 | 1.099 | 13.71 |
| A3: train through 2021-06, test 2021-07..2022-07 | `(20,0.175,0.60,1.7)` | 86 | +0.2554 | 1.481 | 6.75 |

All three anchored OOS folds are positive in aggregate. However, market/side internals are not uniformly positive in every fold, so this is not sufficient for candidate approval.

## Leakage-free rolling walk-forward

Rolling design: 12 months train -> next 6 months OOS, chronological and non-overlapping OOS windows.

| Fold | Frozen config | OOS n | OOS mean R | OOS PF | OOS DD R |
|---|---|---:|---:|---:|---:|
| R1 | `(20,0.175,0.60,2.0)` | 40 | +0.0243 | 1.037 | 7.73 |
| R2 | `(20,0.175,0.50,2.0)` | 24 | +0.1133 | 1.183 | 5.25 |
| R3 | `(20,0.175,0.50,2.0)` | 49 | -0.0617 | 0.912 | 14.91 |
| R4 | `(20,0.175,0.60,1.7)` | 34 | +0.4588 | 1.990 | 3.15 |
| R5 | `(20,0.175,0.60,1.7)` | 47 | -0.0080 | 0.988 | 8.70 |
| R6 | `(20,0.175,0.60,1.7)` | 36 | +0.4185 | 1.925 | 5.18 |
| R7 | `(20,0.175,0.60,2.0)` | 19 | +0.3711 | 1.671 | 6.45 |

Five of seven rolling OOS folds are positive; two are negative. The non-overlapping rolling OOS aggregate is:

- 249 trades;
- stressed mean +0.15264R/trade;
- PF 1.25683;
- max DD 14.913R;
- NAS100: 82 trades, +0.18364R mean;
- SP500: 81 trades, +0.22319R mean;
- US30: 86 trades, +0.05664R mean;
- LONG: 111 trades, +0.23535R mean;
- SHORT: 138 trades, +0.08611R mean.

The optimizer selected `cutoff=20` and `risk/reference=0.175` in every rolling fold. Body and target switched with regime. This is strong evidence that the risk/reference containment is structurally more stable than the body threshold or fixed target choice.

## Regime-level loss forensics

The two negative rolling OOS folds were decomposed by month, market/side and entry family.

### R3 OOS: 2020-05 through 2020-10

Frozen config: `(20,0.175,0.50,2.0)`.

- 49 trades, -0.0617R/trade, PF 0.912, DD 14.91R.
- The loss is highly concentrated in September 2020: 8 trades, -1.039R/trade, -8.31R total.
- US30 SHORT is the largest market/side loss pocket: 10 trades, -0.45R/trade, -4.50R total.
- Order-block entries are weak: 6 trades, -0.55R/trade, -3.30R total.
- Fair-value-gap entries remain positive: 18 trades, +0.14R/trade, +2.53R total.

This fold is not a broad collapse of every market or entry family; it is a concentrated adverse regime with meaningful US30 SHORT and order-block contribution.

### R5 OOS: 2021-05 through 2021-10

Frozen config: `(20,0.175,0.60,1.7)`.

- 47 trades, -0.0080R/trade, PF 0.988, DD 8.70R.
- The negative months are June (-3.60R) and September (-4.65R); October recovers +6.15R.
- LONG remains strongly positive: +0.412R/trade in the rolling fold summary.
- SHORT is the primary failure mode: -0.447R/trade in the rolling fold summary.
- SP500 SHORT: 9 trades, -0.708R/trade, -6.38R total.
- US30 SHORT: 8 trades, -0.375R/trade, -3.00R total.
- NAS100 LONG and SP500 LONG remain positive.

This fold is therefore a directional/regime interaction, not a universal Silver Bullet failure.

### Why target and body rules reverse sign

In the 2020H2-2021H1 chronological window, the body >=0.60 tranche is negative while the 0.50-0.60 tranche is positive. A stronger-looking confirmation candle therefore does not monotonically imply better economics.

The target comparison also changes the executable sample because QORE censors unknown intrabar paths. A smaller 1.7R target can create a same-bar target/stop ambiguity that is censored, while 2R can survive that bar and later produce a valid loss, and vice versa. Therefore target changes affect both payoff and censoring cardinality. Target comparisons must be treated as execution-path effects, not only as a simple reward/risk scalar.

Within 2020H2-2021H1, 2R loses against 1.7R primarily through a small number of path-sensitive reversals: four trades that are winners at 1.7R fail under 2R, with about -10.6R aggregate delta, plus additional 2R-only executable cases that are net negative. In the later 2021H2-2022H1 regime, this relation reverses and 2R is materially superior.

The stable result remains the risk/reference filter: wide-risk trades above 0.175 are strongly negative in the adverse 2020H2-2021H1 regime, while the <=0.175 subset stays positive.

## Full consumed-period fixed-configuration diagnostic

The fixed configuration `(20, 0.175, 0.60, 2.0)` across the entire consumed 2018-05..2022-07 evidence gives:

- 321 trades;
- stressed mean +0.18000R/trade;
- PF 1.29809;
- max DD 13.713R;
- NAS100 +0.1987R mean;
- SP500 +0.2583R mean;
- US30 +0.1000R mean;
- LONG +0.2853R mean;
- SHORT +0.0853R mean.

This is retrospective consumed-evidence evidence only. It must not be treated as fresh validation and must not reuse R5 or R6 identity.

## Current forensic adjudication

- The R5/R6 failure is not explained by LONG vs SHORT alone.
- It is not explained by a single clock-minute filter alone.
- `risk/reference <= 0.175` is the strongest currently supported structural containment: it is selected in every rolling fold and remains beneficial across almost every chronological comparison.
- body >=0.60 is not a stable causal lever.
- cutoff 10:20 is generally useful but is regime-sensitive.
- target 2R is generally useful but is regime-sensitive and interacts with same-bar censoring/execution path.
- The two negative walk-forward folds are concentrated rather than universal: one is dominated by a September-2020 / US30-SHORT / order-block pocket; the other is dominated by SHORT weakness in SP500/US30 during selected 2021 months.
- This supports a regime-interaction hypothesis, but it does not yet justify deleting markets, sides or entry families. Any such rule would require a source-grounded or predecision observable that predicts the adverse pocket prospectively.

No new candidate should be frozen until the adverse-regime pockets are tied to a predecision observable that survives additional chronological validation. Any next candidate must receive a new identity and a genuinely earlier unseen holdout; R5 and R6 remain permanently rejected.
