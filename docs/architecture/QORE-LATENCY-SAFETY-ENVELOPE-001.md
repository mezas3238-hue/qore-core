# QORE-LATENCY-SAFETY-ENVELOPE-001 — Latency Safety Envelope

## Status

**NON-PRODUCTION RELIABILITY CERTIFICATION CONTRACT — PRODUCTION CLOSED**

This delivery implements Delivery 3 of the Futures & Hosting Reliability Certification Program.

It composes the Hosting Reliability Lab contracts and does not add network, broker, provider or server-control I/O.

## Governing rule

Latency is evidence, not authority.

```text
MEASURED LATENCY
 != INFRASTRUCTURE AUTHORITY
```

Any infrastructure intent still requires:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

and no latency condition may create a trading action:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Deterministic duration unit

Latency is represented as integer microseconds through `HostingLatencyDuration`.

This avoids floating-point ambiguity in threshold comparison, percentile classification and the 300 ms catastrophic boundary.

Canonical provisional ceiling:

```text
300 ms = 300_000 microseconds
```

## Independent latency surfaces

`HostingLatencyDistribution` accepts only the four latency paths currently authorized by the roadmap:

```text
NETWORK_INGRESS
INTERNAL_PIPELINE
NETWORK_EGRESS
ROUND_TRIP
```

A healthy ingress therefore cannot certify egress, internal processing or round-trip behavior.

Each distribution is account/runtime/boundary scoped and carries:

- sample count;
- minimum;
- p50;
- p95;
- p99;
- maximum;
- jitter;
- window start/end;
- evidence reference.

Percentiles must satisfy:

```text
minimum <= p50 <= p95 <= p99 <= maximum
```

## Certified normal valley

`HostingLatencyBaseline` records the evidence-backed normal valley for one exact account/runtime/path.

The baseline carries:

- reference p50;
- reference p95;
- reference p99;
- certification timestamp;
- evidence reference.

Distribution and baseline scope must match exactly before evaluation.

A baseline is not a permanent universal threshold. It is a versionable evidence point for relative deterioration.

## Absolute + relative threshold policy

`HostingLatencyEnvelopePolicy` combines:

1. absolute WARNING threshold;
2. absolute DEGRADED threshold;
3. catastrophic hard ceiling;
4. relative WARNING basis-points multiplier over certified p99;
5. relative DEGRADED basis-points multiplier over certified p99;
6. explicit policy choice whether DEGRADED requires new-work containment.

The effective WARNING/DEGRADED thresholds use the stricter of:

```text
absolute threshold
or
relative deterioration threshold
```

This means a route that normally operates at very low latency can degrade before reaching a high absolute number.

No specific relative multiplier is hard-coded as universal truth. The policy must supply it from approved certification evidence.

## Catastrophic ceiling cannot be weakened

For this non-production program:

```text
catastrophic_hard_ceiling <= 300 ms
```

A later calibrated policy may lower the ceiling.

It cannot silently raise it above 300 ms without a future repository-authorized contract change.

The 300 ms ceiling is not a target and does not imply that 299 ms is acceptable.

## Envelope states

Delivery 3 intentionally defines only latency classification states:

```text
CERTIFIED
WARNING
DEGRADED
EMERGENCY
```

It does not define `FAILOVER`, `FAILOVER_AUTHORIZED`, `SWITCH_SERVER` or `RECOVERY` as latency states.

Those require later incident/failover evidence and MISSION-08 authority composition.

## Classification

Evaluation uses both distribution p99 and maximum spike evidence.

Priority:

```text
maximum >= catastrophic hard ceiling
 -> EMERGENCY

p99 >= effective DEGRADED
OR maximum >= absolute DEGRADED
 -> DEGRADED

p99 >= effective WARNING
OR maximum >= absolute WARNING
 -> WARNING

otherwise
 -> CERTIFIED
```

Thus a dangerous spike is not hidden by a healthy percentile average.

## Reliability Lab composition

The latency state maps into a canonical `HostingReliabilityObservation` and then calls the Delivery 2 policy-bound Reliability Lab assessment.

Mapping:

```text
CERTIFIED -> NORMAL / INFO -> NO_ACTION
WARNING   -> ANOMALOUS / WARNING -> NO_ACTION
DEGRADED  -> ANOMALOUS / DEGRADED -> policy-defined NO_ACTION or CONTAIN_NEW_WORK
EMERGENCY -> ANOMALOUS / CRITICAL -> request CONTAIN_NEW_WORK
```

Important:

```text
EMERGENCY LATENCY != AUTHORITY TO CONTAIN
```

If the effective Reliability Lab policy does not authorize `CONTAIN_NEW_WORK`, evaluation fails closed instead of manufacturing authority.

The hard-ceiling breach therefore provides the cause/evidence for containment, while the Reliability Lab policy supplies the authorization.

## 300 ms behavior

A critical path reaching or exceeding the current catastrophic ceiling can produce:

```text
EMERGENCY
 -> EVIDENCE
 -> POLICY-BOUND CONTAIN_NEW_WORK
```

It cannot produce:

```text
FAILOVER
SWITCH_SERVER
ACQUIRE_LEASE
REVOKE_LEASE
```

The future incident and evidence-governed failover deliveries must diagnose the failure domain, establish that the current runtime is unsafe, establish that the candidate runtime is safe and reuse MISSION-08 fencing/reconciliation before any N+1 lease is acquired.

## Dynamic recalibration

`recalibrate_hosting_latency_baseline(...)` may create a new normal-valley baseline only from an assessment already classified `CERTIFIED`.

A WARNING, DEGRADED or EMERGENCY window cannot recalibrate the baseline and normalize its own deterioration.

Recalibration is therefore:

```text
CERTIFIED EVIDENCE
 -> EXPLICIT RECALIBRATION EVIDENCE
 -> NEW BASELINE
```

not:

```text
CURRENT BAD PERFORMANCE
 -> CALL IT NORMAL
```

## No hidden averages

The envelope does not reduce latency safety to one mean value.

The first contract carries minimum/p50/p95/p99/maximum + jitter, while Delivery 4 will add explicit event-path timestamps and I/O certificates/reporting.

## Authority exclusions

The latency module exposes no API for:

- BUY/SELL;
- order submission;
- order retry/redispatch;
- server switching;
- failover execution;
- lease acquisition/revocation;
- fencing mutation;
- Core Decision creation;
- provider SDK calls.

## Files

```text
src/qore/infrastructure/hosting_latency_safety.py
tests/infrastructure/test_hosting_latency_safety.py
docs/architecture/QORE-LATENCY-SAFETY-ENVELOPE-001.md
```

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
