# Turtle Soup Candidate R3 — Bar-2 Failure Exit Preregistration

Status: **FROZEN BEFORE R3 ECONOMIC REPLAY**

Research identity: `turtle-soup-candidate-r3`

Parents: R1 forensic rejection + R2 protective-ratchet falsification.

Canonical trader code: `CODE_UNASSIGNED`

## 1. Causal hypothesis

R1 showed that Plus One losses are dominated by source-valid reversals that later return to the source initial stop. R2 showed that an M15-close break-even ratchet at +0.50R protects too early and suppresses winner participation.

R3 tests a different proposition at a source-relevant daily checkpoint: a Plus One reversal that is still non-profitable at the **close of management bar 2** has failed the earliest author-specified 2-to-6-bar partial-profit window and should be exited rather than allowed to continue toward the initial stop.

This is `QORE_EXPERIMENTAL_MANAGEMENT`, not a claim that Connors/Raschke mechanically specified this exit.

## 2. Source entry and initial stop unchanged

R3 preserves the exact R1 Plus One detector:

- 20-period prior extreme;
- minimum age 3 source bars;
- breakout bar close confirmation;
- next-day stop entry at the prior extreme;
- next-day expiry;
- source initial stop one tick beyond the two-bar/running adverse extreme;
- R1 causal M15 execution and targeted M1 ambiguity policy.

No side, market, session, volatility, or indicator filter is introduced.

## 3. Exact R3 management rule

Only two policies are permitted:

- `R3_B2_FAIL_EXIT_F50_TRAIL1_H10`
- `R3_B2_FAIL_EXIT_F50_TRAIL2_H10`

For both policies:

1. The source initial stop remains active from fill.
2. Management bar 1 receives no new discretionary exit.
3. On management bar 2, the active stop is checked first throughout the bar under the existing causal execution model.
4. If no stop is hit, evaluate the fully closed D1 bar-2 close.
5. If the bar-2 close is favorable versus executable entry:
   - realize exactly 50% at the bar-2 close;
   - keep 50% open;
   - activate the declared one-bar or two-bar trailing stop for the balance, effective on the next bar;
   - retain hard exit at management bar 10.
6. If the bar-2 close is **not** favorable versus executable entry:
   - close 100% of the still-open position at the bar-2 close;
   - exit reason = `BAR2_FAILURE_EXIT`;
   - no later partial, trail, or hard exit is permitted for that trade.
7. Favorable means strictly positive directional price delta before transaction cost. A zero close is classified as non-favorable and exits.
8. The active stop never loosens. Gap-through stop semantics remain unchanged.
9. Transaction cost remains external to the exit trigger and is charged by the frozen research model.

No bar-3, bar-4, bar-5, bar-6 failure-exit grid is allowed in R3. No profit threshold beyond `close > entry` / `close < entry` is introduced.

## 4. Data, folds, costs and embargo

R3 reuses the governed R1 development datasets only:

- D1 run `34947549114`;
- M15 run `34947548876`;
- targeted M1 run `34959770555` only where source-path ambiguity requires it;
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY.

Fresh OOS remains embargoed from `2026-03-01T00:00:00Z`.

Primary cost = 1.0 bp round trip. Stress = 2.0 bp.

Forward folds remain WF1..WF6 exactly as R1/R2.

## 5. Frozen advancement gate

A policy advances only if all conditions hold on the six forward folds:

1. >=30 closed trades;
2. expectancy >0R/trade at 1bp;
3. PF >1.00 at 1bp;
4. >=4/6 positive fold totals;
5. 2bp stress expectancy >=0;
6. all seven leave-one-market-out forward totals >0;
7. max market/year/side contribution <=50% of total positive forward gains;
8. no unresolved evidence counted as realized;
9. primary-cost forward total improves versus the corresponding R1 bar-2 base policy and the failure-exit rule improves fold total in >=4/6 folds versus that base.

The corresponding R1 bases are `P_B2_F50_TRAIL1_H10` and `P_B2_F50_TRAIL2_H10`.

If both pass, select higher 2bp forward total, then higher 1bp forward total, then lower max drawdown, then higher worst-fold total, then lexicographic ID.

## 6. No rescue inside R3

If both policies fail, R3 is rejected. Do not move the failure exit to another bar, add a profit threshold, filter LONG/SHORT, remove a market, or reopen R2 parameters inside this identity.

Fresh OOS remains closed until an iteration passes the development gate and is frozen.
