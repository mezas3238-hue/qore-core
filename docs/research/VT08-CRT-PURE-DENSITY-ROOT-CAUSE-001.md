# VT08 CRT PURE — DENSITY ROOT CAUSE 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Status:** ROOT CAUSE MEASURED / RECOVERY LABS ACTIVE

## 1. Problem

The long-window target labs exposed unacceptable final density:

- AUDUSD: 208 trades / 10Y = 20.8/year
- USDJPY: 83 trades / 12Y = 6.9/year

These counts are **not** the natural density of CRT PURE. They are the population
remaining after multiple engineering gates.

## 2. R2-AH — long-window density attribution

### AUDUSD 2016-2026

Parent CRT:
- 1,403
- 140.3/year

Aligned Model #1 source:
- 1,156 parents
- 82.39% of parents
- 2,639 source events

Selected confirmed hypothesis:
- 765
- 54.53% of parents

Valid current midpoint geometry:
- 560 trades
- 56.0/year
- 39.91% of parents

Current EFF1D 0.10-0.20 population:
- 208 trades
- 20.8/year
- only 37.14% of otherwise-valid trades retained
- 352 valid trades rejected by regime

Unfiltered economics:
- 560 trades
- PF 0.99453171
- -1.07325030R
- DD 26.78757358R
- 56 trades/year

Current narrow-regime economics:
- 208 trades
- PF 1.32085796
- +20.26557893R
- DD 5.38406423R

Interpretation:
EFF1D is buying edge by deleting 62.86% of the already-valid population.

### USDJPY 2014-2026

Parent CRT:
- 1,644
- 137.0/year

Aligned Model #1 source:
- 1,349 parents
- 82.06% of parents
- 3,023 source events

Selected confirmed hypothesis:
- 870
- 52.92% of parents

Valid current midpoint geometry:
- 662 trades
- 55.17/year
- 40.27% of parents

Current EFF5D 0.10-0.20 population:
- 83 trades
- 6.92/year
- only 12.54% of otherwise-valid trades retained
- 579 valid trades rejected by regime

Unfiltered economics:
- 662 trades
- PF 0.97212860
- -6.58199479R
- DD 29.29791972R

Current narrow-regime economics:
- 83 trades
- PF 1.99032476
- +22.17670789R
- DD 4.03448045R

Interpretation:
EFF5D is buying edge by deleting 87.46% of the already-valid population.

## 3. R2-AJ — H4 timing-lattice capacity

The existing FX timing observes only two non-overlapping triplets/day:
- 01-05-09 NY
- 13-17-21 NY

R2-AJ preserved C1 -> C2 -> C3 semantics but evaluated every consecutive H4 triplet
on the same lattice:
- starts 01, 05, 09, 13, 17, 21 NY

No PnL was used.

### AUDUSD 2020-2026

Control:
- 840 parent CRT = 140/year
- 643 structurally valid confirmed slots = 107.17/year
- cap-1 structural capacity = 471 = 78.5/year

Rolling H4:
- 2,515 parent CRT = 419.17/year
- 2,105 structurally valid confirmed slots = 350.83/year
- cap-1 structural capacity = 1,466 = 244.33/year
- cap-2 structural capacity = 1,968 = 328/year

Multipliers:
- parents: 2.994x
- structural slots: 3.274x
- structural cap-1: 3.113x

### USDJPY 2020-2026

Control:
- 767 parent CRT = 127.83/year
- 543 structurally valid confirmed slots = 90.5/year
- cap-1 structural capacity = 407 = 67.83/year

Rolling H4:
- 2,516 parent CRT = 419.33/year
- 2,154 structurally valid confirmed slots = 359/year
- cap-1 structural capacity = 1,455 = 242.5/year
- cap-2 structural capacity = 1,993 = 332.17/year

Multipliers:
- parents: 3.280x
- structural slots: 3.967x
- structural cap-1: 3.575x

## 4. Root cause

The density collapse is produced by **engineering ceilings**, not absence of CRT structure.

Measured bottlenecks:

1. only two H4 triplets/day are currently observed;
2. max one selected hypothesis per parent;
3. midpoint target geometry rejects structurally valid opportunities;
4. narrow EFF regime filters then remove most of the population that survives.

The rolling H4 lattice alone proves that the existing market data contains enough CRT
opportunity capacity to reach roughly 240 cap-1 structural opportunities/year per FX
market, before any cap-2 rearm.

## 5. Economic constraint

Removing EFF alone is **not** a solution.

The unfiltered current-timing populations are near break-even/slightly negative:
- AUDUSD PF ~0.995
- USDJPY PF ~0.972

Therefore density recovery must preserve/rebuild edge rather than merely remove gates.

## 6. Active recovery chain

- R2-AK: rolling H4, one selected hypothesis, current midpoint economics
- R2-AL: fixed-R targets without artificial midpoint precondition
- R2-AM: high-retention single-bucket ablation, minimum 60% population retained
- R2-AO: rolling H4 + structural fixed targets, frozen before outcomes
- R2-AI: long-window multi-hypothesis opportunity capacity

## 7. Governance

No methodology is being changed silently.
Every recovery dimension is isolated or predeclared before PnL is read.

- PR remains DRAFT / UNMERGED
- no VPS
- no DEMO
- no LIVE
- no production
- no real capital
