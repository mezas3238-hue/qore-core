# QORE NQ AM TLR V1 — 1Y HOLDOUT AUDIT

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1`  
Tracker: #653  
Audit date: 28-SEP-2026  
Status: `CANDIDATE_WINDOW_PREREGISTERED_BUT_SEALED`

## Rule

For this program, "fresh" is intentionally stricter than candidate-relative
freshness: a one-year interval is rejected if repository evidence shows NAS100
price/outcome evidence from that interval was already consumed by any QORE
Trader, Shared, CIBO or index research program.

No consumed interval may be relabeled fresh.

## Repository evidence found

### A. CIBO Market Atlas

Issue #602 freezes the official ten-year CIBO market-consumption corpus to:

`2016-09-17T00:00:00Z -> 2026-09-17T00:00:00Z` (end exclusive)

and freezes the canonical/provider mapping:

`NAS100 -> USTEC`

The Atlas contract states that consumed research evidence cannot later be
relabeled fresh OOS for a trader influenced by that evidence. Under this
program's stricter global-freshness rule, the full Atlas interval is treated as
unavailable for the new holdout.

### B. VT31 consumed evidence

The retained `VT-31 R5/R6 Comparative Forensics + Walk-Forward` report records
the full consumed fixed-configuration evidence as:

`2018-05 -> 2022-07`

with NAS100 included.

This interval is therefore unavailable independently of the Atlas exclusion.

### C. VT-08 Index consumed evidence

Issue #547 records:

- `[2022-09-15, 2023-09-15)` consumed forever;
- `[2023-09-15, 2024-08-13)` consumed forever;
- `2024-08-13 -> 2026-09-12` consumed research evidence.

These windows are therefore unavailable independently of the Atlas exclusion.

## Repository search for the immediately preceding year

Repository issue searches performed before preregistration for:

- `NAS100 2015`
- `USTEC 2015`
- `2015-09-17`

returned no issue-level evidence of prior consumption for the proposed interval.
This is not proof that no byte ever existed in a private/local context; it is the
repository-level audit available under the Owner rule that GitHub is source of
truth.

## Preregistered candidate holdout

Subject to provider M1 availability, the exact proposed one-year holdout is:

`2015-09-17 NY -> 2016-09-17 NY` (end exclusive)

Canonical market: `NAS100`  
cTrader DEMO provider symbol: `USTEC`  
Required resolution: `M1`  
Economic data access: `SEALED`

The end boundary is deliberately the start of the frozen CIBO ten-year corpus,
so the holdout does not overlap that corpus.

## Availability gate

The holdout MUST NOT be opened economically until the frozen candidate is green.

A boundary-only provider availability probe may establish:
- that `USTEC` existed;
- that M1 history reaches the warm-up boundary;
- that M1 history covers the entire exact holdout year.

The availability probe may not compute setups, outcomes, P&L, MAE/MFE, or inspect
the internal holdout path for rule selection.

If M1 provider coverage is insufficient, status becomes:

`NO_FRESH_1Y_HOLDOUT_AVAILABLE`

and the program stops. M5 substitution is not authorized for V1 because the
10:50-11:10 / IFVG causal sequence is frozen at M1 resolution.

## One-shot law

After the final pre-open freeze:
1. acquire immutable M1 holdout evidence once;
2. hash it;
3. run exact FULL V1 once;
4. emit result;
5. mark the year permanently consumed;
6. do not mutate V1 against that year.

No result-dependent rescue is permitted.

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`
