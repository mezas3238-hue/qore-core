# QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001 — Program Scope & Authority Contracts

## Status

**OPENING DELIVERY — NON-PRODUCTION ONLY**

Opening baseline:

```text
main @ daa13b421542ed217018134d360ab2ffc8497a98
MISSION-08 = COMPLETED
Production = CLOSED
```

This delivery converts the canonical post-MISSION-08 roadmap into a formal construction boundary without assigning an arbitrary numeric mission identifier.

It introduces no provider SDK, runtime process, external call or Production integration.

## Purpose

The program has two independent goals:

```text
FUTURES PROVIDER NEUTRALITY
+
HOSTING RELIABILITY CERTIFICATION
```

Neither goal may create strategic authority outside Core.

## Trading authority contract

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The only acceptable provider architecture is:

```text
BROKER / MARKET API
 -> CERTIFIED ADAPTER
 -> CANONICAL QORE BOUNDARY
 -> HOSTING
 -> CORE
```

and the reverse authorized execution route must begin from an existing valid Core Decision.

Never:

```text
CORE -> CONCRETE BROKER SDK
```

A broker adapter may translate and transport an already-authorized action. It may not invent BUY/SELL, risk, quantity, SL/TP/trailing strategy or a strategic close.

## Reliability authority contract

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

The Reliability Lab is not Core and is not a trading agent.

Its autonomous action boundary is limited to infrastructure safety under a repository-authorized policy and measured evidence.

Required genealogy:

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

A decision to take no action after a transient anomaly must also retain evidence + rationale.

## Single-writer inheritance

MISSION-08 remains the mandatory execution-authority substrate.

The program may extend evidence used to decide whether failover is justified, but it does not replace:

- Runtime Registry;
- execution lease;
- fencing generation;
- health/heartbeat;
- reconciliation;
- canonical lease acquisition.

The program therefore preserves:

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

Reliability evidence may authorize initiating the controlled failover sequence. It may not directly create the replacement writer.

## Provider certification contract

The initial mandatory provider set is:

```text
TradeStation
IBKR
Tastytrade
```

Each provider must pass distinct Market Data and Execution certification.

Connectivity alone is not certification.

Market Data certification is primarily observational/read-only and must prove normalization, source identity, temporal integrity, continuity, delayed/stale classification, reconnect behavior and ingress timing.

Execution certification begins only in PAPER/SIMULATION and must prove Core-decision genealogy, idempotency, ACK/fill/reject/partial-fill handling, ambiguity containment, reconciliation and egress/round-trip timing.

## External-capability contract

Provider availability is an external fact.

The program records a dated opening verification but requires each provider-specific delivery to re-check official provider documentation and operational prerequisites.

Provider account, entitlement, subscription or sandbox limitations may block one provider delivery without becoming permission to weaken canonical contracts or substitute Production.

## Hosting measurement contract

Certification must separate at least:

```text
PROVIDER -> HOSTING INGRESS
HOSTING INTERNAL PIPELINE
HOSTING -> CORE
CORE DECISION -> HOSTING EGRESS
HOSTING -> ADAPTER
ADAPTER -> PAPER/SIM ACK
```

No single average may stand in for all surfaces.

The future measurement contracts must support minimum/p50/p95/p99/maximum, jitter, loss/gaps when measurable, spikes and sustained deterioration.

## Provisional catastrophic ceiling

The opening non-production ceiling remains:

```text
300 ms
```

Its meaning is only:

```text
PROVISIONAL CATASTROPHIC HARD CEILING
```

It is not the target latency and is not evidence that 299 ms is acceptable.

A breach may require immediate containment and incident capture under policy. It does not automatically authorize server transfer.

## Data-integrity contract

Market-data certification must be able to distinguish valid data from delayed, missing, duplicate, out-of-order, corrupted and quarantined states.

The integrity boundary may classify and quarantine. It may not silently rewrite evidence or fabricate a candle.

Provider disagreement is evidence to classify, not automatic permission for one feed to overwrite another.

## Shadow-before-paper contract

The order of authorization is fixed:

```text
CANONICAL ADAPTER CONTRACTS
 -> READ-ONLY / APPROVED MARKET DATA
 -> DATA + HOSTING CERTIFICATION
 -> SHADOW CORE
 -> PAPER/SIM EXECUTION
```

Paper execution cannot be used to skip the Shadow Core and data/Hosting certification gates.

## Separation of redundancy domains

The program must not collapse:

```text
SERVER REDUNDANCY
FEED REDUNDANCY
BROKER ADAPTER PORTABILITY
```

Each requires its own evidence, policy and action boundary.

## Secrets

All external credentials remain outside Core and repository state.

Only canonical opaque secret references may cross configuration boundaries.

No token, password, API secret, account credential or Authorization header belongs in commits, logs, docs, tests, issues, PR bodies or artifacts.

## Production

This program is explicitly non-production.

The following remain CLOSED:

- real capital;
- Production broker execution;
- Futures Production;
- Native Broker Production;
- productive automatic failover;
- productive infrastructure deployment authorization.

## Delivery sequence authority

The canonical delivery IDs and ordering are defined by:

```text
docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM.md
```

Delivery 1 opens the program boundary only.

Subsequent deliveries may implement the authorized contracts in sequence, each through a dedicated branch/PR and exact GREEN QORE Quality Gate.

Provider-specific runtime work remains subject to external capability/access gates.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```
