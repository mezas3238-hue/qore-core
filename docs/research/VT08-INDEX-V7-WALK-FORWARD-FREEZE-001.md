# VT-08 INDEX V7 — WALK FORWARD FREEZE 001

Date: 2026-09-16
Candidate: `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`

## Governance

This protocol is frozen before the next V7 fresh holdout is opened.

Walk Forward is a robustness gate. It may not tune V7, change markets, sides, anchors, POI families, stop placement, target, or entry logic after observing block results.

`LIVE_AUTHORIZED = FALSE`
`REAL_CAPITAL_AUTHORIZED = FALSE`
`PRODUCTION_AUTHORIZED = FALSE`

## Method

V7 is a deterministic frozen-rule strategy with no trainable economic parameters. Therefore the Walk Forward is a sequential forward replay, not a parameter optimization loop.

For each forward block:

1. use only bars available before and inside that block for causal state;
2. initialize context from a bounded pre-block lookback;
3. do not fit thresholds or select submodels from preceding results;
4. execute the exact frozen V7 fingerprint;
5. evaluate the block under the same conservative stop-first ordering and friction assumptions.

## Evidence scope

Only already-consumed evidence may be used for pre-fresh Walk Forward:

- `[2020-09-15, 2022-09-15)` — consumed V6 fresh holdout;
- `[2022-09-15, 2023-09-15)` — consumed V3 holdout;
- `[2023-09-15, 2024-08-13)` — consumed V2 holdout;
- `[2024-08-13, 2026-09-12)` — consumed R1/development evidence.

The new fresh holdout `[2018-09-15, 2020-09-15)` is excluded from Walk Forward until its one-shot decision is sealed.

## Forward blocks

Use fixed six-month calendar blocks aligned from 15-Sep and 15-Mar wherever source coverage exists. The final partial block ending 12-Sep-2026 is permitted and must be reported as partial.

A block is `supported` when it has at least 20 trades. Sparse blocks are reported but cannot be counted as passes.

## Primary stress

`-0.05R/trade`.

## Secondary stress

`-0.10R/trade`.

## Frozen Walk Forward gates

V7 passes this Walk Forward stage only if all of the following hold:

- at least 6 supported forward blocks;
- at least 70% of supported blocks have positive primary-stress mean R;
- no supported block has primary-stress mean `<= -0.10R/trade`;
- aggregate primary-stress mean > 0;
- aggregate primary-stress PF >= 1.15;
- aggregate primary-stress max drawdown <= 20R;
- aggregate secondary-stress mean > 0;
- aggregate secondary-stress PF > 1;
- no evidence of a single market being responsible for all positive expectancy across supported blocks.

## Interpretation

A Walk Forward pass does not certify V7 by itself. A fresh-holdout pass remains mandatory.

A Walk Forward failure does not permit repair against these consumed blocks under the same V7 identity. Any economic rule change creates a new candidate identity and requires a new untouched holdout.
