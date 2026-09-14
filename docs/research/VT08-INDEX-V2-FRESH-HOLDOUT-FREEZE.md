# VT-08 Index V2 — fresh holdout freeze

## Freeze purpose

This document freezes one and only one QORE experimental VT-08 Index candidate before any new pre-2024 Index evidence is acquired or evaluated. The holdout must not be used to choose, tune, replace, or reinterpret any signal rule, market, anchor, stop, target, lifecycle, cardinality rule, threshold, stress rule, or Monte-Carlo gate.

## Immutable candidate entering validation

Executable candidate SHA: `1d8b9115d3d8f94a2f3470d51d77e8b8327776f8`.

Candidate id: `VT08_INDEX_V2_QORE_CANDIDATE_001`.

Development selection: `V-32e621c9282c`.

Frozen mechanics:

- universe: NAS100 / SP500 / US30;
- New-York anchors: 02:00 / 06:00 / 10:00;
- closure: `c2-or-c3-body-close`;
- protected swing: `farthest-structural`;
- stop: `protected-swing-extreme`;
- target: `1.5r`;
- lifecycle: `next-h4-boundary`;
- daily cardinality: `unique-only`.

The development ambiguity search is consumed evidence and must not be reopened. Its official selecting run is `34789861277`, artifact `10327652038`, artifact digest `sha256:4a43aed58fa43374855ad906d26719e955a03e790398feb329132fd0d786b39b`.

The execution-semantic hardening run is `34791208392`, artifact `10327822885`, artifact digest `sha256:6ca6a157572175e46fba1bd8a400cdedfd134b5b5200ee492824a13a2d03d2a3`. It passed Ruff, Mypy, focused hardening tests, the Full QORE Gate, and the frozen consumed-development replay. The hardened replay remained eligible with 314 trades, +38.57447511956754384644636730R total, +0.1228486468776036428230776029R mean, PF 1.270751727056919843895674775, and max drawdown 9.29850484081694974613427863R. The gap-through repair changed zero development exits (`gap_exit_count=0`).

## Fresh holdout partition

Raw cTrader DEMO acquisition requests the maximum supported 1,095-day M15 history for each Index market. Evaluation is restricted to New-York trading dates:

`[2023-09-15, 2024-08-13)`

The end boundary is exclusive. No decision at or after 2024-08-13 may enter fresh validation. This is disjoint from the known VT-08 Index development lineage beginning 2024-08-13.

The three markets must come from one read-only DEMO account fingerprint. LIVE acquisition or trading is prohibited.

A causal-equivalence check is mandatory: trades and adjudication computed from the full acquired file must exactly match trades and adjudication computed after truncating all M15 observations at the holdout end boundary. A mismatch is a no-lookahead failure and rejects the candidate.

## Pre-registered structural acceptance gates

All gates must pass simultaneously:

- sample >= 90 trades;
- each market >= 20 trades;
- each anchor >= 15 trades;
- aggregate mean R > 0;
- profit factor >= 1.05;
- second-half mean R > 0;
- at least 3 of 4 chronological quartiles have positive mean R;
- every leave-one-market-out mean R > 0;
- every leave-one-anchor-out mean R > 0;
- maximum drawdown <= 12R.

No failed gate may be waived after observing the holdout.

## Pre-registered stress gate

Apply an adverse deterministic friction of `0.05R` to every holdout trade. Both conditions are required:

- stressed mean R > 0;
- stressed maximum drawdown <= 15R.

The stress rule is diagnostic/qualification logic only and may not change the trader's signals.

## Pre-registered Monte-Carlo gate

The Monte-Carlo input is the same holdout return sequence after the frozen `0.05R` friction. Use:

- 10,000 paths;
- moving/block bootstrap length 5;
- each path length equal to the observed holdout sample;
- deterministic seed `20260913`;
- require probability of positive terminal R >= 0.70;
- require p95 maximum drawdown <= 20R.

## Single-look governance

The fresh result is one-shot evidence. If any structural, causal, stress, or Monte-Carlo gate fails, `VT08_INDEX_V2_QORE_CANDIDATE_001` is rejected. Any later repair or economic adjustment is a new candidate and requires a new unseen holdout. No post-result tuning is permitted on this holdout.

CIBO and Risk may review evidence only after the holdout outcome exists. Neither may alter or select trader signals using the holdout. A passing holdout does not itself grant DEMO, LIVE, or production authority; the governed Trader Lab chain must still close independently.

At freeze time:

- `FRESH_HOLDOUT_OPENED=false`;
- `DEMO_ELIGIBLE=false`;
- `LIVE_AUTHORIZED=false`;
- `PRODUCTION_AUTHORIZED=false`.
