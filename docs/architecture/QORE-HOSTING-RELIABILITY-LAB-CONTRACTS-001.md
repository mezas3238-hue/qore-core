# QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001 — Hosting Reliability Lab Contracts

## Status

**NON-PRODUCTION INFRASTRUCTURE-RELIABILITY CONTRACTS — PRODUCTION CLOSED**

Opening baseline:

```text
main @ 47103aa71bb769953459a3e2942e90be629d33c9
```

This delivery implements the foundational contracts authorized by Delivery 2 of the Futures & Hosting Reliability Certification Program.

It introduces no provider SDK, no network I/O, no order I/O and no productive infrastructure mutation.

## Governing authority

Trading authority remains unchanged:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Reliability authority is separately constrained by:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

The Reliability Lab is an infrastructure-safety domain, not a trading agent.

## Canonical genealogy foundation

The contracts provide the first typed segments of the required reliability genealogy:

```text
OBSERVATION
 -> EVIDENCE
 -> AUTHORIZED RELIABILITY POLICY
 -> LAB ASSESSMENT
 -> RATIONALE
 -> AUTHORIZED INFRASTRUCTURE INTENT
 -> ACTION RESULT RECORD
```

Later deliveries add metric-specific evidence, incident genealogy and post-action certification without changing the authority direction established here.

## Observation contract

`HostingReliabilityObservation` is immutable and binds every observation to:

- canonical `TradingAccountId`;
- canonical `ExecutionRuntimeReference`;
- a reliability boundary;
- condition;
- severity;
- timezone-aware observation timestamp;
- opaque reliability evidence reference.

Initial boundaries are deliberately provider-neutral:

```text
RUNTIME
NETWORK_INGRESS
INTERNAL_PIPELINE
NETWORK_EGRESS
ROUND_TRIP
MARKET_DATA
AVAILABILITY_FAILOVER
```

Delivery 2 does not define latency units/distributions or candle semantics; those belong to Deliveries 3–5.

## Condition / severity contract

Conditions:

```text
NORMAL
ANOMALOUS
UNKNOWN
```

Severities:

```text
INFO
WARNING
DEGRADED
CRITICAL
UNKNOWN
```

`UNKNOWN` is explicit rather than inferred as healthy.

A `NORMAL` observation cannot claim degraded/critical/unknown severity, and an `UNKNOWN` condition requires `UNKNOWN` severity.

## Reliability policy contract

`HostingReliabilityPolicySnapshot` is immutable and versioned.

It defines only which Reliability Lab infrastructure intents are permitted while the policy is effective.

Every policy must allow evidence-backed `NO_ACTION` so the Lab can preserve justified non-actions instead of manufacturing an intervention merely because an anomaly was observed.

Policy expiration fails closed for new action authorization.

## Infrastructure intent vocabulary

Delivery 2 intentionally exposes only:

```text
NO_ACTION
CONTAIN_NEW_WORK
RUN_STABILIZATION
INITIATE_FAILOVER_EVALUATION
```

Important distinction:

```text
INITIATE_FAILOVER_EVALUATION != FAILOVER
```

There is intentionally no `FAILOVER`, `SWITCH_SERVER`, lease acquisition, lease revocation or fencing mutation action in this contract.

The actual evidence-governed failover sequence is reserved for Delivery 7 and must reuse the closed MISSION-08 lease/fencing/reconciliation contracts.

## Assessment contract

`HostingReliabilityAssessment` is an evidence + policy-bound authorization record.

Creation through `assess_hosting_reliability_observation(...)` requires:

1. a canonical immutable observation;
2. its evidence reference;
3. an effective reliability policy;
4. an action permitted by that exact policy;
5. an explicit rationale code;
6. a timezone-aware assessment timestamp not preceding the observation.

Additional evidence references may be attached, but they must be unique.

A `NORMAL` observation can authorize only `NO_ACTION`, even if an overly broad policy lists an intervention. This prevents policy configuration alone from manufacturing operational cause.

An `UNKNOWN` or `ANOMALOUS` observation may authorize containment/stabilization/failover evaluation only when the effective policy explicitly permits that intent.

The assessment performs no provider/runtime mutation.

## Action result record

`HostingReliabilityActionRecord` records the result of the exact infrastructure intent authorized by an assessment.

`record_hosting_reliability_action(...)` rejects a result record if the recorded action differs from the assessment-authorized action.

Possible outcomes are:

```text
NO_ACTION_RECORDED
SUCCEEDED
FAILED
UNKNOWN
```

`NO_ACTION` must use `NO_ACTION_RECORDED`, preserving explicit evidence for justified non-action.

The action record remains evidence only. It does not:

- call a provider;
- start/stop a server;
- acquire/revoke a lease;
- create fencing;
- submit an order;
- create a Core Decision.

## No trading authority

The Lab contracts expose no API for:

- BUY;
- SELL;
- order submission;
- retry order;
- redispatch;
- risk mutation;
- position close/liquidation;
- Core Decision creation;
- provider SDK access.

Any future adapter/provider integration remains behind its own canonical boundary.

## MISSION-08 inheritance

Delivery 2 does not reopen MISSION-08.

The existing single-writer truth remains:

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

A Reliability Lab assessment may eventually justify entering the failover process, but writer authority remains created only through the canonical MISSION-08 execution-lease boundary after containment, fencing and reconciliation requirements are satisfied.

## Secrets

This delivery introduces no credentials and no secret values.

Future external configuration must continue to use opaque `SecretRef` references only.

## Explicitly deferred

The following are intentionally deferred to their authorized deliveries:

- latency distributions and 300 ms envelope evaluation;
- I/O timing certificates;
- market-data/candle integrity classifiers;
- full incident/recovery genealogy;
- stabilization procedure execution boundary;
- failover composition with MISSION-08;
- provider-neutral Futures adapter contracts;
- TradeStation/IBKR/tastytrade connectivity;
- Shadow Core;
- Paper Futures E2E.

## Files

This delivery adds:

```text
src/qore/infrastructure/hosting_reliability_lab.py
tests/infrastructure/test_hosting_reliability_lab.py
docs/architecture/QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
