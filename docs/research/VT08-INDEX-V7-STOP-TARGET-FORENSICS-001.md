# VT-08 INDEX V7 — STOP / TARGET FORENSICS 001

Date: 2026-09-16

## Governance

This report uses only consumed evidence from V6 fresh holdout `[2020-09-15, 2022-09-15)`. That interval is permanently consumed and may not be called fresh again.

`LIVE_AUTHORIZED = FALSE`
`REAL_CAPITAL_AUTHORIZED = FALSE`
`PRODUCTION_AUTHORIZED = FALSE`

The analysis below is diagnostic. It may justify source-faithfulness and infrastructure corrections, but it may not be used to optimize parameters against this consumed interval and then relabel the same interval as fresh.

## Accepted operating corrections before this report

Owner-approved execution anchors for the next identity:

- executable: `22:00 / 02:00 / 06:00 / 10:00` New York
- `18:00`: daily-open/context only, never execution
- `14:00`: no execution

The 14:00 removal is operational, not economic: V6 produced zero 14:00 trades in the consumed holdout, so removing it changes no consumed metric.

SAME_C2 source correction:

- LONG continuation close must be strictly above active H4 open
- SHORT continuation close must be strictly below active H4 open
- otherwise abstain

This enforces `let the wick form, trade the body` without adding ATR, wick %, body ratio, or optimized geometry.

## Corrected consumed counterfactual (diagnostic only)

After excluding 18:00/14:00 execution and requiring SAME_C2 to be on the body side of H4 open:

Primary stress `-0.05R/trade`:

- sample: 336
- total: +82.8497175141R
- mean: +0.2465765402R/trade
- PF: 1.4144552298
- max DD: 12.00R
- winners: 145
- losses: 191
- max losing streak: 10

Secondary stress `-0.10R/trade`:

- total: +66.0497175141R
- mean: +0.1965765402R/trade
- PF: 1.3153479515
- max DD: 14.00R

This is NOT a holdout pass for V7.

## Stop-loss forensics

### Finding S1 — dominant V6 failure was entering SAME_C2 while still in the wick

After removing 18:00/14:00 but before the H4-body correction, V6 retained 444 trades.

The H4-body correction removes exactly 108 SAME_C2 trades that entered on the wrong side of the active H4 open.

Those 108 removed trades at `-0.05R/trade` produced:

- total: -29.40R
- mean: -0.272222R/trade
- PF: 0.65
- max DD: 33.90R
- winners/losses: 28 / 80
- max losing streak: 13

Conclusion: this is a structural implementation defect, not a target problem. The model was declaring the wick complete and executing before price had actually transitioned to the H4 body side.

### Finding S2 — remaining stops are mostly genuine protected-swing invalidations

In the corrected 336-trade stream:

- 190 trades exited by stop
- 144 exited by target
- 1 target-gap
- 1 holdout boundary mark

For the 190 stopped trades, using conservative stop-first M15 ordering:

- 103 / 190 (54.2%) never reached +0.5R before the stop
- 140 / 190 (73.7%) never reached +1.0R before the stop
- 50 / 190 (26.3%) reached +1.0R before later stopping
- 29 / 190 (15.3%) reached +1.25R
- 14 / 190 (7.4%) reached +1.50R
- 7 / 190 (3.7%) reached +1.75R

Interpretation:

Most losses did not fail because a 2R target was too far away. Nearly three quarters never reached 1R at all. In those cases price returned through the protected swing and invalidated the wick thesis before meaningful expansion developed.

### Finding S3 — stop failures are usually fast

Among the 190 stops:

- 26.3% stopped within 60 minutes of entry
- 50.5% stopped within 2 hours
- 71.1% stopped within 4 hours
- 88.4% stopped within 8 hours
- 95.8% stopped within 24 hours

Median time to stop: 120 minutes.

Conclusion: a large part of the loss population is immediate or same-session structural failure, again pointing to setup/confirmation quality rather than target distance.

### Finding S4 — model-family quality is not uniform

At `-0.05R/trade` after the accepted corrections:

`C2 closure -> next-H4 expansion`

- n = 40
- mean = +0.6000R/trade
- PF = 2.2698
- DD = 3.30R

`SAME_C2 intracandle`

- n = 289
- mean = +0.1979R/trade
- PF = 1.3235
- DD = 16.80R when isolated

`C3 closure -> next-H4 expansion`

- n = 7
- mean = +0.2357R/trade
- PF = 1.3929
- sample too small for a strong conclusion

Conclusion: completed C2 expansion is the cleanest family in this consumed sample. SAME_C2 remains profitable after the body correction but is the principal source of residual variance and stop clustering.

### Finding S5 — NAS100 remains the weakest market after the correction

At `-0.05R/trade`:

NAS100:

- n = 112
- mean = -0.00536R/trade
- PF = 0.9922
- DD = 14.40R

SP500:

- n = 109
- mean = +0.35963R/trade
- PF = 1.6506
- DD = 6.30R

US30:

- n = 115
- mean = +0.38478R/trade
- PF = 1.7024
- DD = 7.05R

This is a forensic warning, not permission to remove NAS100 post hoc. NAS100 must remain unless an independent source/causal rule justifies different treatment before a future fresh test.

### Finding S6 — shorts are weaker but still positive

LONG:

- n = 198
- mean = +0.35909R/trade
- PF = 1.6449

SHORT:

- n = 138
- mean = +0.08514R/trade
- PF = 1.1311

This is insufficient to justify removing shorts. It is retained as a stability diagnostic.

### Finding S7 — POI families

At `-0.05R/trade`:

CISD POI:

- n = 248
- mean = +0.26855R/trade
- PF = 1.4563

FVG POI:

- n = 73
- mean = +0.14178R/trade
- PF = 1.2240

