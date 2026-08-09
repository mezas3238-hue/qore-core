# QORE-EVIDENCE-GOVERNED-FAILOVER-001 — Evidence-Governed Stabilization & Failover

## Status

**NON-PRODUCTION FAILOVER AUTHORITY COMPOSITION — PRODUCTION CLOSED**

This delivery implements Delivery 7 of the Futures & Hosting Reliability Certification Program.

It composes Reliability Lab incident evidence and candidate I/O certification with the already-closed MISSION-08 single-writer lease/fencing/reconciliation boundary. It does not introduce a second lease authority or a heartbeat-to-backup shortcut.

## Governing sequence

The only valid evidence-governed handoff remains:

```text
ANOMALY
 -> CONTAIN / STABILIZATION EVIDENCE
 -> INCIDENT REMAINS UNSAFE
 -> POLICY AUTHORIZES FAILOVER EVALUATION
 -> PREVIOUS AUTHORITY REVOKED/EXPIRED
 -> ACCOUNT RECONCILIATION MATCHED
 -> EXECUTION RECONCILIATION MATCHED
 -> CANDIDATE HEALTHY + CURRENT
 -> CANDIDATE HOSTING I/O CERTIFIED
 -> MISSION-08 READY_FOR_LEASE_ACQUISITION
 -> CANONICAL N+1 LEASE ACQUISITION
 -> POST-HANDOFF AVAILABILITY / FAILOVER CERTIFICATION
```

Never:

```text
HEARTBEAT LOST -> START BACKUP
LATENCY SPIKE -> SWITCH SERVER
INCIDENT FAILED -> RETRY ORDER
```

## Two independent proofs are required

Failover requires evidence for both sides of the handoff.

### Current runtime unsafe

The current runtime is not considered unsafe merely because an anomaly once existed.

`HostingReliabilityIncidentReport` must remain:

```text
UNRESOLVED
```

and its exact Reliability Lab assessment must already authorize:

```text
INITIATE_FAILOVER_EVALUATION
```

A resolved incident is blocked with:

```text
CURRENT_RUNTIME_NOT_PROVEN_UNSAFE
```

A containment-only or stabilization-only assessment is blocked with:

```text
FAILOVER_EVALUATION_NOT_AUTHORIZED
```

The failover composer may not escalate one infrastructure intent into another.

### Replacement runtime safe

The replacement runtime must carry an independent `HostingIOPeriodicReliabilityReport` for the exact candidate account/runtime.

Its overall state must be:

```text
CERTIFIED
```

which requires independent certified ingress, internal and egress paths.

A healthy heartbeat with degraded egress is therefore insufficient.

Candidate report mismatch or degraded I/O blocks before MISSION-08 lease readiness is considered.

## MISSION-08 remains canonical

After the Reliability Lab evidence gates pass, Delivery 7 calls the existing:

```text
evaluate_hosting_failover_readiness(...)
```

This retains all MISSION-08 requirements:

- previous runtime contained;
- previous authority absent;
- candidate health `HEALTHY`;
- candidate heartbeat freshness `CURRENT`;
- candidate containment `NONE`;
- external account reconciliation `MATCHED`;
- execution reconciliation `MATCHED`;
- next fencing generation exactly N+1.

If MISSION-08 returns `BLOCKED`, the outer assessment remains blocked and retains the exact nested MISSION-08 reason as evidence.

Examples include:

```text
PREVIOUS_AUTHORITY_STILL_ACTIVE
EXTERNAL_ACCOUNT_AMBIGUOUS
EXECUTION_RECONCILIATION_AMBIGUOUS
CANDIDATE_NOT_HEALTHY
```

## Readiness is not writer authority

When every evidence gate passes, Delivery 7 may return only:

```text
READY_FOR_CANONICAL_LEASE_ACQUISITION
```

with the exact `HostingFencingGeneration` supplied by MISSION-08.

At this point:

```text
CANDIDATE IS STILL NOT WRITER
```

The assessment stores exact typed identities for:

- incident report;
- candidate I/O report;
- MISSION-08 readiness assessment;
- next fencing generation.

There are no generic `object`/`Any` IDs in the contract.

## Canonical N+1 acquisition

`acquire_evidence_governed_failover_lease(...)` contains no independent lease algorithm.

It validates that the evidence-governed assessment is READY and then delegates to the existing canonical MISSION-08 function:

```text
acquire_hosting_execution_lease(...)
```

using exactly:

- assessed account;
- assessed candidate runtime;
- assessed MISSION-08 N+1 generation;
- explicit lease identity;
- explicit timestamps;
- lease evidence reference.

The canonical lease boundary therefore remains responsible for rejecting:

- a still-active writer;
- stale/non-increasing generation;
- account/runtime mismatch;
- invalid timing;
- any split-brain attempt.

## Availability / Failover Certificate

Delivery 4 intentionally deferred Availability/Failover certification until authority evidence existed.

Delivery 7 now adds `HostingAvailabilityFailoverCertificate`.

A certificate can be `CERTIFIED` only if, at the exact certification timestamp:

1. the evidence-governed assessment was READY;
2. the exact candidate I/O report identity matches the assessment;
3. candidate I/O remains `CERTIFIED`;
4. the canonical lease snapshot covers the certification time;
5. canonical `current_authority(...)` identifies the exact candidate runtime;
6. current fencing generation equals the exact assessed N+1 generation.

Otherwise the result is `NOT_CERTIFIED` or construction fails if evidence identities/scopes are inconsistent.

The certificate validates its own status; callers cannot directly construct a false `CERTIFIED` record around mismatching lease or I/O evidence.

## Split-brain containment

The resulting authority chain is:

```text
OLD WRITER N
 -> CONTAIN
 -> REVOKE/EXPIRE N
 -> RECONCILE
 -> CANDIDATE CERTIFIED
 -> READY N+1
 -> CANONICAL ACQUIRE N+1
 -> EXACTLY ONE CURRENT WRITER
```

There is no path in this delivery that starts B while A retains current authority.

## Ambiguity

Account or execution ambiguity continues to flow into the canonical MISSION-08 block:

```text
AMBIGUITY
 -> BLOCK
 -> OBSERVE
 -> RECONCILE
 -> RESOLVE
```

Never:

```text
AMBIGUITY -> REDISPATCH ORDER
```

## Failure-domain separation

This delivery is infrastructure failover composition only.

It does not authorize market-data provider switching or broker execution-provider switching.

```text
SERVER REDUNDANCY
 != FEED REDUNDANCY
 != BROKER ADAPTER PORTABILITY
```

Those domains retain separate future policies and certifications.

## Trading authority

Failover never creates trading intent.

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Neither the Reliability Lab, the failover assessment, the canonical lease acquisition wrapper nor the Availability/Failover Certificate can create:

- BUY/SELL;
- order submission;
- automatic retry/redispatch;
- risk/size/SL/TP/trailing;
- strategic close;
- Core Decision.

A new writer may execute only already-authorized lifecycle work according to canonical execution contracts.

## Secrets and provider I/O

No provider SDK, broker endpoint, credential or secret value is introduced.

The deterministic tests use only canonical immutable repository contracts.

## Files

```text
src/qore/infrastructure/hosting_evidence_governed_failover.py
tests/infrastructure/test_hosting_evidence_governed_failover.py
docs/architecture/QORE-EVIDENCE-GOVERNED-FAILOVER-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
