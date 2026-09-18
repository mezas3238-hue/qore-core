# ICT Turtle Soup — Multi-Asset Research Scope

Status: PRE-ECONOMIC GOVERNANCE ADDENDUM
Research lineage: `ICT_TURTLE_SOUP`
Current first implementation identity: `ICT_TURTLE_SOUP_R1_CISD_SESSION`
Canonical trader code: `CODE_UNASSIGNED`

## Decision

ICT Turtle Soup is governed in QORE as a multi-asset methodology family, not as an index-only trader.

The transferable causal core is:

`external/time-based liquidity -> sweep/purge -> reclaim/rejection -> CISD/change in delivery -> causal entry -> structural invalidation beyond sweep -> opposing liquidity objective`.

This core may be researched on Forex, equity indices/futures proxies, metals and other sufficiently liquid markets for which QORE can retain exact causal market evidence.

This document does **not** assert universal profitability. Each asset cohort must independently satisfy data integrity, Walk-Forward, stress, concentration, leave-one-market-out or equivalent cohort robustness, and later untouched/prospective OOS gates before promotion.

## Cohort architecture

### Index cohort

Initial implementation/research proxies:

- NAS100
- SP500
- US30

The current R1 index slice uses London `[02:00,05:00)` New-York-local liquidity and NY-AM `[08:30,11:00)` event timing as a QORE formalization. These exact session boundaries are not automatically inherited by Forex.

### Forex cohort

Forex is explicitly in scope.

The Forex cohort must retain both LONG and SHORT and must use QORE-authorized provider mappings only. Initial research should cover the liquid major/cross FX instruments already supported by QORE rather than cherry-picking a single winning pair after outcomes are observed.

Forex liquidity references may include completed Asia, London, previous-day, weekly, equal-high/equal-low or other predeclared ICT-style external liquidity pools. The exact pool family and session window must be frozen before economic inspection for each candidate identity.

No Forex pair may inherit the index London->NY parameterization merely because the conceptual Turtle Soup sequence is shared.

## Shared mechanics versus adapters

Shared across cohorts:

- liquidity must pre-exist the sweep;
- sweep/purge must be causal;
- rejection/reclaim must complete before confirmation;
- CISD/change-in-delivery confirmation must use only completed bars;
- entry cannot occur before confirmation;
- stop/invalidation must remain beyond the swept structural extreme under the frozen contract;
- ambiguous same-bar chronology fails closed or uses a preregistered conservative rule;
- no retrospective symbol, side, weekday, session, target or management filtering;
- no real-capital authority from development evidence.

Cohort-specific adapters may define:

- liquidity-pool source;
- session/kill-zone windows;
- minimum price increment/pip/tick semantics;
- execution timeframe when source/data support it;
- target hierarchy;
- normalized friction model.

Any adapter change made after observing economic outcomes requires a new candidate identity.

## Promotion policy

A multi-asset umbrella does not permit one strong asset class to hide a failing one.

- Index promotion evidence is adjudicated separately from Forex promotion evidence.
- Forex promotion evidence must include pair-level and leave-one-pair-out stability.
- A universal/multi-asset canonical identity can be assigned only if the frozen cross-asset contract itself passes the required cross-asset gates.
- Otherwise, successful cohorts remain separate trader candidates.

## Authority

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`

This addendum is committed before any ICT Turtle Soup economic P&L replay has been opened.
