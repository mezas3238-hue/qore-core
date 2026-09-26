# QORE CORE STACK V2 — Shared Foundation 001

Status: RESEARCH / SHADOW-ONLY FOUNDATION
Owner: Sergio
Production authority: NONE
Merge authority: NONE

## Architectural extraction

The VT31 donor was inspected on the certified NAS100 research lineage.

GENERAL components eligible for Shared Core abstraction:
- causal as-of-only state;
- deterministic fingerprints;
- immutable snapshots;
- perception integrity and fail-closed behavior;
- factual world/context state;
- attention to changed causal events;
- hypothesis lifecycle state;
- explicit uncertainty and contradiction representation;
- WAIT as a legitimate non-error state;
- ABSTAIN / INVALIDATED as legitimate outcomes;
- cross-market facts as context, never signal authority;
- portfolio concentration and same-factor awareness;
- post-entry factual position context;
- audit/explanation bindings;
- no future/post-outcome data;
- no runtime self-training from PnL.

VT31-SPECIFIC components prohibited from promotion into Shared Core:
- NAS100 identity;
- AM Silver Bullet identity;
- 09:00 New York reference;
- 10:00-11:00 setup semantics;
- Breaker / FVG / Order Block admission semantics;
- DOL1/DOL2/DOL3 target semantics;
- VT31 source-swing invalidation;
- compressed-reference calibration;
- H1 mixed fallback calibration;
- journey/runner parameters;
- NAS100-specific market memory and Trader Experience;
- VT31 capital multipliers or risk-shield calibrations.

## Shared contract implemented

Package: src/qore/infrastructure/core_stack_v2

Implemented contracts:
- MarketEvent
- PerceptionIntegrity
- WorldState
- CoreHypothesis
- UncertaintyState
- PortfolioIntent / PortfolioSituation
- PositionContext
- immutable CoreSnapshot
- deterministic build_snapshot
- CoreAdapter protocol
- VT31CoreAdapter
- audit ledger contract
- generic A/B decision and latency summary
- compatibility manifest

CoreSnapshot and TraderCognitiveContext explicitly carry no order authority,
no QORE Risk authority, and no methodology-mutation authority.

## Fail-closed rules

Context is invalidated for:
- future source timestamp;
- future observed timestamp;
- duplicate event identity;
- duplicate market event;
- out-of-order sequence;
- incomplete event;
- missing candle inferred only from declared NEW_BAR cadence;
- stale source state.

Adapters propagate invalidity and never invent replacement context.

## VT08 Forex

VT08_FOREX = EXCLUDED.

No VT08 Forex adapter is provided. No VT08 Forex methodology, CIBO, Risk,
execution, runtime, signal, anchor, deployment or LIVE file is changed.

## Capitalizer

Capitalizer remains deferred in the compatibility manifest. No Capitalizer file
is changed. Integration remains blocked until its Target phase closes and the
final Capitalizer candidate is frozen.

## First benchmark boundary

VT31 is the first adapter because it is the architectural donor. The first
A/B must bind Core V2 as a shadow sidecar to the unchanged VT31 reasoning path
and record baseline decision, V2-context decision, WAIT/ABSTAIN delta, snapshot
validity, Core latency, adapter latency and end-to-end decision latency.

This foundation does not claim economic improvement yet.

## Governance

CORE_STACK_V2_RESEARCH_AUTHORIZED = TRUE
SHADOW_FIRST = TRUE
VT08_FOREX_INTEGRATION = FALSE
TRADER_METHODOLOGY_MUTATION = FALSE
QORE_RISK_SOVEREIGN = TRUE
ORDER_AUTHORITY = FALSE
LIVE_DEPLOYMENT_AUTHORIZED = FALSE
MERGE_AUTHORIZED = FALSE
