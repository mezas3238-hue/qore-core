# QORE Shared — Global Perception Architecture Audit 001

**Checkpoint:** 29-SEP-2026  
**PR:** #635  
**Audited HEAD:** `b7694f22cf1dfc16ef05735cc00b134bb77f61dc`  
**Status:** AUDIT COMPLETE / IMPLEMENTATION REQUIRED

## Executive conclusion

Shared already has important global foundations, but its actual relational
perception is not yet global.

It has a provider-neutral `CoreGlobalMarketUniverse` without a private symbol
allowlist, an extensible universal identity layer, 19 instrument-family
categories, causal concept discovery, Active Perception sensor governance, and
a concept-level dynamic causal graph.

It does not yet have a dynamic instrument-to-instrument market graph,
generalized SMT, global lead/lag discovery, relationship lifecycle
intelligence, a cross-market Foundation Model, or Active Perception capable of
selecting arbitrary instruments from the provider universe.

## A. Markets Shared can observe today

Architecturally, `market_universe.py` can project every market present in the
provider-neutral `ExecutiveMarketsReadModel`.

The post-V14 cTrader catalogue proved 177 enabled provider symbols are
discoverable under the authorized DEMO account.

Discovery is not admission.

**Status: PARTIAL GLOBAL VISIBILITY.**

## B. Markets actually being acquired

Confirmed Shared/WP-05 evidence includes:

- retained NAS100/SP500/US30 M1 evidence;
- USTEC BID/ASK historical source evidence;
- US500 and US30 BID/ASK V14 source evidence;
- US2000 source pilot: full BID/ASK history;
- XAUUSD source pilot: full BID/ASK history;
- XTIUSD source pilot: partial BID/ASK history.

177 discovered symbols do not equal 177 acquired time series.

**Status: NARROW ACQUISITION RELATIVE TO DISCOVERABLE UNIVERSE.**

## C. Families covered

The universal registry models 19 extensible families:
cash-money-market, fixed-income-credit, rates-term-structures, equities,
funds-pooled-vehicles, indices-benchmarks, fx, futures, options,
forwards-swaps-otc, commodities, crypto-digital-assets,
structured-hybrid-products, volatility-variance-products,
securities-financing, cross-asset-compositions, event-contracts,
contracts-for-difference and loans-credit-facilities.

Most are partial; several are unresolved. Actual Shared relational acquisition
is still concentrated in US equity-index context plus early metal/energy
probes.

**Status: BROAD TAXONOMY / NARROW SENSOR COVERAGE.**

## D. Manually coded relations

- `perception.py` computes peer consensus/divergence from SP500 and US30;
- V14 froze US500 + US30;
- the post-V14 pilot froze US2000/XAUUSD/XTIUSD by semantic role.

These are lawful hypotheses, not automatic relation discovery.

**Status: SUBSTANTIALLY MANUAL.**

## E. Automatically discoverable relations

`causal_discovery_engine.py` can discover/falsify relations between generic
`CausalConcept` states with temporal ordering, confounders, regimes and
replication partitions. Representation Discovery can discover latent concepts.

There is no arbitrary instrument pair/group relation discovery engine with
multiple-testing control.

**Status: CONCEPT DISCOVERY EXISTS / GLOBAL INSTRUMENT DISCOVERY MISSING.**

## F. Dynamic Market Graph

No real instrument-level dynamic market graph exists.

`dynamic_causal_graph.py` is a graph of causal concepts.
`universal_instrument_identity_graph.py` is an identity graph.

**Status: MISSING.**

## G. Generalized SMT

No generic `CROSS_MARKET_STRUCTURAL_DIVERGENCE` engine exists.

**Status: MISSING.**

## H. Lead/lag discovery

Lead/follower is required by the architecture contract, but there is no
arbitrary market-pair lead/lag discovery with regime-conditioned OOS
validation.

**Status: MISSING.**

## I. Convergence/divergence intelligence

Local peer divergence exists. `resident_convergence_intelligence.py`
reconciles internal evidence states, not arbitrary instrument relationships.

**Status: PARTIAL / NOT GLOBAL.**

## J. Relationship stability / decay

Generic stability fields exist. No per-edge instrument lifecycle tracks stable,
decaying, broken, recovering and recoupling relations with provenance.

**Status: MISSING AS GLOBAL EDGE LIFECYCLE.**

## K. Active Perception dynamic market choice

The planner ranks preregistered candidate sensors from epistemic need and
acquisition cost. It does not search the entire provider catalogue or choose
arbitrary markets/horizons/relationships.

**Status: PARTIAL.**

## L. Market Foundation Model cross-market consumption

No implemented QORE Market Foundation Model was found. The architecture law
requires it and includes cross-market relations, but the implementation is not
present.

**Status: NOT IMPLEMENTED.**

## M. Current limits to hundreds of markets

1. hard-coded peer logic;
2. no canonical global sensor lifecycle registry;
3. no generic arbitrary-instrument acquisition orchestrator;
4. no full market-hours/session/holiday comparability engine;
5. no universal timestamp alignment for asynchronous markets;
6. no global pair/group relation measurement engine;
7. no multiple-testing/data-snooping control;
8. no instrument-level dynamic relational graph;
9. no per-edge stability/decay/recovery lifecycle;
10. no generalized SMT;
11. no regime-conditioned lead/lag/information-flow discovery;
12. Active Perception selects supplied candidates, not the full universe;
13. no cross-market Foundation Model;
14. no learned dynamic clustering over the complete sensor universe;
15. no computation-budget scheduler separating deep cognition from the
    <=2.0s Trader-facing path.

## N. Exact work required

1. freeze global-perception governance;
2. create configuration-driven global sensor registry;
3. bind provider identity to universal QORE economic identity;
4. build market-hours/session/holiday/liquidity comparability;
5. build causal as-of synchronization;
6. generalize historical acquisition by sensor contract;
7. build relation measurement primitives and multiple-testing controls;
8. build generalized cross-market structural divergence;
9. build regime-conditioned lead/lag/information-flow discovery;
10. build relationship stability/decay/break/recovery;
11. build `QORE_GLOBAL_MARKET_RELATIONAL_GRAPH`;
12. connect graph uncertainty/value to Active Perception;
13. build learned dynamic clustering;
14. feed cross-market structure into the Market Foundation Model;
15. connect relation surprise to Blindspot discovery;
16. enforce deep/nearline/runtime computation tiers;
17. falsify and replicate every promoted relation OOS.

No step grants execution authority.
