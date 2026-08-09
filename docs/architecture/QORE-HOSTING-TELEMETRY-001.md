# QORE-HOSTING-TELEMETRY-001 — Managed Hosting Telemetry

## Status

**MISSION-08 DELIVERY 8 — NON-PRODUCTION CONTRACTS**

This delivery projects already-existing hosting state into account/runtime-scoped observational telemetry. It adds no execution authority, monitoring daemon, provider integration or hidden clock.

## Observed facts

`HostingRuntimeTelemetry` may expose:

- TradingAccountId and runtime reference;
- Runtime Registry generation;
- desired and observed runtime lifecycle state;
- health, heartbeat freshness and containment;
- whether this runtime is the current writer, another runtime is writer, or no current writer exists;
- current lease/fencing identity only when this exact runtime is the current writer;
- optional failover-readiness classification;
- explicit observation time and evidence reference.

## Authority boundary

Telemetry is presentation/operations evidence only.

```text
TELEMETRY != AUTHORITY
HEALTHY != AUTHORIZED TO EXECUTE
NO CORE DECISION -> NO NEW TRADING ACTION
```

Telemetry cannot acquire/revoke a lease, fence a runtime, activate a backup, submit an order, alter risk, retry, redispatch or call a broker/provider.

## Time and binding safety

Projection requires:

- health bound to the exact account/runtime;
- health evaluated at the exact telemetry time;
- Runtime Registry observation no newer than telemetry;
- lease snapshot captured at or after telemetry time;
- optional failover assessment bound to the same account, one of its two runtimes and the exact time.

A stale lease snapshot cannot be displayed as a current writer fact.

## Writer observation

Closed vocabulary:

```text
CURRENT_WRITER
OTHER_RUNTIME_IS_WRITER
NO_CURRENT_WRITER
```

Only CURRENT_WRITER may carry lease ID and fencing generation. These remain observations of the existing lease contract and do not become a second authority mechanism.

## Provider and secret boundary

No raw secret, broker credential, provider SDK object or external account identifier is introduced. Telemetry consumes only canonical opaque platform identities and evidence.

## MISSION-08 relationship

This is Delivery 8 of 11. The next ordered delivery is `QORE-HOSTING-COMMERCIAL-SUSPENSION-001`.

MISSION-03 issue #146 remains externally blocked. MISSION-06 and Production remain CLOSED. Native Broker and Regional Futures remain outside this mission.

## Quality gate

The exact PR head must pass unchanged:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No ignore, cast, suppression, test removal or gate weakening.
