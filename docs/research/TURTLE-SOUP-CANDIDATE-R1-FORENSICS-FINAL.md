# Turtle Soup Candidate R1 — Final Development Forensics Adjudication

Status: **R1 REJECTED / FRESH OOS NOT CONSUMED**

Research identity: `turtle-soup-candidate-r1`

Canonical trader code: `CODE_UNASSIGNED`

PR: #553

This report closes the R1 development-forensics decision. It does not grant DEMO, LIVE, FTMO, FundedNext, production, or real-capital authority.

## Evidence boundary

Only development evidence with `opened_at < 2026-03-01T00:00:00Z` was consumed.

Base corrected acquisition:

- D1 workflow run: `34947549114`
- M15 workflow run: `34947548876`
- acquisition SHA: `5a228511d39dabd9686c2d9c14c1a6a4f52ad2b2`

Targeted ambiguity-resolution campaign:

- M1 workflow run: `34959770555`
- acquisition SHA: `a2f1b411ea8b8dada4f41181f9698f503ac69de1`
- selection: only sessions that were `INTRABAR_PATH_AMBIGUOUS` under the frozen M15 replay; no winner/loser or P&L selection was used.

Targeted-M1 evidence digests:

- EURUSD: `d3fb720d25585e3b125457a99043c62a30869998eca569284f0197a2c9c33146`
- GBPUSD: `ffb5dca5b7a408503e85a7ed102f75d8ebe7f8eae64fc16267fdc1e0818670f9`
- USDJPY: `07eaad240bccfc6e5f1fadfc89b6d49776d9d9f933fb9d91cb5de33698a6b405`
- AUDUSD: `953c014a8840e87a1472dbce7f296a0d8e84764bd756089f0062cd8941f4eac6`
- USDCAD: `d2023941a5abd82698517a1fd84bfc8a9a0273017c7d06eeb36e6478e7091c1d`
- GBPJPY: `78770630ac1601d62375af1e46603e663a6b90b504d4661dde86b84d2b7b15a1`
- AUDJPY: `5a855f2175a176748d66cea05bc42aee33f41f64bf9718a3841f09fe70ba1990`

Primary cost remains the preregistered `1.0 bp` all-in round trip. Stress remains `2.0 bp`.

## Hierarchical M1 resolution discipline

M1 was not substituted wholesale for the source stream. The M15 bar that produced `INTRABAR_PATH_AMBIGUOUS` was eligible for refinement only when the native M1 sub-bars inside that exact M15 interval:

1. began at the M15 open;
2. were contiguous at one-minute cadence;
3. ended at the M15 close; and
4. reproduced the exact M15 OHLC.

305 of the 309 targeted ambiguous M15 bars satisfied this exact refinement contract. Four did not and remained data-resolution limitations. If the M1 bar itself contained both causal events in an unknowable order, the case remained ambiguous rather than receiving a fabricated path.

## Classic result

Before M1 refinement, Classic had 307 M15 `INTRABAR_PATH_AMBIGUOUS` cases and only three directly executable source fills.

After targeted M1 refinement:

- deterministic Classic setups/fills: **14**
- M1-resolved fills: **8**
- additional later-M15 fills made reachable after M1 resolved the earlier ambiguous state: **3**
- original M15-resolved fills retained: **3**
- still `m1-intrabar-path-ambiguous`: **293**
- M1 data-resolution limitation: **3**
- closed trades: **14**
- censored management trades among those fills: **0**

All four frozen Classic management policies have identical realized results because every resolved trade reached the source initial stop before the experimental management could differentiate them:

- primary-cost total: **-19.8458965548R**
- primary-cost mean: **-1.4175640396R/trade**
- profit factor: **0.000**
- win rate: **0%**
- max drawdown: **19.8458965548R**
- 2 bp stress total: **-25.6917931096R**

Forward-fold-only evidence:

- closed trades across WF1..WF6: **8**
- forward total: **-8.8781245495R**
- forward expectancy: **-1.1097655687R/trade**
- forward profit factor: **0.000**
- positive folds: **0/6**
- forward 2 bp stress total: **-9.7562490989R**

Loss forensics across the 14 resolved Classic trades:

