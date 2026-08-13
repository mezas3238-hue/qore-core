# QORE-MARKET-CLOCK-SCHEDULE-B-003 — Generic Deterministic Wall-Clock Composition

## Status

**SLICE 3 — IMPLEMENTATION CANDIDATE — INDEPENDENT REVIEW REQUIRED**

Baseline: `64443380c262e17cd041cdcad3c3cb707e5c1757`

Tracking: Issue #295.

## Purpose

Schedule A advances research only at retained market-data `available_at` instants. The mixed
market-event replay introduced by PR #294 provides exact data-availability instants but does not
advance simulated time when no market event becomes available.

Schedule B adds methodology-neutral wall-clock transitions and composes them with mixed market
event availability. It is additive and does not mutate legacy Schedule A or its fingerprints.

## Canonical distinction

Time is not trading policy.

The generic market clock MUST NOT interpret `16:00 America/New_York` as a global market close,
forced liquidation, no-overnight rule, or account reset. Trader Midpoints may attach those
methodology-specific meanings to selected instants. A swing/trend trader may retain positions
across the same instants and across multiple days.

Core simulated time can continue when no market event arrives. Provider or venue availability is
separate evidence and must not be represented as a global clock shutdown.

## Wall-clock boundary contract

`WallClockBoundary` retains only a local `hour`, `minute`, and `second`. It intentionally has no
trading semantic label.

`derive_wall_clock_transitions(...)` requires:

- an explicit half-open simulation window `[simulated_start, simulated_end)`;
- an explicit IANA timezone name;
- an immutable tuple of local wall-clock boundaries.

Output transition instants are canonical UTC.

## IANA and DST semantics

The implementation uses `zoneinfo.ZoneInfo` and performs local -> UTC -> local round-trip
validation.

- ordinary local times produce one exact UTC instant;
- nonexistent local times during spring-forward produce no fabricated transition;
- ambiguous local times during fall-back fail closed because choosing first or second occurrence
  would be methodology policy not owned by this generic infrastructure slice.

No fixed UTC offset is retained as session truth.

## Schedule B composition

`derive_schedule_b_instants(...)` composes:

1. retained market events whose `available_at` is inside the simulation window;
2. exact wall-clock transitions inside the same window.

Each physical instant appears once.

When market availability and a wall-clock boundary collide, the result contains one
`ScheduleBInstant` with both causes:

- `newly_available_market_events` in retained arrival-provenance order;
- `wall_clock_transitions` in canonical local-boundary order.

No synthetic market payload is created and no artificial `CLOCK -> MARKET` or `MARKET -> CLOCK`
ordering is introduced.

## Compatibility

Unchanged by this slice:

- `ReplayClock`;
- `ReplayMarketDataObservation`;
- `ResearchExecutionSession` and `derive_schedule_a_instants`;
- `ResearchExecutionTrace` v1 membership and fingerprints;
- `HistoricalOhlcReplayDataset`;
- PR #294 mixed market-event replay and historical dataset contracts;
- cTrader adapter/runtime behavior;
- Trader Midpoints evaluator semantics.

Schedule B is infrastructure for a later additive research composition. It is not silently wired
into Phase 1A/1B.

## Determinism and side effects

The implementation uses supplied timestamps, IANA timezone rules, retained event provenance, and
pure deterministic derivation only.

Forbidden:

- `datetime.now()` / `datetime.utcnow()`;
- `uuid4()`;
- sleep, scheduler, thread, retry, or async loops;
- network access;
- provider SDK imports;
- global trading-policy constants such as market close or forced liquidation.

## Non-claims

This slice does not implement or prove:

- global market hours;
- provider/venue session availability;
- Trader Midpoints force-close behavior;
- swing-trader lifecycle policy;
- concrete Trader Midpoints evaluation;
- decision-only research composition;
- provider symbol discovery;
- cTrader multi-timeframe reads;
- margin/leverage normalization;
- execution;
- calibration, OOS, generalization, performance, or profitability.

Promotion requires exact-head Quality Gate, independent adversarial review, Integration Gate, and
post-merge baseline verification.
