# VT08 CRT PURE — R2-CE WAIT cohort alignment — measured replay results

**Date:** 2026-10-13  
**Status:** RESEARCH-ONLY / EXPLORATORY — NOT candidate certified  
**PR:** #626 (open/draft/unmerged), branch `agent/vt08-crt-pure-source-identity-001`  
**Freeze (preregistered before outcome read):** `VT08-CRT-PURE-R2CE-WAIT-COHORT-ALIGNMENT-FREEZE-001.md`  
**Authoritative run:** [GitHub Actions 38441743755](https://github.com/mezas3238-hue/qore-core/actions/runs/38441743755) — quality SUCCESS, AUDUSD SUCCESS, USDJPY SUCCESS.

## Method and provenance

Two separately fitted market models, no cross-market experience. CONTROL_ALL reproduces R2-CC/CD exactly; WAIT_ALIGNED_DIAGNOSTIC fits Journey Experience on those prior-4Y historical rows that the **fold-fitted initial model** classifies as WAIT, preserving all other mechanics and the original market-specific protections. All outcomes are normalized R. Input evidence consists exclusively of frozen, original R2-CC/CD GitHub Actions `delayed.jsonl` and `report.json` artifacts, not new broker reads.

**Important causal limitation:** Historical TRAIN WAIT membership is evaluated under the same in-sample 4Y model. This is a population-alignment *diagnostic*, not a fully nested out-of-sample training journal. Its gains may be optimistic. A separate strictly prior-only nested replay is REQUIRED before any market candidate promotion or further optimization based on this result.

Original runs: AUDUSD `36173116494`, USDJPY `36173125334`. New job: `38441743755` (successful). `ruff`, strict `mypy`, five pytest checks all GREEN. BOTH control reproductions passed.

## AUDUSD

| Metric | Frozen R2-CC control | R2-CE WAIT aligned |
|---|---:|---:|
| Trades | 1,067 | 1,232 |
| Trades per OOS year | 97 | 112 |
| First EXECUTE | 815 | 815 |
| WAIT delayed EXECUTE | 252 | 417 |
| Gross PF | 1.07424084 | 1.08351066 |
| Gross total R | +28.14400120 | +36.43575727 |
| Gross max DD (R) | 17.00562863 | 19.48843405 |
| DOA rate | 24.179944% | 24.107143% |
| 0.02R PF | 1.01740919 | 1.02622426 |
| 0.02R total | +6.80400120 R | +11.79575727 R |
| 0.02R DD | 22.15907357 R | 25.12843405 R |
| 0.05R PF | 0.93833439 | 0.94650911 |
| 0.05R total | -25.20599880 R | -25.16424273 R |

Interpretation: +165 trades (~15.5% density increase), +8.29175607 gross R, but higher DD and extremely thin post-cost margin. 112/year remains short of frozen 170/year floor.

## USDJPY

| Metric | Frozen R2-CD control | R2-CE WAIT aligned |
|---|---:|---:|
| Trades | 511 | 600 |
| Trades per OOS year | 63.875 | 75 |
| First EXECUTE | 432 | 432 |
| WAIT delayed EXECUTE | 79 | 168 |
| Gross PF | 1.01154342 | 1.10977925 |
| Gross total R | +2.26369481 | +25.21538718 |
| Gross max DD (R) | 15.16258017 | 18.95173947 |
| DOA rate | 24.461840% | 25.333333% |
| 0.02R PF | 0.96054269 | 1.05600123 |
| 0.02R total | -7.95630519 R | +13.21538718 R |
| 0.02R DD | 17.25849732 R | 21.00178016 R |
| 0.05R PF | 0.88919731 | 0.98052073 |
| 0.05R total | -23.28630519 R | -4.78461282 R |

Interpretation: +89 trades (~17.4% density increase) and +22.95169237 gross R, with increased DD and DOA. 0.02R becomes nominally positive, but 0.05R remains negative; 75/year remains far below floor.

## Adjudication

- **Engineering reproduction: GREEN.** Both old controls match frozen trade counts/PF/R and original reports; independent historical replay completes without cTrader account discovery.
- **Economic direction: EXPLORATORY IMPROVEMENT** on both markets at 0.02R friction.
- **Density >=170 trades/year: FAIL** for both (AUDUSD 112; USDJPY 75).
- **0.05R resilience: FAIL** for both.
- **Strict causal nested WAIT cohort: OPEN**, not asserted.
- **Sufficient economic candidate / certification: NO.**
- **BTCUSD frozen market research status: unchanged.**
- **No sizing, volume, leverage, portfolio allocation, VPS, DEMO, LIVE, merge, production, real money.**

## Next question — R2-CF

A separate preregistered strictly chronological nested first-action classification should reconstitute the training WAIT cohort with each event assessed using only earlier years and a fixed minimum warmup. R2-CE results are already visible, so R2-CF must be explicitly declared a **confirmatory/diagnostic follow-up**, with frozen rules and no tuning until after outputs. Analyze fold breadth, support loss, density and cost margins separately; do not treat a positive pooled aggregate as proof of a certifiable edge.

No further claims of profitability follow from this exploratory R2-CE run.
