# ICT Turtle Soup R3 — Source-Bound Research Freeze

Date: 2026-09-15
Identity: `ICT_TURTLE_SOUP_R3_SOURCE_BOUND`
Parent: `ICT_TURTLE_SOUP_R2_ALL_SESSION_MULTI_ASSET`

## Purpose

Freeze the R3 research questions before any new economic replay. R3 is not yet a candidate trader and has no economic authority.

## Frozen source questions

R3 must determine, without selecting on P&L:

1. What makes a pre-existing high/low `meaningful`, `old`, `obvious`, or liquidity-bearing in ICT terminology?
2. How do old highs/lows, equal highs/lows, previous-day/week/month extrema, completed session extrema and local short-term swings differ conceptually?
3. Can multiple coincident liquidity references be treated as stacked/confluent rather than ambiguous? If so, how can this be represented without inventing a priority hierarchy?
4. What rejection/failure behavior is source-supported after the liquidity run? Same-bar reclaim is NOT assumed.
5. Which confirmation families are compatible with Turtle Soup but separable from the event itself: direct rejection, CISD/protected swing, MSS, inversion, FVG, breaker?
6. What higher-timeframe/context information is genuinely required versus merely preferred for specific execution models?
7. How should lifecycle/invalidation be defined so that normal retests are not automatically confused with true failure?
8. How should the opposing liquidity objective be selected when more than one pre-existing target exists?
9. How do these concepts transfer across Forex, index futures/proxies and metals without importing instrument-specific tick/pip rules?

## Consumed-evidence diagnostics allowed

The already-consumed R2 full ledger may be used only for descriptive feature matrices and root-cause comparisons. Permitted examples:

- liquidity-reference family;
- age/visibility descriptors computed without outcome labels;
- number of coincident pools at the swept level;
- distance from broader-range extremes;
- sweep penetration normalized by pre-entry volatility/range;
- same-bar vs delayed rejection as descriptive categories;
- CISD latency;
- protected-swing formation timing;
- displacement/expansion descriptors;
- target distance and opposing-liquidity structure;
- session/macro/hour as diagnostics only;
- symbol/side/timeframe breadth.

No threshold, filter, pool family, hour, session, symbol, side or confirmation family may be selected because it looks profitable on the consumed holdout.

## Forbidden retrospective conclusions

The following are explicitly prohibited from becoming R3 rules solely from the consumed R2 ledger:

- remove a losing pair;
- operate only positive hours/sessions;
- require a profitable pool family discovered post hoc;
- choose a sweep-depth threshold from winner/loser separation;
- choose a CISD latency cutoff from winner/loser separation;
- choose a stop width or breakeven rule from stopped-trade recovery;
- choose a minimum R:R from the result;
- choose a market subset from leave-one-out behavior.

## Source-confidence labels

Every eventual R3 mechanic must be marked one of:

- `PRIMARY_ICT_CONFIRMED`
- `TTRADES_CORROBORATED`
- `ICT_COMPATIBLE_QORE_FORMALIZATION`
- `SOURCE_UNDERDETERMINED`

`SOURCE_UNDERDETERMINED` mechanics cannot silently become economic gates.

## Advancement requirement

Before any R3 economic replay there must be a separate pre-economic candidate freeze containing:

- exact liquidity qualification algorithm;
- exact confirmation family;
- exact entry/invalidation/target/lifecycle;
- exact markets/timeframes;
- exact data provenance;
- exact friction/stress assumptions;
- exact development/WF/holdout boundaries;
- exact advancement gates.

No previously consumed R2 holdout may be called fresh again.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
