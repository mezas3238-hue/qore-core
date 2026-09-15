# Turtle Soup Candidate R2 — Protective Ratchet Development Result

Status: **R2 REJECTED / FRESH OOS NOT CONSUMED**

Research identity: `turtle-soup-candidate-r2`

Parent evidence: `turtle-soup-candidate-r1`

The preregistered R2 hypothesis was tested without changing the source entry, initial stop, seven-market universe, cost schedule, forward folds, base partial/trail policies, or the `2026-03-01` fresh-OOS embargo.

## Hypothesis tested

After the first fully closed native M15 bar whose directional close is >= +0.50R, ratchet the active stop to exact executable entry for the next M15 bar, never loosening a more protective stop.

No alternate threshold was tested inside R2.

## Development result

All six R2 policies fail the absolute forward advancement gate.

| R2 policy | WF trades | WF net R @1bp | WF PF | Positive folds | WF stress @2bp | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `R2_BE050_P_B2_F50_TRAIL1_H10` | 70 | -12.6084 | 0.552 | 2/6 | -15.3222 | NO |
| `R2_BE050_P_B2_F50_TRAIL2_H10` | 70 | -13.5677 | 0.524 | 2/6 | -16.2814 | NO |
| `R2_BE050_P_B4_F50_TRAIL1_H10` | 70 | -13.7715 | 0.533 | 2/6 | -16.4852 | NO |
| `R2_BE050_P_B4_F50_TRAIL2_H10` | 70 | -14.2691 | 0.517 | 2/6 | -16.9828 | NO |
| `R2_BE050_P_B6_F50_TRAIL1_H10` | 70 | -13.1205 | 0.545 | 2/6 | -15.8342 | NO |
| `R2_BE050_P_B6_F50_TRAIL2_H10` | 70 | -13.3627 | 0.533 | 2/6 | -16.0764 | NO |

The least-negative forward result is `R2_BE050_P_B2_F50_TRAIL1_H10` at `-12.6084R`, PF `0.552`, only `2/6` positive folds, negative 2bp stress, and every leave-one-market-out forward result remains negative.

The +0.50R ratchet activated in roughly 69–70 of 111 closed trades depending on base policy. Instead of creating robustness, it materially reduced winner participation and produced many small gross break-even exits that remain net-negative after transaction cost.

## Adjudication

`R2_PROTECTIVE_RATCHET_FALSIFIED`

The hypothesis that a +0.50R M15-close break-even ratchet would rescue the R1 Plus One failure is rejected. R2 is not tuned to +0.25R, +1R, +2R, a different stop level, a different side, or a market subset.

The result suggests that protection this early is too aggressive relative to the observed reversal path: it suppresses favorable recovery/winner continuation without solving the underlying forward instability.

## Authority

- candidate freeze: NONE
- fresh OOS consumed: NO
- FTMO/FundedNext approval: NO
- LIVE authority: NO

Any next management hypothesis requires a new research/config identity and preregistration before replay.
