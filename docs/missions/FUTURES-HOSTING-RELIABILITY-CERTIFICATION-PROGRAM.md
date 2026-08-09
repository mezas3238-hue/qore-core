# QORE Futures & Hosting Reliability Certification Program

Status: **OPEN — NON-PRODUCTION PROGRAM AUTHORIZED; PRODUCTION REMAINS CLOSED**

Opening baseline:

```text
main @ daa13b421542ed217018134d360ab2ffc8497a98
MISSION-08 = COMPLETED
MISSION-03 Gate #5 / issue #146 = OPEN / BLOCKED
Production = CLOSED
```

Canonical roadmap:

```text
docs/roadmap/QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP.md
```

This document formalizes the post-MISSION-08 roadmap into an explicit repository-governed construction program without inventing a numeric mission identifier.

The program is authorized only for **NON-PRODUCTION certification, contracts, deterministic/offline evidence, read-only market-data validation, Shadow Core, and broker PAPER/SIMULATION** according to the staged gates below.

It does not authorize real capital or productive broker execution.

## Program authority model

### Strategic trading authority

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Core remains the only strategic trading authority.

Core connects directly to:

```text
0 CONCRETE BROKER APIs
```

All provider integrations must remain behind certified adapters and canonical QORE boundaries.

No Hosting component, Reliability Lab, broker adapter, Billing surface, Widget or provider integration may invent:

- BUY/SELL intent;
- a new entry;
- strategic close;
- risk;
- size;
- SL;
- TP;
- trailing policy;
- Core Decision.

### Reliability authority

The Hosting Reliability Lab receives a separate and narrowly scoped infrastructure authority:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

Any autonomous reliability action must retain reconstructable genealogy:

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

Justified non-actions must also be recorded.

The Lab may observe, measure, classify, certify, contain new work, execute an approved stabilization procedure and initiate a Hosting failover process only when evidence + policy authorize it.

It may not create or alter trading strategy.

## Existing MISSION-08 authority remains mandatory

This program reuses rather than replaces the closed MISSION-08 single-writer controls.

