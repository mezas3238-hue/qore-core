# QORE-RELIABILITY-INCIDENT-GENEALOGY-001 — Reliability Incident & Rationale Genealogy

## Status

**NON-PRODUCTION EVIDENCE GENEALOGY — PRODUCTION CLOSED**

Opening baseline:

```text
main @ 62ed754b4118dc258c28ed43774b67ce4b41cbda
```

This delivery implements Delivery 6 of the Futures & Hosting Reliability Certification Program.

It adds anomaly and incident/recovery evidence structures on top of the existing Hosting Reliability Lab contracts. It does not execute stabilization, failover, provider mutation or trading actions.

## Governing genealogy

The program requires every autonomous infrastructure action to remain reconstructable as:

```text
OBSERVATION
 -> DETECTED ANOMALY
 -> MEASURED EVIDENCE
 -> AUTHORIZED RELIABILITY POLICY
 -> LAB ASSESSMENT
 -> RATIONALE
 -> INFRASTRUCTURE ACTION
 -> RESULT
 -> POST-ACTION CERTIFICATION
```

Delivery 6 makes this chain explicit without creating a second authority engine.

The canonical Observation, Assessment, policy reference, rationale and Action Record remain those introduced by:

```text
QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001
```

## Anomaly Report

`HostingReliabilityAnomalyReport` binds:

- the exact canonical Reliability Lab observation;
- its exact policy-bound assessment;
- affected reliability boundary through the observation;
- severity through the observation;
- explicit metric name;
- threshold evidence reference;
- policy reference through the assessment;
- rationale through the assessment;
- generated timestamp;
- report evidence reference.

Only `ANOMALOUS` or `UNKNOWN` observations may become anomaly reports.

A normal observation is not relabeled as an anomaly merely to generate activity.

## NO-ACTION is first-class evidence

A transient spike may be anomalous while policy still concludes that intervention is not justified.

Example:

```text
network egress spike
 -> measured threshold evidence
 -> threshold duration not satisfied
 -> policy-bound assessment = NO_ACTION
 -> anomaly report retained
 -> no intervention incident opened
```

`HostingReliabilityAnomalyReport.is_justified_no_action` makes this state explicit.

Attempting to open an intervention incident from a `NO_ACTION` assessment fails closed.

Therefore:

```text
ANOMALY != MANDATORY ACTION
```

and:

```text
NO_ACTION != NO EVIDENCE
```

## Intervention Incident

`HostingReliabilityIncident` can open only from an anomaly report whose canonical Lab assessment already authorizes a non-`NO_ACTION` infrastructure intent.

The incident does not choose the action. It inherits it exactly from the assessment.

This prevents the incident/report layer from escalating:

```text
CONTAIN_NEW_WORK -> SWITCH_SERVER
```

or:

```text
RUN_STABILIZATION -> FAILOVER
```

without a separate authorized assessment.

## Recovery attempts

`HostingReliabilityRecoveryAttempt` records one policy-governed stabilization/recovery attempt with:

- incident identity;
- deterministic ordinal;
- authorized procedure reference;
- rationale code;
- start timestamp;
- completion timestamp;
- outcome;
- explicit failure reason when outcome is `FAILED` or `UNKNOWN`;
- evidence reference.

Outcomes:

```text
SUCCEEDED
FAILED
UNKNOWN
```

A failed or unknown attempt cannot omit why the result was not certified.

A successful attempt cannot carry a contradictory failure reason.

The report requires recovery ordinals to be contiguous from 1, preserving sequence.

## Action Record binding

`HostingReliabilityIncidentReport` reuses the canonical Delivery 2 `HostingReliabilityActionRecord`.

The report validates that:

- action record assessment identity equals the incident assessment;
- recorded action equals the exact assessment-authorized action;
- account/runtime scope matches;
- recovery attempts bind the same incident;
- post-action certification binds the same incident.

Evidence from a different incident cannot be spliced into the genealogy.

## Post-action certification

`HostingReliabilityPostActionCertification` records what was observed after the infrastructure action/recovery sequence.

States:

```text
CERTIFIED
NOT_CERTIFIED
UNKNOWN
```

It contains explicit evidence references and cannot predate the action/recovery evidence it certifies.

The incident report then derives only an evidence state:

```text
CERTIFIED     -> RESOLVED
NOT_CERTIFIED -> UNRESOLVED
UNKNOWN       -> UNKNOWN
```

This final state does not itself authorize another infrastructure action.

If the system remains unsafe, a new or continued policy-bound assessment is required.

## Incident / Recovery Report content

The resulting report is capable of reconstructing:

- what anomaly was observed;
- when it was observed;
- affected account/runtime/path;
- severity;
- measured evidence identity;
- relevant threshold evidence;
- reliability policy identity;
- assessment rationale;
- exact infrastructure intent;
- action result;
- each recovery attempt;
- why an attempt failed or remained unknown;
- post-action certification evidence;
- final resolved/unresolved/unknown state.

The later failover delivery will extend this genealogy with old lease/fencing generation, reconciliation, replacement-runtime certification and N+1 authority evidence rather than duplicating this report layer.

## Authority boundaries

This module records evidence only.

It exposes no direct API for:

- provider SDK calls;
- process/server restart;
- server switching;
- failover execution;
- lease acquisition/revocation;
- fencing mutation;
- order submission;
- order retry/redispatch;
- BUY/SELL;
- risk/size/SL/TP/trailing;
- Core Decision creation.

The governing rules remain:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Relationship to Delivery 7

Delivery 7 (`QORE-EVIDENCE-GOVERNED-FAILOVER-001`) may consume these incident records and extend them with the already-closed MISSION-08 authority chain.

Delivery 6 does not pre-authorize failover.

## Files

```text
src/qore/infrastructure/hosting_reliability_incident.py
tests/infrastructure/test_hosting_reliability_incident.py
docs/architecture/QORE-RELIABILITY-INCIDENT-GENEALOGY-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
