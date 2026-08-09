# QORE-HOSTING-IO-CERTIFICATION-001 — Hosting I/O Measurement & Certification

## Status

**NON-PRODUCTION RELIABILITY CERTIFICATION — PRODUCTION CLOSED**

Opening baseline:

```text
main @ 5c33d3fd219ed09245cd8b8f2132e7565195e82b
```

This delivery implements Delivery 4 of the Futures & Hosting Reliability Certification Program.

It adds deterministic checkpoint timing, independent I/O path certificates and periodic reliability reporting. It performs no provider, broker, server or network mutation.

## Core rule

Hosting reliability must not be represented by one aggregate latency average.

The certification boundary keeps the following surfaces independent:

```text
PROVIDER EVENT -> HOSTING INGRESS
HOSTING INGRESS -> CORE INGRESS
CORE DECISION -> ADAPTER RECEIVE
CORE DECISION -> EXTERNAL ACK
```

These map respectively to:

```text
NETWORK_INGRESS
INTERNAL_PIPELINE
NETWORK_EGRESS
ROUND_TRIP
```

A healthy ingress cannot certify egress. A healthy egress cannot certify internal processing. Round-trip evidence exists only when an external acknowledgement exists.

## Canonical checkpoint vocabulary

`HostingIOCheckpoint` defines provider-neutral timing anchors:

```text
PROVIDER_EVENT
HOSTING_INGRESS
NORMALIZATION_START
NORMALIZATION_END
CORE_INGRESS
CORE_DECISION
HOSTING_EGRESS
ADAPTER_RECEIVE
EXTERNAL_ACK
```

Delivery 4 uses canonical start/end pairs for each independent certificate surface.

The normalization and Hosting-egress checkpoints are retained in the vocabulary so later trace/certification work may preserve more granular timing without reshaping the certificate authority model.

## Timing samples

`HostingIOTimingSample` is immutable and account/runtime/path scoped.

Every sample contains:

- typed sample identity;
- canonical `TradingAccountId`;
- canonical `ExecutionRuntimeReference`;
- exact reliability boundary;
- start checkpoint;
- end checkpoint;
- timezone-aware start/end timestamps;
- evidence reference.

Duration is derived deterministically in integer microseconds from the timestamps.

A sample cannot relabel a Core-decision-to-adapter span as ingress or a provider-to-ingress span as egress. Checkpoint pairs are validated against the boundary.

## Deterministic distribution construction

`build_hosting_io_distribution(...)` converts one immutable batch for one exact account/runtime/path into the Delivery 3 `HostingLatencyDistribution`.

The distribution uses deterministic nearest-rank percentiles and preserves:

- sample count;
- minimum;
- p50;
- p95;
- p99;
- maximum;
- maximum adjacent sample-duration variation as the delivery's deterministic jitter statistic;
- batch time window;
- batch evidence reference.

Samples from different accounts, runtimes or I/O boundaries cannot be mixed into one distribution.

The chosen jitter statistic is explicitly defined rather than hidden behind a provider-specific calculation. Later evidence may add other jitter measures without silently changing this field's meaning.

## Independent path certification

`certify_hosting_io_path(...)` composes:

```text
TIMING SAMPLES
 -> DETERMINISTIC PATH DISTRIBUTION
 -> LATENCY SAFETY ENVELOPE
 -> RELIABILITY LAB POLICY ASSESSMENT
 -> PATH CERTIFICATE
```

`HostingIOPathCertificate` has only two certificate statuses:

```text
CERTIFIED
NOT_CERTIFIED
```

A path is `CERTIFIED` only when the underlying latency envelope is `CERTIFIED`.

A WARNING, DEGRADED or EMERGENCY path remains `NOT_CERTIFIED`; the underlying envelope state and Reliability Lab assessment remain available as evidence instead of being flattened into a boolean explanation-free result.

## Example: healthy ingress / bad egress

The contracts intentionally support:

```text
NETWORK_INGRESS = CERTIFIED
INTERNAL_PIPELINE = CERTIFIED
NETWORK_EGRESS = NOT_CERTIFIED / DEGRADED
```

This is a first-class valid report state.

The system must not average those three paths and produce a misleading global latency value.

## Round-trip evidence

Round-trip certification is optional in a periodic report when no external acknowledgement exists.

When present, its canonical span is:

```text
CORE_DECISION -> EXTERNAL_ACK
```

Future Paper/SIM execution delivery will supply real adapter/paper acknowledgement evidence. Delivery 4 does not create or simulate provider ACK authority by itself.

## Periodic reliability report

`HostingIOPeriodicReliabilityReport` requires independent certificates for:

```text
NETWORK_INGRESS
INTERNAL_PIPELINE
NETWORK_EGRESS
```

and may include:

```text
ROUND_TRIP
```

The report:

- keeps one certificate per boundary;
- requires exact account/runtime scope;
- requires each certificate's measurement window to fit the report window;
- exposes per-boundary lookup;
- derives overall `CERTIFIED` only when every certificate actually present is certified.

The overall state is a summary flag only. It does not replace or aggregate the path distributions.

## Reliability authority

This delivery reuses the Delivery 3 latency envelope and Delivery 2 Reliability Lab policy boundary.

Therefore:

```text
MEASUREMENT != INFRASTRUCTURE AUTHORITY
CERTIFICATE != INFRASTRUCTURE AUTHORITY
REPORT != INFRASTRUCTURE AUTHORITY
```

A degraded I/O certificate may contain a Lab assessment that authorizes `CONTAIN_NEW_WORK` according to policy, but the certificate itself cannot mutate infrastructure.

The governing rule remains:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

## Trading authority

Nothing in timing or certification creates strategic execution authority.

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The module exposes no API for:

- BUY/SELL;
- order submission;
- automatic retry/redispatch;
- provider SDK access;
- server switching;
- failover;
- execution lease acquisition/revocation;
- fencing mutation;
- Core Decision creation.

## Availability / Failover Certificate

The canonical roadmap also requires an Availability / Failover Certificate.

It is intentionally **not** fabricated inside this I/O-only delivery.

That certificate requires evidence from:

- MISSION-08 health/heartbeat;
- lease/fencing generation;
- account/execution reconciliation;
- replacement-runtime certification;
- evidence-governed failover policy;
- controlled failure/recovery drills.

Those facts are completed by later Deliveries 7 and 15. Delivery 4 establishes the I/O evidence that those future certificates can consume.

## Secrets and external access

No provider credential, account secret, bearer token or Authorization header is used or stored.

Only opaque evidence/account/runtime identifiers appear in these contracts.

No network access is required for the deterministic tests.

## Files

```text
src/qore/infrastructure/hosting_io_certification.py
tests/infrastructure/test_hosting_io_certification.py
docs/architecture/QORE-HOSTING-IO-CERTIFICATION-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
