# QORE-HOSTING-RELIABILITY-DRILL-001 — Hosting Redundancy & Emergency Drill

## Status

**DETERMINISTIC OFFLINE FAILURE-INJECTION DRILL — PRODUCTION CLOSED**

This delivery implements Delivery 15 of the Futures & Hosting Reliability Certification Program.

It turns the roadmap's failure-injection matrix into a mandatory typed drill report. The drill does not mutate a real server, broker, network or provider.

## Purpose

The drill certifies the safety response shape under deliberately injected non-production failures.

The central negative assertions are:

```text
FAILURE != AUTOMATIC FAILOVER
AMBIGUITY != ORDER REDISPATCH
PROVIDER DISAGREEMENT != AUTOMATIC PROVIDER SWITCH
```

## Mandatory injected scenarios

The report must cover exactly once:

```text
SERVER_SHUTDOWN
HEARTBEAT_LOSS
NETWORK_DEGRADATION
LATENCY_300MS_PLUS
HIGH_JITTER
PACKET_LOSS
INGRESS_HEALTHY_EGRESS_BAD
EGRESS_HEALTHY_INGRESS_BAD
CANDIDATE_SERVER_UNHEALTHY
STALE_LEASE
DUPLICATE_EVENT
DELAYED_MESSAGE
OUT_OF_ORDER_MARKET_DATA
FEED_DISCONNECT
PROVIDER_DISAGREEMENT
AMBIGUOUS_ORDER_STATE
PARTIAL_FILL
REJECT
LOST_ACK
```

Reconciliation and duplicate-redispatch protection are verified as required dispositions/negative action flags around the order-state scenarios.

## Infrastructure failure expectations

Server, heartbeat, network, catastrophic latency, jitter, packet-loss and asymmetric ingress/egress failures must produce containment evidence.

They cannot directly set:

```text
automatic_failover_triggered = true
```

Candidate-unhealthy and stale-lease cases must remain `BLOCKED`.

This preserves the MISSION-08 / Delivery 7 sequence where failover requires separate evidence, reconciliation and canonical N+1 lease acquisition.

## Market-data failure expectations

Duplicate and out-of-order market data are quarantined.

Delayed messages require quarantine or reconciliation depending on the evidence class.

Feed disconnect is contained.

Provider disagreement is blocked as evidence and cannot directly switch feeds.

Every drill result enforces:

```text
provider_switch_triggered = false
```

## Execution failure expectations

```text
AMBIGUOUS_ORDER_STATE -> RECONCILIATION_REQUIRED
LOST_ACK              -> RECONCILIATION_REQUIRED
PARTIAL_FILL          -> PRESERVE_AUTHORIZED_LIFECYCLE
REJECT                -> OBSERVED_NO_RETRY
```

Every result enforces:

```text
order_redispatch_triggered = false
```

Therefore the drill captures the repository-wide rule:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

not:

```text
AMBIGUITY -> RETRY ORDER
```

## Scenario-specific safe dispositions

`HostingReliabilityDrillResult` validates each scenario against a closed safe-disposition set.

A caller cannot claim, for example, that an unhealthy candidate was safely handled by continuing as if it were a valid replacement. That scenario must remain `BLOCKED`.

Likewise a lost ACK cannot be labeled as a successful no-op; it requires reconciliation.

## Full drill report

`HostingReliabilityDrillReport` is certifiable only when every mandatory scenario is present exactly once and every result fits inside the drill time window.

Its only current status is:

```text
CERTIFIED_OFFLINE
```

The report exposes fixed totals:

```text
automatic_failovers = 0
order_redispatches = 0
provider_switches = 0
```

Any result attempting to set one of those actions true fails contract construction.

## Relationship to prior deliveries

The drill report is the evidence summary layer for behavior already established by:

- Reliability Lab contracts;
- latency envelope;
- Hosting I/O certificates;
- market-data integrity/quarantine;
- incident genealogy;
- evidence-governed failover;
- provider-neutral Futures execution ambiguity/reconciliation;
- three-provider cross-certification.

It does not replace those canonical authority functions.

## No Production claim

This delivery does not claim that a real VPS, cloud server, exchange route, provider connection or paper broker account was physically disrupted.

It is deterministic failure-injection certification of the repository behavior only.

A future operational drill may attach real sanitized evidence after external access exists and is explicitly authorized.

## Authority exclusions

The drill module exposes no direct API for:

- server switching;
- lease acquisition/revocation;
- provider switching;
- order submission;
- retry/redispatch;
- Core Decision creation;
- Production mutation.

## Files

```text
src/qore/infrastructure/hosting_reliability_drill.py
tests/infrastructure/test_hosting_reliability_drill.py
docs/architecture/QORE-HOSTING-RELIABILITY-DRILL-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
