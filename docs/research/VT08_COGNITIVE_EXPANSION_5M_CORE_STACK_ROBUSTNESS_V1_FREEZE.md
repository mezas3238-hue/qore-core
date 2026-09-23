# VT08 Cognitive Expansion 5M — Core Stack Robustness V1 Freeze

Status: **PRE-ROBUSTNESS FREEZE / FRESH-SCREEN SURVIVORS ONLY**

The first backward fresh screen is complete.

Fresh-screen outcomes:
- EURJPY: PASS
- NZDUSD: PASS
- CADJPY: PASS
- USDCAD: FALSIFIED_FOR_THIS_STACK_V1
- USDCHF: INCONCLUSIVE_SAMPLE (economically negative)

Only the three passing markets enter this robustness stage. This is a staged
gate, not retrospective market ranking.

## Candidate identity

The candidate remains exactly Core Stack DEV V1:

- VT08 signal admission unchanged;
- VT08 reference-H4 midpoint EQ50 bank;
- VT08 opposite reference-H4 destination;
- pre-existing VT08 CIBO aggressive ratchets;
- original 2R target;
- original H4 lifecycle;
- runner OFF;
- no market/anchor/side deletion inside a market.

No parameter changes are allowed in this suite.

## Evidence

Use the exact 1095-day artifacts already acquired in run `35934924907`.
No new bars are fetched for robustness.

The full 1095-day series is now consumed extended-validation evidence.

## Robustness architecture transferred from VT31/Core

1. Full-window economics.
2. Three chronological trade-count blocks.
3. Deterministic moving-block Monte Carlo:
   - 10,000 paths;
   - block length 5 trades;
   - SHA-256 deterministic draw domain bound to market and candidate.
4. Execution stress:
   - -0.01R per trade;
   - -0.02R per trade;
   - -0.05R per trade.
5. Extreme winner dependence:
   - remove top 1 winner;
   - remove top 5 winners.
6. Diagnostics by anchor and side.

## Frozen qualification gates

A market is ROBUSTNESS_PASS only if all are true:

- sample >= 60 trades;
- full PF >= 1.80;
- total R > 0;
- observed DD <= 6R;
- all three chronological blocks total R > 0;
- MC positive terminal probability >= 0.90;
- MC p95 max DD <= 15R;
- +0.02R stress remains total-positive and PF > 1.00;
- remove-top-1 remains total-positive and PF > 1.00.

Top-5 removal is diagnostic only because the current samples are much smaller
than VT31's 806-trade certification sample.

A failure does not authorize retuning on these same 1095 days.

## Authority

- research_only=true
- robustness_is_final_certification=false
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