Relevant-swing POI:

- n = 15
- mean = +0.39331R/trade
- PF = 1.7612

All are positive in consumed evidence. No POI family is removed.

## Target forensics

Official TTrades material explicitly supports both:

- a fixed 2:1 / 2R target; and
- higher-timeframe / logical-liquidity objectives when structure supports a larger target.

The 15-minute Fractal Model guidance states that after continuation entry with the stop beyond the protected swing, targets can be set at a fixed two-to-one or at higher-timeframe objectives. Other TTrades playbook material describes 2R as a minimum target/benchmark and uses higher-timeframe liquidity for extended R:R.

Therefore a fixed 2R target is source-compatible and may remain the deterministic V7 primary target. Structural higher-timeframe objectives may be retained as diagnostics/runners, but are not required to replace 2R before the next holdout.

The frozen V6/V7 2R target was stress-tested on the consumed corrected stream to determine whether 2R itself was causing the stop-loss problem.

All values below include `-0.05R/trade` friction and use the same 336 entry signals/stops.

| Fixed target | Total R | Mean R/trade | PF | Max DD |
|---|---:|---:|---:|---:|
| 0.75R | +5.95 | +0.0177 | 1.0433 | 14.35R |
| 1.00R | +39.20 | +0.1167 | 1.2667 | 11.60R |
| 1.25R | +40.95 | +0.1219 | 1.2422 | 15.15R |
| 1.50R | +47.20 | +0.1405 | 1.2554 | 17.00R |
| 1.75R | +67.95 | +0.2022 | 1.3536 | 14.50R |
| 2.00R | +82.85 | +0.2466 | 1.4145 | 12.00R |
| 2.25R | +99.60 | +0.2964 | 1.4830 | 11.45R |
| 2.50R | +92.35 | +0.2749 | 1.4221 | 17.15R |
| 3.00R | +88.54 | +0.2635 | 1.3752 | 14.00R |

### Target conclusion T1 — 2R is sufficient and not too ambitious

Lowering the target does not solve the loss mechanism. 1R and 1.5R both produce materially less expectancy than 2R in consumed evidence.

2.25R is numerically strongest in this consumed sample, but MUST NOT be selected from this table because that would be retrospective optimization.

Therefore:

- retain fixed 2R as the V7 primary deterministic target;
- do not lower 2R to cure stops;
- do not promote 2.25R based on consumed optimization;
- higher-timeframe liquidity objectives may be recorded as optional structural extension diagnostics, not as a post-hoc replacement target.

### Target conclusion T2 — trade management can reduce DD but costs expectancy

Diagnostic dual-target test, 50% at 1R and 50% runner to 2R:

Without moving the remaining stop to breakeven:

- total: +61.02R
- mean: +0.18162R/trade
- PF: 1.4082
- DD: 11.00R

With remaining stop moved to breakeven after 1R:

- total: +49.20R
- mean: +0.14643R/trade
- PF: 1.3347
- DD: 9.50R

This demonstrates a return/DD tradeoff, not a free improvement. No partial/breakeven policy is adopted for V7 because it is unnecessary to repair the identified failure and would add a new management degree of freedom.

## Critical infrastructure finding I1 — nominal holdout did not actually trade its first ~10 months

The V6 holdout partition is `[2020-09-15, 2022-09-15)`, but the first generated V6 trade occurred only on `2021-07-28`.

Root cause:

The daily-source reconstruction calls `_aggregate_contiguous_m15(... count=92)` from 18:00 NY through 17:00 NY. Before `2021-07-26`, the cTrader CFD history has a regular missing M15 slot at `16:15 NY`.

Measured across days with otherwise complete history before 2021-07-26:

- NAS100: 244 / 244 eligible source days missing 16:15 NY
- SP500: 244 / 244 eligible source days missing 16:15 NY
- US30: 244 / 244 eligible source days missing 16:15 NY

Because one maintenance-gap bar was absent, the contiguous 92-bar aggregator rejected the entire source day. As a consequence, daily bias could not be built and V6 produced zero signals for the early part of the nominal holdout.

This is a P0 infrastructure bug for any older holdout.

### Required V7 infrastructure correction I1

Reconstruct the 18:00 -> 17:00 NY source day from actual available broker M15 bars inside the window, while:

- preserving exact first/last session boundaries;
- allowing only documented broker maintenance gaps;
- never synthesizing OHLC for a missing maintenance interval;
- rejecting days with unexplained/large data gaps;
- recording bar count and gap timestamps in provenance.

This correction is data/session handling only and must not depend on trade profitability.

The `[2018-09-15, 2020-09-15)` fresh holdout MUST NOT be opened until this correction is implemented, tested and hardening is green. Otherwise the candidate could silently abstain through large portions of the period and the holdout would be invalid.

## Current forensic decision

1. 18:00 execution defect: CONFIRMED and removed.
2. 14:00 execution: owner-disabled; zero consumed V6 trades, therefore no economic tuning effect.
3. SAME_C2 pre-body execution defect: CONFIRMED and removed.
4. Protected-swing stop placement: retained. TTrades treats the protected swing as the structural invalidation level; most remaining stops fail before +1R, so widening the stop is not supported.
5. Fixed 2R target: CONFIRMED source-compatible and quantitatively sufficient; retain for V7.
6. 2.25R: diagnostic only; prohibited as a retrospective optimization choice.
7. Partial/breakeven management: not adopted; it reduces DD but also reduces expectancy and is not required to repair the root cause.
8. Daily-source aggregation maintenance-gap bug: CONFIRMED P0 and must be fixed before any older fresh holdout.
9. Next fresh interval remains `[2018-09-15, 2020-09-15)` only if deterministic evidence is available after the source-day fix and candidate freeze.