- `FAILED_REVERSAL_AFTER_RECOVERY`: **11**
- `IMMEDIATE_ADVERSE_CONTINUATION`: **3**
- losses that reached at least +0.25R MFE: **11/14**
- at least +0.50R: **9/14**
- at least +1R: **5/14**
- at least +2R: **5/14**

### Classic adjudication

`R1_REJECTED_INSUFFICIENT_ADMISSIBLE_SAMPLE_AND_NEGATIVE_RESOLVED_EVIDENCE`

Classic cannot pass the frozen advancement gate: it has fewer than 30 forward closed trades, negative forward expectancy, PF 0, 0/6 positive folds, negative stress, and every leave-one-market-out forward result remains negative. The 293 residual M1 intrabar ambiguities are not converted into hypothetical trades.

This rejects **Classic R1 as an executable candidate under available historical resolution**. It is not a claim that every possible higher-resolution implementation of the source method is disproven.

## Plus One result

Plus One after the same evidence controls:

- source fills: **112**
- closed trades per frozen policy: **109**
- censored management trades per policy: **3**
- residual M1 ambiguity: **1**
- M1 data-resolution limitation: **1**

The six frozen policies all fail the forward advancement gate.

| Policy | All-dev net R | All-dev PF | WF net R | WF PF | Positive folds | WF 2bp stress R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `P_B2_F50_TRAIL1_H10` | -3.7748 | 0.949 | -7.8068 | 0.841 | 2/6 | -10.4347 |
| `P_B2_F50_TRAIL2_H10` | -1.4641 | 0.981 | -12.0875 | 0.756 | 2/6 | -14.7154 |
| `P_B4_F50_TRAIL1_H10` | +9.5505 | 1.115 | -13.1342 | 0.760 | 3/6 | -15.7621 |
| `P_B4_F50_TRAIL2_H10` | +6.1003 | 1.073 | -15.8497 | 0.711 | 3/6 | -18.4776 |
| `P_B6_F50_TRAIL1_H10` | -0.2353 | 0.997 | -14.4876 | 0.749 | 3/6 | -17.1155 |
| `P_B6_F50_TRAIL2_H10` | +0.5324 | 1.006 | -15.5571 | 0.733 | 3/6 | -18.1850 |

The apparently strongest all-development policy, `P_B4_F50_TRAIL1_H10`, is therefore **not** a candidate: its positive aggregate is driven by earlier development and reverses to `-13.1342R` across the preregistered forward folds.

For `P_B4_F50_TRAIL1_H10`, 80 primary-cost losing trades decompose as:

- `FAILED_REVERSAL_AFTER_RECOVERY`: **53**
- `IMMEDIATE_ADVERSE_CONTINUATION`: **22**
- `PARTIAL_SKIPPED_THEN_LOSS`: **4**
- `PARTIAL_TAKEN_BALANCE_LOSS`: **1**

Thus **75/80 (93.75%)** of its losses are primarily source-entry/market-response failures reaching the source initial stop, rather than experimental partial/trailing failures.

Favorable excursion before those 80 realized losses:

- MFE >= +0.25R: **58**
- MFE >= +0.50R: **45**
- MFE >= +1R: **24**
- MFE >= +2R: **9**

Its primary-cost side decomposition over all development is also unstable:

- SHORT: **+20.6548R**
- LONG: **-11.1042R**

No side is deleted from R1 after observing this result.

### Plus One adjudication

`SOURCE_METHOD_ECONOMIC_WEAKNESS_UNDER_R1_MANAGEMENT_AND_FORWARD_REGIME`

All six policies have negative forward total/expectancy and PF below 1.0. None passes the frozen development gate. The fresh holdout is therefore not opened for R1.

## R1 decision

- Classic: **REJECT R1**
- Plus One: **REJECT R1**
- candidate/config freeze: **NONE**
- fresh OOS consumed: **NO**
- FTMO/FundedNext approval: **NO**
- LIVE authority: **NO**

R1 is closed without selecting the best-looking retrospective result.

## Forensics-derived next research hypothesis

The dominant actionable observation is not a justification for a side or market filter. It is that many Plus One source-valid reversals achieve material favorable excursion and then return to the source initial stop before the frozen daily management protects the position.

A subsequent iteration must use a new research/config identity and preregister any protective-management hypothesis before replaying it. R1 results may generate that hypothesis, but R1 itself is not rewritten and the fresh OOS remains untouched.
