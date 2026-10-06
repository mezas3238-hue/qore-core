# VT31 NAS100 — Rapid-Invalidation Matched Entry Study Gate 001

**Status:** PREDECLARED OBSERVATION-ONLY GATE  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Question

Can the large Breaker sudden-invalidation class be distinguished from
recoverable/winning Breaker trades **at entry time** using already-existing,
causal market states, without new threshold search?

This study is not a Comparator and has no action authority.

## Frozen populations

Use the unchanged Comparator-009 admitted Breaker population across:

- R8;
- R6;
- R5;
- recent consumed.

Define for diagnosis only:

- sudden invalidation loss = stressed losing Breaker trade that never exposes a
  fully closed M1 with `current_open_r <= -0.50R` before terminal resolution;
- recovery/winner control = stressed winning Breaker trade under the same
  Comparator-009 policy.

The terminal label defines the retrospective study cohort only. It may never be
exported to runtime facts.

## Frozen feature dictionary

Inspect only already-existing entry-time fields/buckets:

- side;
- H4 state;
- H1 state;
- M15 state;
- prior-day state;
- premarket state;
- cash-open state;
- position in prior-day range;
- reference volatility state;
- current-path-compressed boolean;
- sequence-stale-8-14 boolean;
- last structure-event family;
- confirmation-latency buckets already used by VT31:
  - FAST_LE5M;
  - MID_6_10M;
  - 11M_PLUS;
- reclaim/evidence freshness states already defined in the research stack;
- target/destination geometry states already available at entry;
- reasoning contradictions and uncertainty codes available causally at entry.

Do not invent a new numeric boundary from the known losing trades.

## Required observation output

For every candidate categorical state or conjunction reported:

- total sample;
- winner count;
- loss count;
- sudden-invalidation count;
- R8/R6/R5/recent support;
- stressed total R;
- winner-R contained;
- exact matched winners that would be affected;
- whether the state already exists in a frozen admission rule;
- causal interpretation.

Prefer single states and two-state conjunctions. Three-state conjunctions may
be reported only when they are directly implied by an existing named VT31
market-state concept; do not mine arbitrary triples.

## Promotion bar for a later comparator

This observation gate cannot promote anything.

A later Comparator requires a separate predeclaration and should only be
opened if one market-native hypothesis:

- has support in at least three consumed partitions;
- does not depend on a date, fold, terminal outcome or future path;
- uses no newly searched numeric threshold;
- has a coherent causal interpretation;
- is not already redundant with Comparator 009;
- has a realistic path to both stitched DD <=6R and Sharpe >=1.50 rather than
  merely improving PF.

If no such hypothesis exists, report that admission forensics is insufficient
and move to a different pure-edge source such as genuinely additional
independent valid setups. Do not relax certification gates.

## Governance

- observation only;
- no runtime action authority;
- no sizing/leverage/compounding/portfolio/capital logic;
- Fresh Holdout remains sealed;
- VT31 remains not certified.
