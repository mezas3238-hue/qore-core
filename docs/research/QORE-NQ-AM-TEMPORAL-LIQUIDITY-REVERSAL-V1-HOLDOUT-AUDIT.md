# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V1 — NAS100 HOLDOUT AUDIT

Tracker: #653  
Status: HOLDOUT SEALED

## Repository evidence already consumed

GitHub is the source of truth. The following repository evidence materially
constrains a new historical NAS100 holdout:

1. CIBO Market Atlas owner amendment #602 froze the primary consumed corpus to
   `2016-09-17T00:00:00Z -> 2026-09-17T00:00:00Z` (end exclusive), with
   canonical mapping `NAS100 -> USTEC`. Once used for research, this corpus is
   consumed and cannot be relabeled fresh OOS.

2. VT31 research additionally contains consumed NAS100 evidence in overlapping
   historical windows, including the 2018-2022 family of Silver Bullet / WFO
   studies.

3. VT08 Index research marks `2022-09-15 -> 2023-09-15`,
   `2023-09-15 -> 2024-08-13`, and `2024-08-13 -> 2026-09-12` as consumed.

Therefore no interval wholly inside `2016-09-17 -> 2026-09-17` is eligible to
be called fresh for this new candidate.

## Current defensible historical option

The only immediately plausible historical one-year class on the same provider
is an interval ending no later than `2016-09-17T00:00:00Z`, subject to actual
cTrader USTEC M1 availability and confirmation that the exact interval has not
been consumed elsewhere.

Preferred availability candidate to probe, without retaining OHLC outcomes:

`2015-09-17T00:00:00Z -> 2016-09-17T00:00:00Z`

This is NOT yet the holdout. It remains a proposed availability boundary only.

If the provider cannot supply complete-enough M1 USTEC evidence for an eligible
pre-2016 year, the correct result is:

`NO_FRESH_1Y_HISTORICAL_HOLDOUT_AVAILABLE`

and the candidate must move to genuinely future forward evidence rather than
launder consumed data as fresh.

## Availability-probe law

An availability probe may record only:
- whether the canonical/provider symbol exists and is enabled;
- digits / symbol identity;
- first/last observed timestamps in the proposed boundary;
- bar counts / timestamp continuity summaries;
- data-quality gaps.

It must not persist OHLC values, compute returns, inspect candidate signals, or
run the strategy before the V1 freeze.
