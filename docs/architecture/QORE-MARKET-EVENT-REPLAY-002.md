# QORE-MARKET-EVENT-REPLAY-002 — Unified Capture Chronology and Mixed Replay

## Status

**SLICE 2 — IMPLEMENTATION CANDIDATE — INDEPENDENT REVIEW REQUIRED**

Baseline: `8ab3eeb3eea983a422de7194424e744b742ec897`

Tracking: Issue #293.

This delivery is additive. It does not modify the legacy replay, historical OHLC dataset, Phase 1A/1B research composition, calibration, or cTrader runtime contracts.

## Purpose

Market Evidence v2 introduced exact OHLC, quote, and instrument-specification evidence. This slice gives those payloads one retained capture chronology and one deterministic historical replay representation without using UUID order as arrival evidence.

It establishes the infrastructure foundation for:

- GAP-A — retained exact Bid/Ask market events;
- GAP-B — explicit order-sensitive arrival chronology;
- GAP-G — first-arrival provenance when visibility timestamps collide;
- later GAP-F — Schedule B composition from retained availability plus exact wall-clock transitions.

These gaps are not operationally closed until provider capture, Schedule B, and the concrete Trader Midpoints evaluator consume the evidence end to end.

## Mixed payload algebra

`MarketEventPayload` is deliberately closed to:

- `QualifiedOhlcBarObservation`;
- `QualifiedQuoteTickObservation`;
- `InstrumentMarketSpecification`.

No order, execution, portfolio, or trading-methodology payload belongs in this infrastructure boundary.

## Capture chronology

Every `RetainedMarketEventObservation` retains:

- one explicit capture lineage;
- one capture session identity;
- an explicit session ordinal inside the lineage;
- an explicit ingress sequence inside the session;
- provider/hosting boundary receipt time;
- Core ingress time;
- availability-evidence time and basis;
- replay `available_at`;
- immutable evidence reference.

Canonical first-arrival ordering within one lineage is:

`(capture_session_ordinal, ingress_sequence)`

UUID lexical or numeric ordering is never an arrival fallback.

The contract also verifies that retained arrival provenance does not contradict observed receipt or Core-ingress chronology.

## Semantic time versus arrival time

The payload boundary is semantic evidence, not arrival evidence:

- OHLC: `closed_at`;
- quote: `observed_at`;
- instrument specification: `effective_at`.

Receipt cannot predate that semantic boundary. Core ingress cannot predate receipt. Replay visibility cannot predate supported evidence or Core ingress.

`available_at` controls replay visibility only. It does not redefine first arrival.

## Equal timestamps, duplicates, and conflicts

Infrastructure retains evidence; it does not apply Trader Midpoints conflict policy.

Therefore:

- exact duplicate payloads can coexist as distinct arrivals;
- conflicting payloads at the same semantic timestamp can coexist;
- explicit capture provenance establishes their arrival order;
- no UUID sort resolves a conflict;
- the later methodology evaluator owns `exact duplicate ignore` and `first arrival wins`.

## Historical mixed dataset

`HistoricalMarketEventDataset` binds:

- one market-data source;
- one canonical instrument;
- one capture lineage;
- one explicit Core-ingress capture window;
- schema and normalization versions;
- dataset/revision administrative identity;
- exact retained mixed observations;
- deterministic SHA-256 evidence digest.

Input tuple order is incidental. Canonical retained order comes only from capture provenance.

Duplicate arrival provenance fails closed.

The evidence digest includes scope, exact payload logical values, arrival provenance, receipt/ingress chronology, availability evidence, and replay visibility. Administrative dataset/revision identity and assembly timestamp are intentionally excluded from evidence-content identity.

## Replay visibility

`visible_market_event_observations(...)` uses an inclusive boundary:

`available_at <= simulated_now`

The visible subset remains in retained arrival order, even when later arrivals became replay-visible earlier.

`derive_market_event_availability_instants(...)` returns sorted distinct data-availability instants for later Schedule B composition. It does not create wall-clock transitions itself.

## Compatibility

Unchanged by this slice:

- `ReplayMarketDataObservation`;
- `replay_observation_order_key` and legacy replay ordering;
- `HistoricalOhlcReplayDataset` and existing digests;
- `ResearchExecutionSession` Phase 1A/1B semantics;
- `ResearchExecutionTrace` fingerprints;
- specialist/calibration paths;
- cTrader M5 adapter/runtime contracts;
- Trader Midpoints methodology R10.

No legacy fingerprint migration is performed.

## Determinism and side effects

Contracts use externally supplied identities and timestamps only.

Forbidden:

- `datetime.now()` / `datetime.utcnow()`;
- `uuid4()`;
- hidden mutable global counters;
- sleep/scheduler/thread/retry loops;
- network calls;
- provider SDK imports.

## Non-claims

This slice does not prove or implement:

- cTrader live Bid/Ask capture;
- historical tick completeness;
- exact Schedule B wall-clock transitions;
- Trader Midpoints evaluator;
- decision-only research composition;
- FunctionalDecision mapping;
- broker execution;
- calibration/OOS/generalization/performance/profitability;
- production readiness.

Promotion requires exact-head Quality Gate plus independent adversarial review and Integration Gate approval.