At all times:

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
REGISTRY != AUTHORITY
HEALTH != AUTHORITY
TELEMETRY != AUTHORITY
ORCHESTRATOR != LEASE AUTHORITY
```

Failover continues to require containment, previous authority removal, fencing, reconciliation, healthy/current replacement evidence and canonical N+1 lease acquisition.

No heartbeat, latency spike or provider disconnect directly activates a backup runtime.

## Ambiguity / retry rule

The program preserves:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

Never:

```text
AMBIGUITY -> RETRY ORDER
```

No provider adapter may convert lost ACK, timeout or unknown external order state into automatic duplicate redispatch.

## Failure-domain separation

Three redundancy domains remain independent:

```text
Infrastructure redundancy       = SERVER A -> SERVER B
Market-data redundancy          = FEED A -> FEED B
Execution-provider portability  = BROKER ADAPTER A/B/N
```

A failure in one domain does not authorize a switch in another without explicit evidence, policy and authority.

## Minimum provider requirement

The program requires certification against a minimum of three independent Futures broker/API providers:

1. TradeStation
2. Interactive Brokers / IBKR
3. tastytrade

Tradovate/NinjaTrader remains an optional fourth candidate until separately verified and authorized.

No concrete provider object may leak into Core.

Each of the mandatory three providers requires two independent certification tracks:

### Market Data Certification

Must cover at least:

- quote/trade/bar connectivity;
- futures instrument identity mapping;
- provider timestamp preservation;
- source identity;
- normalization into canonical QORE messages;
- continuity;
- gaps;
- duplicates;
- out-of-order events;
- delayed/stale data;
- reconnect behavior;
- candle integrity;
- ingress latency;
- sanitization and `SecretRef` boundaries.

### Execution Certification

Initial execution certification is strictly:

```text
PAPER / SIMULATION ONLY
```

Must cover at least:

- authorized order request derived from a valid Core Decision;
- ACK;
- rejection;
- fills;
- partial fills;
- idempotency/duplicate protection;
- lost/ambiguous ACK containment;
- execution reconciliation;
- egress and round-trip timing;
- safe reconnect;
- no real capital.

## External provider verification — 2026-08-09

The target set was re-checked against official provider documentation before program opening.

### TradeStation

Official documentation currently confirms:

- API v3 supports Futures;
- market-data snapshot/stream surfaces are available;
- authenticated API access uses bearer-token authorization;
- a dedicated SIM API exists for paper trading using simulated accounts/money;
- API-key scope/account access remains an external prerequisite.

Official references:

```text
https://api.tradestation.com/docs/
https://api.tradestation.com/docs/specification/
https://api.tradestation.com/docs/fundamentals/sim-vs-live/
https://api.tradestation.com/docs/fundamentals/authentication/auth-overview/
```

### Interactive Brokers / IBKR

Official IBKR documentation currently confirms:

- Web API and TWS API provide market-data/trading interfaces;
- paper accounts may use IBKR APIs with simulator-specific limitations;
- live market-data API access commonly requires the relevant subscriptions/permissions;
- Web API usage for an individual paper account still depends on an associated live account being fully open and funded;
- Futures market-data/API usage may carry exchange/compliance requirements.

These access requirements are external certification gates, not Core assumptions.

Official references:

```text
https://ibkrcampus.com/campus/ibkr-api-page/getting-started/
https://ibkrcampus.com/campus/ibkr-api-page/webapi-doc/
https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/
https://ibkrcampus.com/campus/ibkr-api-page/market-data-subscriptions/
```

### tastytrade

Official tastytrade documentation currently confirms:

- Open API exposes market data and trading surfaces including Futures;
- a sandbox/certification environment exists;
- sandbox account state resets periodically;
- sandbox quotes are documented as delayed by 15 minutes;
- sandbox and Production credentials/environments are separate.

Therefore the future tastytrade adapter may not claim realtime Futures market-data or Futures paper-execution certification merely because the sandbox API is reachable. Exact instrument/data/execution capability must be proven at its own delivery gate.

Official references:

```text
https://tastytrade.com/api/
https://developer.tastytrade.com/
https://developer.tastytrade.com/sandbox/
https://developer.tastytrade.com/faq/
```

Provider terms, entitlements, endpoints and sandbox behavior are mutable external facts and must be revalidated again at each provider-specific delivery.

## Hosting Reliability Lab scope

The Lab is outside Core and must independently certify:

- runtime/server health;
- heartbeat and freshness;
- ingress latency;
- internal processing latency;
- egress latency;
- round-trip latency when ACK exists;
- jitter;
- loss/gaps when measurable;
- market-data integrity;
- candle integrity;
- provider-route health;
- failover readiness;
- recovery/post-action certification.

The Lab must distinguish a healthy ingress from a healthy egress. One aggregate latency average is insufficient.

## Latency safety envelope

The program must implement a certified operating valley/envelope using at least:

- minimum;
- p50;
- p95;
- p99;
- maximum;
- jitter;
- spike count;
- sustained deterioration;
- packet/message loss when measurable;
- ingress/internal/egress/round-trip paths.

The initial non-production catastrophic ceiling remains:

```text
300 ms = PROVISIONAL CATASTROPHIC HARD CEILING
```

It is not an acceptable operating target and must be recalibrated from evidence.

A severe ceiling breach authorizes containment/incident evidence capture according to policy. It does not by itself authorize server failover.

## Market-data integrity

The program must create provider-neutral integrity evidence capable of distinguishing at least concepts equivalent to:

```text
VALID
DELAYED
GAP_DETECTED
DUPLICATE
OUT_OF_ORDER
CORRUPTED
QUARANTINED
```

The system must validate timestamp/continuity/OHLC/trade/volume semantics when applicable and preserve source + normalization evidence.

Suspect data may be classified/degraded/quarantined under policy. The Lab must not silently fabricate a replacement candle.

## Shadow Core gate

Before Paper/SIM execution certification, approved market data must feed Core through canonical boundaries while all executable output terminates at a safe null/shadow boundary.

Shadow certification must prove:

- provider neutrality;
- full-session continuity;
- auditable decisions/rationales;
- no live order path;
- market-data anomaly containment;
- Hosting reliability containment without strategic mutation.

## Program deliveries

The roadmap work packages are formalized as the following repository delivery sequence:

1. `QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001` — Program Scope & Authority Contracts
2. `QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001` — Hosting Reliability Lab Contracts
3. `QORE-LATENCY-SAFETY-ENVELOPE-001` — Latency Safety Envelope
4. `QORE-HOSTING-IO-CERTIFICATION-001` — Hosting I/O Measurement & Certification
5. `QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001` — Market Data Integrity & Candle Certification
6. `QORE-RELIABILITY-INCIDENT-GENEALOGY-001` — Reliability Incident & Rationale Genealogy
7. `QORE-EVIDENCE-GOVERNED-FAILOVER-001` — Evidence-Governed Stabilization & Failover
8. `QORE-FUTURES-ADAPTER-CONTRACTS-001` — Futures Provider-Neutral Adapter Contracts
9. `QORE-FUTURES-TRADESTATION-ADAPTER-001` — TradeStation Certification Adapter
10. `QORE-FUTURES-IBKR-ADAPTER-001` — IBKR Certification Adapter
11. `QORE-FUTURES-TASTYTRADE-ADAPTER-001` — tastytrade Certification Adapter
12. `QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001` — Three-Provider Cross-Certification
13. `QORE-FUTURES-TRADOVATE-CANDIDATE-001` — Optional Tradovate/NinjaTrader Candidate Evaluation
14. `QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001` — Shadow Futures Core Runtime Certification
15. `QORE-HOSTING-RELIABILITY-DRILL-001` — Hosting Redundancy & Emergency Drill
16. `QORE-PAPER-FUTURES-E2E-001` — Paper Futures Execution E2E
17. `QORE-FUTURES-RELIABILITY-CLOSURE-001` — Program Closure / Certification Review

Delivery 13 is optional and cannot replace Deliveries 9–11 unless a later repository change explicitly revises the mandatory target set with rationale.

Provider-specific deliveries may split into smaller independently reviewable PRs when the canonical scope document for that delivery requires it; such subdivision may not weaken the three-provider or two-certification requirements.

## External access gates

Real provider certification may require human/operational prerequisites such as:

- provider accounts;
- API applications/keys;
- market-data subscriptions;
- paper/SIM credentials;
- exchange agreements;
- compliance acknowledgements;
- provider approval.

Absence of those prerequisites is a blocker only for the delivery that needs them. It does not block offline contracts, deterministic certification logic, or unrelated providers.

No credential value may be committed or posted. Only opaque `SecretRef` references are permitted in QORE repository state.

## Issue #146

MISSION-03 issue #146 remains independent and OPEN/BLOCKED until its real OANDA Practice evidence criteria are satisfied.

This Futures/Reliability program does not fabricate or substitute that evidence and does not use #146 as a reason to stop unrelated non-production construction.

## Production boundary

The following remain CLOSED throughout this program unless a later explicit repository authorization changes them:

```text
Production
real capital
Production broker execution
Futures Production
Native Broker Production
productive automatic failover
productive cloud/VPS/Kubernetes control
productive credentials in repository state
```

Shadow, Paper, Simulation and Certification are not Production authorization.

## Quality Gate

Every delivery must pass its exact PR head through the unchanged repository Quality Gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No safety test, typing guarantee or coverage requirement may be weakened merely to obtain GREEN CI.
