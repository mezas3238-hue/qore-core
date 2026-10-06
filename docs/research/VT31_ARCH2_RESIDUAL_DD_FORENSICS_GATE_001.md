# VT31 NAS100 — Residual Recent DD Forensics Gate 001

**Status:** PREDECLARED OBSERVATION-ONLY GATE  
**Comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Purpose

Reconstruct the exact peak-to-trough path responsible for the remaining recent
observed drawdown above the sovereign 6R gate.

Current recent observed DD:

`6.593383112613882R`

Hard gate:

`<= 6.00R`

Residual excess:

`0.593383112613882R`

## Frozen rules before inspection

This stage has **zero trading-policy authority**.

It may:

- reconstruct the exact stressed equity curve;
- identify the peak index and trough index;
- list every trade inside that drawdown path;
- expose causal entry-time context already present in consumed evidence;
- expose available post-entry diagnostic fields;
- compare drawdown-path trades with winning trades using context similarity;
- summarize state counts.

It may not:

- add or remove a trade;
- create a new threshold;
- promote a new admission rule;
- modify position management;
- use outcome labels as runtime authority;
- use fold identity or dates as runtime authority;
- use sizing, leverage, compounding or capital weighting;
- open the fresh holdout.

## Context dimensions allowed for forensics

- entry family;
- side;
- prior-day state;
- H4;
- H1;
- M15;
- premarket;
- cash open;
- reference volatility;
- position in prior-day range;
- liquidity/raid/efficiency/overlap fields when present;
- reclaim age and its already-existing bucket;
- confirmation latency and its already-existing bucket;
- target/destination geometry when present;
- risk geometry when present;
- structure event when present;
- post-entry cognitive diagnostics when already present in the simulated row.

## Matched-winner control

For every trade in the exact drawdown path, the forensic report must search
winning Comparator-007 trades and rank them by equality across the predeclared
context dimensions.

This is diagnostic only. A high similarity to winners is evidence **against**
a broad exclusion rule.

## Next-step rule

No new economic frontier is allowed until this forensic report is read.

Any subsequent hypothesis must be written in a separate predeclared gate before
economic results are run.

Fresh holdout remains sealed.
