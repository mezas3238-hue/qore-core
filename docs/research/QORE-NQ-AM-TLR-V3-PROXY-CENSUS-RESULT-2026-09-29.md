# QORE NQ AM TLR V3 — USTEC PROXY SOURCE CENSUS RESULT

Date: 29-SEP-2026  
Tracker: #656  
PR: #654  
Identity: `QORE_NQ_AM_TLR_V3_SOURCE_CENSUS_001`

## Authoritative result

The V3 source-event census completed GREEN over the consumed one-year cTrader
`USTEC` M1 interval:

`2024-08-13 NY -> 2025-08-13 NY` (end exclusive)

Authoritative source-census run:
- workflow: `36504364440`
- SHA: `7ec5d68020ffa23cfa477e2df2f6a4916f5ecbac`
- artifact: `11006542575`
- artifact digest:
  `sha256:a0229e05ce6c59fd7a9f48d9a05525d9a3556e1f065b9f486b5b6fa7329e336c`

A later performance-only implementation retained exact summary semantics:
- workflow: `36505212955`
- SHA: `d5558053d71f2d69e893b0a621529dfbcaa51b9d`
- artifact: `11006469033`
- artifact digest:
  `sha256:e8523580ef637493f4b4996b5289071b7b2c9a7e3e18b94d4524921301f7f4f9`
- `summary.json` SHA-256 in both runs:
  `e05a8c60ee70a82ababb7a9116c7f04b260455dc679da4a498e05862f957e01f`

Therefore the census metrics below are reproducible across the original and
indexed implementations.

## One-year source-event census

- evaluated RTH sessions: **247**
- gap-down sessions: **104**
- source-like opening signature:
  - first 1 M1 bar: **61** sessions
  - first 2 M1 bars: **52** sessions
  - first 5 M1 bars: **39** sessions
- prior-five daily-reference rows: **980**
- untouched prior daily-reference rows: **622**
- untouched + gap-down daily-reference rows: **232**
- full 10:50-11:10 macro touches among those 232 rows: **1**
- macro touch + IFVG confirmation: **0**
- macro touch + body rejection of daily reference: **0**
- macro touch + body rejection of 2SD: **0**

No P&L was computed. The census has no selection authority.

## Distance to 2SD

For the 232 untouched daily references that occurred on gap-down days:

| normalized absolute daily-low distance to 2SD | references | macro touches | IFVG confirmations |
|---|---:|---:|---:|
| <= 0.125 gap | 3 | 0 | 0 |
| <= 0.25 gap | 4 | 0 | 0 |
| <= 0.50 gap | 10 | 0 | 1 |
| <= 1.00 gap | 26 | 0 | 2 |
| > 1.00 gap | 189 | 1 | 14 |

The only macro-touch row lies in the **>1.00 gap** distance group and did not
produce the source-like body-rejection + IFVG continuation chain.

## Scientific interpretation

The consumed USTEC proxy year does not contain a sufficiently recurrent event
family matching the reviewed source example closely enough to freeze another
executable Trader without relaxing or inventing source rules.

This does **not** establish that the NQ methodology itself is false. The evidence
instrument is a cTrader CFD proxy:

`USTEC_PROXY_EVIDENCE != EXACT_NQ_CONTRACT_EVIDENCE`

The source trade was executed on NQ futures, where contract basis, RTH settlement,
prior daily lows and opening-gap geometry can differ.

The correct next step is exact-instrument evidence, not threshold rescue.

## Exact NQ evidence foundation

QORE now contains a read-only TradeStation API v3 historical-evidence foundation:

- commit: `a3f15725374615cbbd77260ac33e4b32b268dba9`
- workflow: `36505444250`
- quality result: **GREEN**
  - Ruff GREEN
  - mypy GREEN
  - focused tests GREEN
  - governance assertions GREEN

The collector:
- uses only TradeStation market-data barcharts;
- requires provider-verified NQ contract symbols and roll boundaries;
- retains each contract identity per M1 bar;
- forbids synthetic/back-adjusted splicing;
- exposes no brokerage/order call;
- has zero trading authority.

Exact acquisition has **not** run because TradeStation market-data credentials
and a provider-verified NQ contract manifest are not currently configured in this
research branch.

## Current adjudication

`V2 = INSUFFICIENT_EXECUTABLE_SAMPLE_ON_USTEC_1Y`

`V3_USTEC_SOURCE_CENSUS = SOURCE_EVENT_INCIDENCE_INSUFFICIENT_FOR_NEW_TRADER_FREEZE`

`V3_EXACT_NQ_EVIDENCE_FOUNDATION = ENGINEERING_GREEN / PROVIDER_AUTH_PENDING`

No V3 executable Trader is frozen yet. No LIVE/DEMO/real-capital authority is
introduced.
