# QORE Shared WP-05 V12 — Source-Only Anchor Observability / Staleness Freeze

Identity:

`QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ANCHOR_OBSERVABILITY_001`

## Scientific purpose

Measure whether independently retained historical BID/ASK evidence is causally
usable at the exact frozen R8 source timestamps and freeze quote staleness
without reading any target/outcome.

This stage is strictly source-only. It may inspect:

- the frozen 6,804 R8 evaluation anchors;
- the immutable full-R8 BID/ASK acquisition;
- provider event timestamps and prices;
- source-only provenance/integrity evidence.

It may not inspect matured structural-failure labels, MAE/MFE, trade outcomes,
PnL, R6/R5, WP-05 fresh holdout or the final Shared certification holdout.

## Upstream gates

The stage may run only after:

1. full acquisition = 16/16 and 2948/2948;
2. raw source integrity = `green_source_integrity`;
3. exact 6,804 source-anchor artifact is frozen and reproduces the acquisition
   manifest SHA256.

## Causal quote-state rule

For each frozen evaluation anchor and each side independently:

`latest_side = latest provider event with provider_event_at <= evaluation_at`

Future provider events are forbidden.

BID and ASK are never forced into one-to-one event pairing.

For equal provider timestamps, the retained provider order is preserved. Across
historical pagination boundaries, older page content precedes newer page content
when timestamps are equal.

## Frozen staleness candidate grid

Before observing anchor-age results, the only candidate limits are:

`250, 500, 1000, 2000, 5000, 10000, 30000, 60000 ms`

No other threshold may be introduced after the audit is observed.

For threshold `T`, an anchor is **usable** only when:

- BID exists at-or-before the anchor;
- ASK exists at-or-before the anchor;
- BID age <= T;
- ASK age <= T;
- reconstructed causal spread is non-negative.

A crossed asynchronous state is not repaired, clipped or paired to a future
quote. It is `INSUFFICIENT` for spread representation.

## Frozen threshold selection rule

Select the **smallest** candidate `T` whose usable-anchor coverage is at least
**9500 bps (95.00%)** of the complete 6,804-anchor R8 population.

If no candidate through 60 seconds reaches 9500 bps:

`V12_QUOTE_STALENESS_FREEZE = REJECTED`

and target-aware V12 discovery remains closed.

No threshold may be selected based on structural-failure performance.

## Required source-only report

For the complete anchor population report:

- BID age min/p50/p95/p99/max;
- ASK age min/p50/p95/p99/max;
- max(BID age, ASK age) min/p50/p95/p99/max;
- absolute side-age skew min/p50/p95/p99/max;
- no-prior-BID count;
- no-prior-ASK count;
- crossed causal quote count before staleness filtering;
- for every frozen threshold:
  - both-side-fresh count;
  - non-crossed usable count;
  - usable coverage bps;
  - crossed count among both-side-fresh states;
- selected staleness limit or REJECTED;
- deterministic report SHA256.

## Frozen missingness law

After a threshold is selected:

- missing side => `INSUFFICIENT`;
- stale side => `INSUFFICIENT`;
- crossed causal quote => `INSUFFICIENT`;
- no future interpolation;
- no forward-fill beyond threshold;
- no nearest-neighbor synchronization;
- no target-aware deletion of insufficient anchors.

Missingness itself may later be retained as an explicit source-quality state,
but may not be transformed using outcome information.

## Multiscale windows

The causal microstructure windows are frozen independently of target outcomes:

- 1,000 ms;
- 5,000 ms;
- 15,000 ms;
- 60,000 ms.

These windows are not selected from R8 target performance.

## Post-audit consequence

A GREEN observability/staleness freeze authorizes construction of the exact
source-only V12 representation dataset at all 6,804 anchors.

It still does not authorize R6/R5 or any fresh holdout.

Target-aware R8 discovery may begin only after the exact feature family,
normalization semantics, representation fingerprint and candidate-selection
protocol are frozen.

## Sovereignty

No Trader, CIBO, Risk, order or Execution authority is created by this work.
