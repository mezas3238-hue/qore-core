# QORE NQ AM TLR V4 — USTEC CAPABILITY FREEZE

Identity: QORE_NQ_AM_TLR_V4_USTEC_CAPABILITY_001
Issue: #657
Parent: #656
PR: #654
Status: RESEARCH_ONLY / CAPABILITY_DISCOVERY

## Question

Does the AM-session low reversal architecture have measurable economic capability
on QORE's actual cTrader USTEC CFD?

This is a different question from exact source replication on exchange NQ
futures. Exact-NQ work remains open, but does not block this USTEC capability
test.

## Primary candidate — frozen before economics

ROLLING_AM_LOW_M2

Rules:

1. USTEC / NAS100 CFD, M1.
2. Prior RTH 16:14 New York settlement is above the current 09:30 open
   (discount opening gap).
3. Use the first two completed RTH M1 candles as the opening-delivery
   signature. Their highs must remain below the lower gap quadrant and their
   closes below the lowest gap octant.
4. At 10:50 New York freeze the causal AM reference as the minimum low observed
   from 09:30 through 10:49.
5. During 10:50-11:10 price must trade below that frozen AM low.
6. From the first penetration through 11:10, no M1 close may remain at/below the
   frozen reference.
7. A bearish FVG from the delivery leg must invert causally by 11:10.
8. Entry = close of the qualifying IFVG overlap/reclaim bar.
9. Stop = one provider tick below the lowest observed price from the penetration
   through entry.
10. Target = 09:30 RTH open.
11. Exit unfinished positions at 12:00.
12. Same-M1 stop/target collision = stop first.

The M2 choice is frozen because the source discussion refers to the initial
opening candles in plural. It is not selected from USTEC P&L.

The primary candidate does not require:
- V2's formulaic bullish ETH daily-context gate;
- an untouched prior daily low;
- a fixed daily-low/2SD tolerance.

## Diagnostic matrix — zero promotion authority

Opening signature:
- NONE
- M1
- M2
- M5

Reference model:
- ROLLING_AM_LOW
- NEAREST_PRIOR_DAILY_LOW
- TWO_SD_OPENING_GAP_EXTENSION

All 12 cells are computed. Only ROLLING_AM_LOW_M2 adjudicates the primary
question. No diagnostic cell can replace the primary because it has favorable
P&L.

## Evidence

Read-only cTrader DEMO USTEC M1:
- acquisition warm-up starts: 2022-07-29T00:00:00Z
- evaluation: 2022-08-13 NY -> 2025-08-13 NY end exclusive

Fixed one-year folds:
- Y1: 2022-08-13 -> 2023-08-13
- Y2: 2023-08-13 -> 2024-08-13
- Y3: 2024-08-13 -> 2025-08-13

This is capability discovery, not fresh sealed certification.

## Primary discovery gate

USTEC_CAPABILITY_SUPPORTED requires all of:
- trades >= 24;
- PF > 1.15 after 0.05R/trade primary friction;
- Total R > 0;
- max drawdown <= 8R;
- positive Total R in at least 2/3 fixed yearly folds.

If trades < 24:
INSUFFICIENT_SAMPLE

Otherwise:
USTEC_CAPABILITY_NOT_SUPPORTED

Stress friction of 0.10R/trade is reported but does not change this discovery
label.

## Authority

DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false

No merge without explicit Owner order.
