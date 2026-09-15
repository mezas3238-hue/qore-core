# Turtle Soup Candidate R1 — Interim Classic + Plus One Forensics

Status: **DEVELOPMENT FORENSICS / FRESH OOS CLOSED**

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`
PR: #553

This report records the first loss-forensics pass over the corrected, already-consumed development evidence. It is not candidate approval and it does not authorize FTMO, FundedNext, LIVE, production or real-capital execution.

## Evidence boundary

Only the corrected acquisition campaign is admitted:

- D1 run: `34947549114`
- M15 run: `34947548876`
- acquisition SHA: `5a228511d39dabd9686c2d9c14c1a6a4f52ad2b2`
- universe: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY, AUDJPY
- development cutoff: `opened_at < 2026-03-01T00:00:00Z`
- fresh OOS: **NOT ACCESSED**

The session rule is the reconciled D1/M15 rule frozen before P&L interpretation: a D1 source bar is execution-qualified only when a maximal contiguous M15 path starting at the D1 open reproduces the D1 OHLC exactly. Missing or non-reconciling sessions fail closed.

Reconciled development D1 sessions:

| Market | D1 bars | Reconciled | Non-reconciled |
| --- | ---: | ---: | ---: |
| EURUSD | 636 | 633 | 3 |
| GBPUSD | 635 | 632 | 3 |
| USDJPY | 636 | 633 | 3 |
| AUDUSD | 636 | 632 | 4 |
| USDCAD | 636 | 631 | 5 |
| GBPJPY | 635 | 633 | 2 |
| AUDJPY | 636 | 633 | 3 |

No non-reconciled session is converted into a realized trade.

## Classic — forensic result is resolution-limited

The M15 source detector generated only **3 causally resolvable Classic fills** across the seven-market development corpus, but censored **307 additional Classic opportunities** as `INTRABAR_PATH_AMBIGUOUS` because sweep and recovery occurred inside the same M15 bar and their order cannot be inferred from OHLC.

Ambiguous Classic sessions by market:

| Market | M15 intrabar ambiguities |
| --- | ---: |
| EURUSD | 44 |
| GBPUSD | 48 |
| USDJPY | 36 |
| AUDUSD | 49 |
| USDCAD | 44 |
| GBPJPY | 44 |
| AUDJPY | 42 |
| **Total** | **307** |

The 3 resolved Classic fills all stopped during the entry session, before any of the four frozen experimental management policies could become economically different:

| Market | Side | Fill | Net R @1 bp | MFE before loss | Primary diagnosis |
| --- | --- | --- | ---: | ---: | --- |
| USDJPY | SHORT | 2025-06-22 22:00Z | -1.0352R | +0.3293R | FAILED_REVERSAL_AFTER_RECOVERY |
| GBPJPY | SHORT | 2025-05-11 22:00Z | -1.0549R | +0.2210R | IMMEDIATE_ADVERSE_CONTINUATION |
| AUDJPY | SHORT | 2025-05-12 00:15Z | -1.0244R | +0.0548R | IMMEDIATE_ADVERSE_CONTINUATION |

Therefore all four Classic policies currently have the same result: 3 closed trades, 0 winners, approximately **-3.1145R net at 1 bp** and **-3.2290R at 2 bp stress**.

This is **not sufficient evidence to adjudicate Classic as economically weak**. The dominant forensic finding is `DATA_RESOLUTION_LIMITATION`: 307 ambiguous opportunities versus only 3 resolved fills. Classic requires targeted native-M1 resolution of those exact pre-embargo sessions before its R1 economic verdict is admissible.

## Plus One — economically observable at M15

Plus One produced **112 source fills**. For each frozen policy, 109 trades closed and 3 were censored for insufficient/reconciliation-safe management evidence. Only 2 Plus-One opportunities were M15 intrabar ambiguous, so the current sample is materially more usable than Classic.

Primary 1 bp / stress 2 bp results:

| Policy | Closed | Censored | Net R @1 bp | Mean R | PF | Max DD R | Net R @2 bp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P_B2_F50_TRAIL1_H10 | 109 | 3 | -3.7748 | -0.0346 | 0.9495 | 14.9641 | -8.4977 |
| P_B2_F50_TRAIL2_H10 | 109 | 3 | -1.4641 | -0.0134 | 0.9806 | 16.0906 | -6.1870 |
| P_B4_F50_TRAIL1_H10 | 109 | 3 | **+9.5505** | **+0.0876** | **1.1154** | 17.7985 | **+4.8276** |
| P_B4_F50_TRAIL2_H10 | 109 | 3 | +6.1003 | +0.0560 | 1.0735 | 18.8558 | +1.3774 |
| P_B6_F50_TRAIL1_H10 | 109 | 3 | -0.2353 | -0.0022 | 0.9973 | 26.0463 | -4.9582 |
| P_B6_F50_TRAIL2_H10 | 109 | 3 | +0.5324 | +0.0049 | 1.0060 | 22.3398 | -4.1905 |

`P_B4_F50_TRAIL1_H10` is the strongest development-management lead, but this is **not a candidate freeze**.

## Plus One loss causes — B4 / one-bar trail lead

For `P_B4_F50_TRAIL1_H10`, 80 of 109 closed trades are net-negative at the primary 1 bp cost. Their primary causes are:

| Primary cause | Losses | Share of losses |
| --- | ---: | ---: |
| FAILED_REVERSAL_AFTER_RECOVERY | 53 | 66.25% |
| IMMEDIATE_ADVERSE_CONTINUATION | 22 | 27.50% |
| PARTIAL_SKIPPED_THEN_LOSS | 4 | 5.00% |
| PARTIAL_TAKEN_BALANCE_LOSS | 1 | 1.25% |

Thus **75/80 losses (93.75%)** are dominated by source-entry / source-initial-stop behavior, not by the experimental partial/trailing mechanics. Only 5/80 are primarily attributable to the frozen Plus-One management state.

Across the 112 source fills, **46 stopped during the entry session before experimental management could act**. This is direct evidence that the main loss mechanism is not simply an overly tight trailing stop.

Favorable excursion before a realized B4/one-bar loss:

- 58/80 reached at least +0.25R before ending negative;
- 45/80 reached at least +0.50R;
- 24/80 reached at least +1.00R;
- 9/80 reached at least +2.00R.

This indicates two distinct source-response populations: immediate adverse continuation and reversals that initially work but later fail.

## Plus One stability warning

The aggregate positive result of the B4 policies is not temporally or directionally uniform.

For `P_B4_F50_TRAIL1_H10`, the predeclared forward slices produce:

- WF1: +2.5573R
- WF2: -5.4212R
- WF3: +1.7363R
- WF4: +1.0540R
- WF5: -4.5551R
- WF6: -8.5053R

Only **3 of 6** forward slices are positive. This fails the already-frozen requirement of at least 4/6 positive forward folds.

By side, the same policy is:

- SHORT: +20.6548R
- LONG: -11.1042R

Approximately 79.24% of gross positive net-R contribution comes from SHORT trades. This violates the frozen concentration discipline. Removing LONG retrospectively is prohibited; such a change would be a new hypothesis with a new research identity and new validation chain.

The recent-period deterioration is also material:

- 2023: +21.1204R
- 2024: +2.6136R
- 2025: -8.9232R
- 2026 development: -5.2604R

## Current forensic adjudication

### Classic

**R1 ECONOMIC ADJUDICATION DEFERRED — DATA_RESOLUTION_LIMITATION.**

The 307 M15 ambiguities are economically material. The next valid action is targeted M1 acquisition for those exact pre-embargo sessions (plus the 2 Plus-One M15 ambiguities), followed by the same frozen source detector and management grid. No Classic parameter is changed.

### Plus One

**CURRENT R1 DOES NOT PASS THE FROZEN FORWARD/STABILITY GATE.**

Forensics rejects the hypothesis that experimental management is the dominant cause of losses. The dominant mechanism is source-valid reversal failure / source initial-stop loss, with strong side and recent-period instability. `P_B4_F50_TRAIL1_H10` remains a development forensic lead only; it is not eligible for candidate freeze or fresh OOS under the current evidence.

Any new directional, regime, market or context filter derived from these results is post-hoc research and must be preregistered as a new hypothesis before further validation. It cannot be silently added to R1.

## Governance

`FRESH_OOS_ACCESS = PROHIBITED`

No price bar with `opened_at >= 2026-03-01T00:00:00Z` was used for these findings. No current Turtle Soup R1 configuration is approved for FTMO, FundedNext, LIVE, production or real capital.
