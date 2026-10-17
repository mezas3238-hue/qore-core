# VT08 CRT PURE — R2-A MODEL #1 MINIMAL-REFERENCE CHARACTERIZATION 001

**Identity:** `VT08_CRT_PURE_R2A_MODEL1_MINIMAL_REFERENCE_001`  
**Run:** 35717586143 — SUCCESS  
**Evidence HEAD:** `4f64ffd2b724e62f2463a4590356d45d2640f6d7`  
**Status:** CONSUMED CHARACTERIZATION / REJECTED FOR PROMOTION / RESEARCH ONLY

## Purpose

R2-A isolates the source-authorized Model #1 entry family while refusing to import
unclosed Journey/re-entry semantics.

It uses `UNTOUCHED_SWING_STRENGTH_1` only as the **minimal deterministic engineering
translation** of RomeoTPT's qualitative "old high / old low" language. This choice is
not source-canonical and was not selected from PnL.

## Frozen R2-A contract

- parent = scheduled H4 CRT / one-sided Turtle Soup;
- execution timeframe = M15 Model #1;
- old-level adapter = confirmed untouched local M15 swing, strength 1;
- reference consumed at first strict breach;
- only FIRST direction-aligned Model #1 source event inside the parent C3 is eligible;
- the first source may confirm later inside C3;
- a later source event can never replace it;
- if the first source never body-confirms, no trade;
- no Journey re-entry;
- no KOD re-entry;
- entry = next contiguous M15 open after body-close confirmation;
- stop = Model #1 source-candle extreme;
- target = frozen R1 C1 50% midpoint control;
- expiry = frozen R1 C3-close control;
- same-M15 ambiguity = STOP_FIRST;
- BTCUSD uses schedule-aware cTrader completeness;
- no synthetic bars;
- no deployment/capital authority.

## Results

### AUDUSD

- Parent CRTs: 287
- Trades: 68
- Wins / losses / flat: 35 / 32 / 1
- PF: **1.09243751**
- Total: **+1.93967966R**
- Mean: +0.02852470R
- DD: **4.61206897R**
- LS: 4

Year 1:
- 36 trades
- PF 0.91136994
- -1.05792487R
- DD 4.61206897R

Year 2:
- 32 trades
- PF 1.33132682
- +2.99760453R
- DD 2.97655890R

Event disposition:
- no aligned Model #1 source: 53
- first source not confirmed: 128
- confirmed but invalid risk geometry: 38
- trade created: 68

### USDJPY

- Parent CRTs: 267
- Trades: 61
- Wins / losses: 35 / 26
- PF: **1.38445997**
- Total: **+8.65937239R**
- Mean: +0.14195692R
- DD: **9.07297136R**
- LS: 7

Year 1:
- 29 trades
- PF 2.30110727
- +10.74630676R
- DD 2.00000000R

Year 2:
- 32 trades
- PF 0.85369338
- -2.08693437R
- DD 8.52452270R

Event disposition:
- no aligned Model #1 source: 51
- first source not confirmed: 121
- confirmed but invalid risk geometry: 34
- trade created: 61

### BTCUSD

- Parent CRTs: 459
- Trades: 139
- Wins / losses: 81 / 58
- PF: **1.03479179**
- Total: **+1.73609300R**
- Mean: +0.01248988R
- DD: **15.46603476R**
- LS: 5

Year 1:
- 66 trades
- PF 0.76830000
- -6.00419031R
- DD 11.19617521R

Year 2:
- 73 trades
- PF 1.32270196
- +7.74028331R
- DD 6.54626253R

Event disposition:
- no aligned Model #1 source: 70
- first source not confirmed: 177
- confirmed but invalid risk geometry: 73
- trade created: 139

## Combined chronological result

The three retained trade ledgers were combined and sorted by entry timestamp.

- Parent CRTs: **1,013**
- Trades: **268**
- Wins / losses / flat: **151 / 116 / 1**
- PF: **1.13205853**
- Total: **+12.33514505R**
- Mean: **+0.04602666R**
- Chronological DD: **17.53479699R**
- Longest losing streak: **7**

Year 1:
- 131 trades
- PF **1.07990108**
- +3.68419158R
- DD **8.28127176R**
- LS 7

Year 2:
- 137 trades
- PF **1.18290607**
- +8.65095347R
- DD **11.15181015R**
- LS 5

Combined event disposition across 1,013 parent CRTs:

- first Model #1 source not confirmed: **426** (42.05%)
- trade created: **268** (26.46%)
- no aligned Model #1 source: **174** (17.18%)
- confirmed Model #1 with invalid risk geometry: **145** (14.31%)

## Adjudication

### What improved

Relative to the R1 mechanical C3-open baseline, R2-A demonstrates that waiting for a
causal Model #1 can materially alter entry quality and reduce trade density.

This is a behavioral observation, not proof that the engineering old-level adapter is
RomeoTPT's exact rule.

### Why R2-A is rejected for promotion

1. `MODEL_1_REFERENCE_SELECTION` remains source-ambiguous.
2. AUDUSD is negative in Year 1.
3. USDJPY is negative in Year 2.
4. BTCUSD is negative in Year 1.
5. The combined PF 1.132 is not sufficient evidence to certify CRT.
6. Target/expiry remain R1 controls rather than fully source-closed Journey/Destination rules.
7. Key-level context has not yet been implemented.
8. Journey/re-entry/KOD remain deliberately excluded.
9. No WFO, Monte Carlo, stress, slippage or genuine fresh holdout has been authorized for
   this rejected characterization.

## Decision

**R2-A = REJECTED_FOR_PROMOTION, retained as causal characterization evidence.**

The next source-first research layer is **HTF Key Level context**, because RomeoTPT
explicitly states that a higher-timeframe key level outranks a lower-timeframe market
structure shift and separately teaches trading either the Journey toward a key level or
the reaction from it.

The next investigation must define key-level semantics from source before any hard filter
is introduced. PnL is not allowed to choose the key-level taxonomy.
