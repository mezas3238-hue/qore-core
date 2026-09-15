# Turtle Soup Candidate R3 — Bar-2 Failure Exit Development Result

Status: **R3 REJECTED / FRESH OOS NOT CONSUMED**

Research identity: `turtle-soup-candidate-r3`

Parent evidence: R1 forensic rejection + R2 protective-ratchet falsification.

The preregistered R3 hypothesis was tested without changing the source entry, initial stop, seven-market universe, cost schedule, forward folds, or fresh-OOS embargo.

## Hypothesis tested

At management bar 2, after the source stop survives the bar, a favorable close takes the existing 50% partial and activates the declared trail. A non-favorable close exits the full remaining position as `BAR2_FAILURE_EXIT` rather than allowing the failed reversal to continue toward the source stop.

Only the preregistered one-bar and two-bar trail variants were evaluated.

## Forward result

| R3 policy | WF trades | WF net R @1bp | WF PF | Positive folds | WF stress @2bp | Improves >=4/6 folds vs R1 base | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `R3_B2_FAIL_EXIT_F50_TRAIL1_H10` | 68 | -8.3025 | 0.829 | 2/6 | -10.9304 | YES | NO |
| `R3_B2_FAIL_EXIT_F50_TRAIL2_H10` | 68 | -11.9588 | 0.754 | 2/6 | -14.5867 | YES | NO |

`R3_B2_FAIL_EXIT_F50_TRAIL1_H10` forward-fold totals:

- WF1: +6.6957R
- WF2: -5.1289R
- WF3: +3.2106R
- WF4: -2.2742R
- WF5: -4.3696R
- WF6: -6.4362R

`R3_B2_FAIL_EXIT_F50_TRAIL2_H10` forward-fold totals:

- WF1: +6.5427R
- WF2: -6.6899R
- WF3: +3.0430R
- WF4: -2.2862R
- WF5: -5.6038R
- WF6: -6.9646R

Both policies fail the absolute advancement gate: expectancy <= 0, PF <= 1, only 2/6 positive folds, negative 2bp stress, and every leave-one-market-out forward total remains negative. Positive-gain concentration also exceeds the 50% limit.

## All-development diagnostic

`R3_B2_FAIL_EXIT_F50_TRAIL1_H10`:

- 109 closed trades
- total @1bp: -4.0979R
- PF: 0.945
- max drawdown: 15.2872R
- exit reasons: 101 STOP, 8 BAR2_FAILURE_EXIT

`R3_B2_FAIL_EXIT_F50_TRAIL2_H10`:

- 109 closed trades
- total @1bp: -1.0516R
- PF: 0.986
- max drawdown: 15.4275R
- exit reasons: 98 STOP, 8 BAR2_FAILURE_EXIT, 3 TIME_EXIT

The new rule affected only eight trades per policy. It was therefore too weak and too late to address the dominant failed-reversal population, despite improving at least four fold totals relative to the corresponding R1 bar-2 base policy.

## Adjudication

`R3_BAR2_FAILURE_EXIT_FALSIFIED`

R3 is rejected. The failure-exit checkpoint is not moved to another bar and no side, market, threshold, or trail parameter is changed inside this identity.

## Authority

- candidate freeze: NONE
- fresh OOS consumed: NO
- FTMO/FundedNext approval: NO
- LIVE authority: NO

A subsequent hypothesis requires a new research/config identity and preregistration before replay.
