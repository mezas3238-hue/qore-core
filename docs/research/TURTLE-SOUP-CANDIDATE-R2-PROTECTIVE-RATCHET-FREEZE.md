# Turtle Soup Candidate R2 — Protective Ratchet Preregistration

Status: **FROZEN BEFORE R2 ECONOMIC REPLAY**

Research identity: `turtle-soup-candidate-r2`

Parent evidence: `turtle-soup-candidate-r1`

Canonical trader code: `CODE_UNASSIGNED`

## 1. Why R2 exists

R1 is closed and rejected. It is not rewritten by this iteration.

R1 Plus One showed that the dominant losing population was not caused by the frozen partial/trailing implementation: for `P_B4_F50_TRAIL1_H10`, 75 of 80 primary-cost losses were source-entry/market-response losses that ultimately reached the source initial stop, while 45 of those 80 losers had previously achieved at least +0.50R MFE.

This observation generates one new management hypothesis. It does not authorize side filtering, market deletion, entry-rule changes, target mining, or holdout access.

Classic is **not** modified by this R2 hypothesis. Classic R1 remains rejected under the available resolution because its admissible forward sample is insufficient and negative, with 293 residual M1 intrabar ambiguities.

## 2. Immutable source entry

R2 Plus One preserves the exact R1 source detector and initial-stop logic:

- 20-period prior extreme;
- minimum reference age 3 source bars;
- breakout bar must close at/beyond the prior extreme;
- entry only on the next source day/bar at the earlier 20-period extreme;
- next-day order expires if not filled;
- initial stop remains one tick beyond the two-bar/running adverse extreme;
- causal M15 execution and the already-governed targeted-M1 ambiguity resolution remain unchanged.

No signal-side or market filter is introduced.

## 3. Frozen R2 hypothesis — M15 close protective ratchet at +0.50R

One and only one new protective rule is introduced:

1. Initial risk is `abs(executable_entry_price - initial_stop_price)` and is immutable for R accounting.
2. While the position is open, inspect each **fully closed native M15 bar** causally after the fill.
3. Compute directional close excursion:
   - LONG: `(m15_close - entry) / initial_risk`
   - SHORT: `(entry - m15_close) / initial_risk`
4. The first time that a completed M15 close is `>= +0.50R`, activate the protective ratchet.
5. The ratchet sets the candidate stop to the exact executable entry price.
6. It becomes active only for the **next** M15 bar; the bar whose close activates it cannot be retroactively stopped at entry.
7. The active stop may never loosen. If an R1 base-policy trail is already more protective than entry, retain the more protective stop.
8. A stop hit before an M15 close wins before any close-triggered ratchet update.
9. Gap-through stop execution keeps the existing conservative QORE observed-open fill rule.
10. The ratchet is gross break-even only; transaction cost remains charged separately by the frozen research cost model.

The +0.50R threshold is not optimized in R2. R1 already preregistered +0.25R, +0.50R, +1R and +2R as forensic measurement thresholds before loss interpretation. R2 selects exactly one hypothesis threshold and does **not** run a threshold grid.

## 4. Base management policies retained

The protective ratchet is overlaid independently on each of the six already-frozen Plus One base policies; their partial fraction, scheduled partial bar, daily trail lookback and hard exit remain unchanged:

- `R2_BE050_P_B2_F50_TRAIL1_H10`
- `R2_BE050_P_B2_F50_TRAIL2_H10`
- `R2_BE050_P_B4_F50_TRAIL1_H10`
- `R2_BE050_P_B4_F50_TRAIL2_H10`
- `R2_BE050_P_B6_F50_TRAIL1_H10`
- `R2_BE050_P_B6_F50_TRAIL2_H10`

No other R2 management family is permitted in this iteration.

## 5. Data and embargo

R2 reuses only the already-governed R1 development evidence:

- corrected D1 run `34947549114`;
- corrected M15 run `34947548876`;
- targeted M1 ambiguity-resolution run `34959770555` when required by the source detector;
- seven-market universe: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY.

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`

No post-embargo price may enter R2 hypothesis testing, selection, debugging by outcome, or policy ranking.

## 6. Costs and walk-forward remain frozen

Primary cost: `1.0 bp` all-in round trip.

Stress cost: `2.0 bp` all-in round trip.

The same six chronological forward folds are retained:

- WF1: 2024-09-01 -> <2024-12-01
- WF2: 2024-12-01 -> <2025-03-01
- WF3: 2025-03-01 -> <2025-06-01
- WF4: 2025-06-01 -> <2025-09-01
- WF5: 2025-09-01 -> <2025-12-01
- WF6: 2025-12-01 -> <2026-03-01

Fold assignment remains by executable fill timestamp.

## 7. Frozen R2 advancement gate

An R2 policy may advance only if all conditions hold on the six forward folds:

1. at least 30 closed trades;
2. primary-cost expectancy strictly > 0R/trade;
3. primary-cost profit factor strictly > 1.00;
4. at least 4 of 6 fold totals strictly > 0R;
5. 2.0 bp stress expectancy >= 0R/trade;
6. leave-one-market-out forward total remains strictly > 0R for all seven removals;
7. no single market, year, or side contributes more than 50% of total positive forward gains;
8. no unresolved data-integrity/path ambiguity is counted as a realized trade;
9. compared with its exact corresponding R1 base policy, R2 must improve primary-cost fold total in at least 4 of 6 folds; this relative comparison is secondary and cannot rescue failure of any absolute gate above.

If multiple R2 policies pass, selection remains deterministic: higher 2bp forward total, then higher 1bp forward total, then lower forward max drawdown, then higher worst-fold total, then lexicographically smaller R2 policy ID.

## 8. Interpretation discipline

R2 tests one causal proposition only: whether a completed-M15-close break-even ratchet at +0.50R prevents enough failed reversals from returning to the source initial stop to create a robust forward edge.

If all six policies fail, R2 is rejected. No threshold, side, market, partial bar, trail length, or hard exit may then be changed inside R2 to rescue it.

A subsequent hypothesis requires a new research/config identity.

## 9. Authority

This preregistration grants no candidate approval, fresh-OOS release, FTMO/FundedNext qualification, DEMO/LIVE/production authority, or real-capital permission.
