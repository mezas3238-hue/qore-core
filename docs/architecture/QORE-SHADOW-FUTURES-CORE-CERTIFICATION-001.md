# QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001 — Shadow Futures Core Runtime Certification

## Status

**NON-PRODUCTION SHADOW BOUNDARY — PRODUCTION CLOSED**

This delivery implements Delivery 14 of the Futures & Hosting Reliability Certification Program.

Delivery 13 is optional and is not a prerequisite for this delivery.

The implementation reuses the repository's canonical `FunctionalDecision` contract. It does not create a second Futures strategy engine.

## Governing principle

Shadow Core must prove that Core can receive certified market-data evidence, process it, produce auditable decisions and preserve those decisions without opening an execution path.

The terminal rule is:

```text
CORE DECISION
 -> SHADOW EVIDENCE
 -> NULL_SHADOW_SINK
```

Never:

```text
CORE DECISION
 -> PAPER/LIVE ORDER
```

inside the Shadow boundary.

## Canonical Core decision reuse

`FuturesShadowDecisionRecord` accepts only canonical resolved:

```text
FunctionalDecision
```

with:

```text
decision_type = core.trade
```

No duplicate `FuturesCoreDecision` type is introduced.

An `APPROVED` Core decision remains an approved strategic decision in the evidence record, but:

```text
trading_action_emitted = false
sink = NULL_SHADOW_SINK
```

A `REJECTED`, `BLOCKED` or `DEGRADED` resolved Core decision is preserved through the same null sink.

Pending decisions are not accepted as completed Shadow decision evidence.

## Market-data input gate

`FuturesShadowInputCertification` requires the cross-provider assessment to be either:

```text
CERTIFIED
```

or:

```text
DELAY_AWARE_CERTIFIED
```

A cross-provider `DISAGREEMENT` or `BLOCKED` state cannot feed a certified Shadow record.

This does not mean delay-aware data is realtime. It means the declared market-data mode has already been preserved and accepted for the specific Shadow evidence mode.

## Two Shadow evidence modes

The contract distinguishes:

```text
DETERMINISTIC_OFFLINE
READ_ONLY_OPERATIONAL
```

### Deterministic offline

This mode proves the architecture and safety boundary with repository-native immutable evidence.

It cannot carry an operational evidence reference.

Its status is:

```text
CERTIFIED_OFFLINE
```

This is **not** a claim that a real provider session occurred.

### Read-only operational

This mode exists for future authenticated read-only session evidence.

It requires an explicit opaque operational evidence reference.

Its status is:

```text
CERTIFIED_READ_ONLY_OPERATIONAL
```

Merely constructing offline evidence cannot produce this status.

## Session report

`FuturesShadowSessionReport` requires:

- explicit Shadow session identity;
- certified market-data input;
- non-empty immutable Core decision records;
- all decisions bound to the exact input evidence;
- explicit start/end/report timestamps;
- all decisions contained inside the session window;
- operational evidence only in operational mode.

The report exposes:

```text
trading_actions_emitted = 0
```

for every mode.

## No execution request is created

This module does not construct `FuturesExecutionRequest`.

The Shadow boundary therefore cannot accidentally become a Paper execution adapter merely because Core emitted `APPROVED`.

The next Paper E2E gate must explicitly cross a later authorization boundary after Shadow requirements are satisfied.

## Genealogy

The Shadow evidence chain is:

```text
CROSS-PROVIDER MARKET-DATA CERTIFICATION
 -> SHADOW INPUT EVIDENCE
 -> CANONICAL CORE FUNCTIONAL DECISION
 -> DECISION REASONS / OUTCOME
 -> SHADOW DECISION RECORD
 -> NULL_SHADOW_SINK
 -> SESSION REPORT
```

No provider order ID, ACK or fill exists inside this chain.

## Real session boundary

This delivery does not fabricate:

- authenticated TradeStation market-data session;
- authenticated IBKR market-data session;
- authenticated tastytrade/DXLink session;
- full-session realtime provider evidence.

Such evidence may only be recorded in `READ_ONLY_OPERATIONAL` mode after it actually exists.

## Authority exclusions

The Shadow module exposes no API for:

- order submission;
- order retry/redispatch;
- provider network clients;
- broker SDKs;
- execution lease mutation;
- server failover;
- strategic mutation of Core decisions.

The invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

and Shadow adds the stronger temporary boundary:

```text
CORE DECISION -> NO TRADING ACTION
```

## Files

```text
src/qore/infrastructure/futures_shadow_core.py
tests/infrastructure/test_futures_shadow_core.py
docs/architecture/QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
