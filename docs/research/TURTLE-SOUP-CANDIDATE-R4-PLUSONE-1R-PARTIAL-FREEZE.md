# Turtle Soup Candidate R4 — Plus One +1R Partial Preregistration

Status: **FROZEN BEFORE R4 ECONOMIC REPLAY**

Research identity: `turtle-soup-candidate-r4`

Parents: R1 forensic rejection, R2 protective-ratchet falsification, R3 bar-2 failure-exit falsification.

Canonical trader code: `CODE_UNASSIGNED`

## 1. Causal hypothesis

R1 showed that many losing Plus One reversals first achieved material favorable excursion. R2 showed that moving the stop to break-even after a +0.50R M15 close was too aggressive and suppressed winner participation. R3 showed that a non-favorable bar-2 close exit affected too few trades and did not repair the forward edge.

R4 tests one new proposition: monetize a meaningful favorable excursion first, then protect only the remaining balance.

This is `QORE_EXPERIMENTAL_MANAGEMENT`; it is not represented as a mechanical Connors/Raschke exit rule.

## 2. Source entry and initial stop unchanged

R4 preserves the exact R1 Plus One source detector and initial-stop logic:

- 20-period prior extreme;
- minimum reference age 3 source bars;
- breakout bar closes at/beyond the prior extreme;
- next-day stop entry at the earlier extreme;
- next-day order expiry;
- initial stop one tick beyond the two-bar/running adverse extreme;
- causal M15 execution with the governed targeted-M1 refinement only where source-entry ordering is otherwise ambiguous.

No side, market, year, session, volatility, or indicator filter is introduced.

## 3. Single frozen R4 management policy

Policy ID:

`R4_B2_6_TP1R_F50_BE_TRAIL2_H10`

Exact mechanics:

1. The source initial stop remains active from fill.
2. No profit-taking is permitted during management bar 1.
3. During management bars 2 through 6 inclusive, while no partial has yet executed, a one-time 50% take-profit level is fixed at exactly +1.00R from executable entry, where R is the immutable initial source risk.
4. LONG target = `entry + initial_risk`; SHORT target = `entry - initial_risk`.
5. On each native M15 bar in management bars 2–6, active-stop execution is evaluated first. If the active stop is touched in that M15 bar, the stop wins and no target fill is claimed from the same bar.
6. If the active stop is not touched:
   - if the M15 open has already gapped favorably through the +1R target, the 50% partial fills at the observed M15 open;
   - otherwise, if the M15 high/low reaches the +1R target, the 50% partial fills at the exact target price.
7. The partial executes at most once. It is not moved to another threshold and is not made up later if bars 2–6 never reach +1R.
8. After the 50% partial executes, the remaining 50% stop is ratcheted to the exact executable entry price, effective only from the **next native M15 bar**. No same-bar retroactive break-even stop is allowed.
9. After the partial, the remaining balance also receives the already-defined two-completed-D1-bar trailing stop. That daily trail may only tighten the stop and becomes effective on the following bar under the existing causal precedence.
10. If no +1R partial occurs by the end of management bar 6, the source initial stop remains active and no break-even ratchet is introduced merely because the window expired.
11. Hard time exit remains at management bar 10 for any remaining exposure.
12. Gap-through stop execution retains the conservative QORE observed-open fill convention.
13. Transaction cost remains external to trigger decisions and is applied by the unchanged research cost model.

There is no +0.5R/+1.5R/+2R grid, no alternate partial fraction, no alternate partial window, and no one-bar trail variant in R4.

## 4. Why +1R is admissible as a hypothesis value

R1 Forensics preregistered +0.25R, +0.50R, +1R and +2R as diagnostic MFE thresholds before interpreting losses. R4 chooses one of those already-declared diagnostic levels to formulate a new hypothesis after R1–R3. It does not compare those thresholds inside R4.

The value is therefore explicitly data-informed hypothesis generation, not claimed source authority. Its validity depends entirely on new forward development falsification under this R4 identity.

## 5. Data, folds, costs and embargo

R4 may consume only the already-governed development corpus:

- corrected D1 run `34947549114`;
- corrected M15 run `34947548876`;
- targeted M1 run `34959770555` only for previously governed source-entry ambiguity resolution;
- markets: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY.

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`

No post-embargo bar may participate in R4 implementation debugging by outcome, replay, metrics, or selection.

Primary cost = 1.0 bp all-in round trip.
Stress cost = 2.0 bp.

Forward folds remain exactly WF1..WF6 from R1.

## 6. Frozen advancement gate

R4 advances only if every condition holds across the six forward folds:

1. at least 30 closed trades;
2. primary-cost expectancy > 0R/trade;
3. primary-cost PF > 1.00;
4. at least 4/6 fold totals > 0R;
5. 2bp stress expectancy >= 0R/trade;
6. all seven leave-one-market-out forward totals > 0R;
7. no single market, calendar year, or side contributes more than 50% of positive forward gains;
8. no unresolved data/path ambiguity is counted as a realized trade;
9. forward total at 1bp must exceed the R1 `P_B2_F50_TRAIL2_H10` baseline forward total of `-12.0875R` and improve at least 4/6 fold totals versus that baseline. This relative criterion is secondary and cannot rescue failure of any absolute gate.

## 7. No rescue inside R4

If R4 fails, it is rejected. The target, partial fraction, window, trail length, hard exit, market universe, side universe, or costs may not be changed inside R4 to rescue it.

A different hypothesis requires a new identity and preregistration.

## 8. Authority

R4 grants no candidate approval, fresh-OOS release, FTMO/FundedNext qualification, DEMO/LIVE/production authority, or real-capital permission.
