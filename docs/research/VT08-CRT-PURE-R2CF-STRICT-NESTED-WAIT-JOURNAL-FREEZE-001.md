# VT08 CRT PURE — R2-CF strictly chronological nested WAIT journal — preregistration

**Date:** 2026-10-13  
**Status:** Frozen before R2-CF economic results; independent methodological follow-up after R2-CE exploratory finding  
**Repository/PR:** `mezas3238-hue/qore-core` / #626, research-only  
**Source:** original frozen R2-CC/CD `delayed.jsonl` plus `report.json`, Github Actions runs AUDUSD `36173116494` and USDJPY `36173125334`; checksum archive content in CI.

## Motivation and prediction

The exploratory R2-CE WAIT-aligned prior-4Y model improved PF and delayed volume in both AUDUSD and USDJPY; however it classifies training WAIT rows using the SAME fold-fitted prior-4Y initial model that includes their own trade outcomes. Hence historical cohort membership is not out-of-sample for the training rows. This can overstate the quality of learned Journey Experience.

**Primary causal audit question:** does a WAIT journal built only from strictly prior 4-year models preserve improved post-cost economics or does the gain disappear?

## Freeze — arms and algorithm

Two and only two arms: (A) `CONTROL_ALL` replicates frozen R2-CC/CD, (B) `STRICT_NESTED_WAIT_4Y` replaces Journey Memory training cohort as follows:

1. Outer OOS year Y is identical to R2-CC/CD, with outer first-action model trained on immediately prior 4Y [Y-4,Y) using the same market-specific features, MIN_CELL_SUPPORT=30 and PRIOR_STRENGTH=100.
2. For each historical year y within [Y-4,Y), compute the *historical* initial WAIT action for historical trade rows in y with an **independent inner initial model fitted only on [y-4,y)**, NEVER on y or later; minimum **full 4-year** chronological warmup required. If y-4 is before the available earliest market research start, those y rows are excluded from the nested Journey journal, and their lack of support is counted explicitly. No relaxed warmup after observing results.
3. Each historical initial `WAIT` with available causal delayed-trade record contributes its **already frozen delayed-entry outcome** to the nested Journey Memory; all other historical actions and terminal WAIT rows are not used. There is no OOS-year outcome in inner or outer fit.
4. Fit one Journey Memory by same frozen bucket semantics `CLOSE_LT_NEG_050R`, `CLOSE_NEG_050_TO_0R`, `CLOSE_0_TO_025R`, `CLOSE_025_TO_050R`, `CLOSE_GE_050R`; labels delayed Expected-R and DOA; minimum cell support 30; prior strength 100; baseline computed among viable journal rows only.
5. Outer EXECUTE and ABSTAIN are unchanged. Outer WAIT cases observe exactly one completed M15 and, if not structurally invalidated, consumed, expired or missing, pass through the unchanged `_second_decision` with nested Journal Memory. Only second `EXECUTE` enters at the next M15 open, stop and target frozen; no third WAIT.
6. Full 4Y warmup means early outer folds have partial/empty journal; preserve those honest limitations instead of replenishing samples with ex-post labels.

## Invariants and tests

- Separate AUDUSD and USDJPY; BTCUSD untouched; no cross-market experience.
- Same fixed 1.5R target, structural stop, original C3 close, STOP_FIRST and protections (AUDUSD BE_CLOSE_075; USDJPY CONTROL), normalized R.
- Main CONTROL_ALL must reproduce prior original report count/PF/R/DD/DOA and origin counts exactly; abort on mismatch.
- All nested historical model fit windows strictly end at or before the historical event's year boundary; 4Y count strictly enforced, otherwise excluded.
- Fail closed on duplicate hypothesis keys, absent source ledger, unsupported action, unknown state, accounting gaps.
- Report per fold: inner valid years, inner unavailable rows, WAIT journal size, eligible and terminal WAIT, cell supports, initial/second actions, delayed origin, PF/R/DD/DOA/cost 0.02R & 0.05R and density.
- Expose positive OOS-year fraction. Report no value as "profitability certified" based on historical gains alone.
- A positive R2-CF result cannot become a final candidate without economic margin, `>=170` trades/year, broad positive folds and independent fresh unobserved validation.
- No sizing, volume, capital assignment, leverage, merge, VPS, DEMO, LIVE, production or real capital.

## Design knowledge and evaluation limit

R2-CE economic results are already known and motivated R2-CF; therefore this is a *causal-integrity follow-up* on already used historical data, NOT an independent untouched holdout or evidence of a fully novel edge. Its decisive role is to test whether the prior R2-CE cohort alignment survives genuine historical out-of-sample WAIT membership.

Interpret outcomes against both frozen R2-CC/CD control and documented R2-CE exploratory results without moving thresholds after inspection.
