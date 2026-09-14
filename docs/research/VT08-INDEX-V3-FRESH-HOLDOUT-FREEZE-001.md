# VT-08 Index V3 — Fresh Holdout Freeze 001

Checkpoint: 2026-09-14

## Frozen candidate

Identity: `VT08_INDEX_V3_QORE_GEOMETRY_001`.

This candidate is a new identity built from already-consumed V2 development + V2 fresh evidence. V2 remains rejected. Nothing in this V3 freeze changes the V2 one-shot decision.

Frozen mechanics:

- markets: NAS100 / SP500 / US30;
- Owner anchors: 02:00 / 06:00 / 10:00 America/New_York;
- closure: C2-or-C3 body close;
- protected swing: farthest structural;
- stop: exact protected-swing extreme;
- one raw signal per market/New-York-date before geometry admission;
- protected-swing risk width / entry >= `0.003`;
- closure-H4 range / causal reference-H4 range >= `1.2`;
- fixed V3 QORE research target `2.5R`;
- lifecycle: next H4 boundary, 16 M15 bars;
- adverse opening stop gap exits at observed M15 open;
- favorable target gap credits no more than frozen target;
- same-M15 stop/target ambiguity is STOP-first.

The numerical geometry gates and 2.5R target are QORE empirical research policies, not universal TTrades/source claims.

## Pre-access execution history

The first workflow attempt `34798831821` stopped in `quality` at Ruff before any fresh-data acquisition job ran. The only defect was a line-length lint violation in the fresh validator's CLI print statement. Commit `09801d70b473d5bcda97f9328a6fd63887d8dd0d` reformatted that statement only; no candidate mechanics, numerical gates, markets, sides, anchors, holdout dates, stress rule, or Monte Carlo rule changed. Acquisition and adjudication were skipped, so the V3 holdout remained unopened at this renewed freeze.

## New one-shot unseen tranche

Fresh holdout ID: `VT08_INDEX_V3_FRESH_2022_09_15_TO_2023_09_15`.

Partition, New York dates:

`[2022-09-15, 2023-09-15)`

This partition predates every bar used by the prior V2 fresh tranche `[2023-09-15, 2024-08-13)` and the V2 development tranche beginning `2024-08-13`.

Acquisition is cTrader DEMO, read-only, M15, exact requested lookback `1460` days. Acquisition must prove coverage reaches on or before 2022-09-15 and extends beyond the holdout end. The actual acquisition software SHA and account fingerprint must be preserved.

If cTrader cannot supply the required old history, the workflow fails closed and the economic holdout is not adjudicated from an incomplete substitute. No alternate dates may be selected after seeing partial results.

## Frozen acceptance gates

Structural:

- sample >= `30`;
- every market sample >= `7`;
- LONG sample >= `8` and SHORT sample >= `8`;
- at least `2` distinct Owner anchors represented;
- aggregate mean R > `0`;
- profit factor >= `1.10`;
- second-half mean R > `0`;
- at least `3/4` chronological quartiles positive;
- NAS100, SP500, and US30 mean R each > `0`;
- LONG and SHORT mean R each > `0`;
- every leave-one-market-out mean R > `0`;
- max drawdown <= `10R`.

Stress:

- subtract `0.05R` from every trade;
- stressed mean R > `0`;
- stressed max drawdown <= `12R`.

Monte Carlo:

- deterministic SHA-256 domain-separated moving-block bootstrap;
- paths: `10,000`;
- block length: `5`;
- seed: `20260914`;
- input sequence: stressed holdout trade sequence;
- positive terminal R probability >= `0.70`;
- p95 max drawdown <= `15R`.

## Causal equivalence

The official workflow must replay the frozen V3 candidate twice:

1. against the complete newly acquired 1460-day raw evidence while selecting only the frozen holdout partition;
2. against copies truncated causally at `2023-09-15 00:00 America/New_York`.

Trades and gap-exit count must be identical. Any mismatch is a no-lookahead failure and rejects adjudication.

## One-shot governance

Once raw evidence covering the holdout is acquired, the tranche is consumed forever for this research lineage.

No post-result change to market, side, anchor, geometry threshold, closure, swing, stop, target, lifecycle, stress, or Monte Carlo gate is permitted for this candidate.

A failing result means `VT08_INDEX_V3_QORE_GEOMETRY_001` is rejected. A passing result allows progression to governed Risk / CIBO / independent-validation stages; it does **not** by itself authorize LIVE or production.

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`
