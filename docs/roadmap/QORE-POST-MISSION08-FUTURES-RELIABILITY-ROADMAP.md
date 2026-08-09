# QORE Post-MISSION-08 Futures & Hosting Reliability Construction Roadmap

## Status

**PLANNED — CANONICAL POST-MISSION ROADMAP — NON-PRODUCTION**

This document records the agreed construction organigram that follows formal closure of MISSION-08.

It is a roadmap, not Production authorization and not a retroactive expansion of MISSION-08. Each implementation stage must be opened as an explicit repository mission/delivery and must pass the unchanged QORE Quality Gate before it can become canonical implementation.

The repository remains the single source of truth.

## Strategic objective

After MISSION-08 closes, QORE must prove that the existing provider-neutral architecture can operate continuously against real futures-market interfaces without coupling Core to any broker, without real-capital execution, and with independently certified Hosting reliability.

The program must demonstrate all of the following:

```text
MINIMUM 3 INDEPENDENT FUTURES BROKER/APIs
        -> SEPARATE CERTIFIED ADAPTERS
        -> CANONICAL QORE BOUNDARIES
        -> HOSTING RUNTIME
        -> CORE
        -> SHADOW / PAPER-ONLY EXECUTION
```

and, independently:

```text
HOSTING RELIABILITY LAB
        -> OBSERVE
        -> MEASURE
        -> CERTIFY
        -> EXPLAIN
        -> CONTAIN / RECOVER / FAILOVER ONLY WHEN EVIDENCE + POLICY JUSTIFY IT
```

## Non-negotiable authority model

### Trading authority

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Core is the only strategic trading authority.

Core connects directly to **zero** concrete broker APIs. Broker/provider integrations exist only behind approved adapters and canonical ports.

Neither Hosting, Billing, Widget, a broker adapter nor the Reliability Lab may create BUY/SELL intent, change strategy, change risk, invent a position-management action or originate a new trade.

### Reliability authority

The Hosting Reliability Lab has narrowly scoped operational authority over infrastructure stability. It may observe, certify, contain new work, execute approved recovery procedures and initiate Hosting failover only when repository-approved policy and measured evidence justify the action.

Canonical rule:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

Every autonomous Lab action must be reconstructable from immutable evidence:

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

The Lab must also preserve evidence for justified **non-action** when an anomaly does not satisfy intervention thresholds.

## Construction organigram

```text
                                      QORE CORE
                                         |
                               CANONICAL QORE CONTRACTS
                                         |
                   +---------------------+---------------------+
                   |                                           |
          FUTURES MARKET DATA EDGE                     FUTURES EXECUTION EDGE
                   |                                           |
          Provider Adapter Registry                    Broker Adapter Registry
            |          |          |                      |         |         |
       TradeStation   IBKR   tastytrade             Adapter A  Adapter B  Adapter C
            |          |          |                      |         |         |
            +----------+----------+----------------------+---------+---------+
                                         |
                              QORE MANAGED HOSTING RUNTIME
                                         |
                     +-------------------+-------------------+
                     |                   |                   |
              INGRESS MEASUREMENT   INTERNAL PIPELINE   EGRESS MEASUREMENT
                     |                   |                   |
                     +-------------------+-------------------+
                                         |
                              HOSTING RELIABILITY LAB
                                         |
             +---------------------------+---------------------------+
             |                           |                           |
       LATENCY SAFETY LAB        MARKET DATA INTEGRITY       AVAILABILITY / FAILOVER
             |                           |                           |
       valley/envelope               candle quality            heartbeat / leases
       p50/p95/p99/max               gaps/duplicates           fencing / reconcile
       jitter/loss                   out-of-order              server redundancy
       ingress/egress                timestamp/OHLC            recovery evidence
```

The names above identify logical boundaries. Concrete module/package names remain subject to the future mission design review.

## Minimum broker-adapter requirement

The first real Futures certification program must integrate **at least three independent broker/API adapters**.

Initial target set:

1. **TradeStation**
2. **Interactive Brokers (IBKR)**
3. **tastytrade**

A fourth candidate, **Tradovate/NinjaTrader**, should be evaluated after the minimum three-adapter proof is complete or earlier if access requirements are satisfied.

API access terms, market-data entitlements, sandbox/paper behavior and account prerequisites are external facts and must be re-verified from official provider documentation when each adapter delivery begins. They must not be hardcoded as permanent assumptions in Core.

### Why three are mandatory

One provider proves connectivity.

Two providers prove that the canonical contract is not accidentally shaped around one provider.

Three providers provide the minimum cross-provider evidence required to certify QORE as genuinely provider-neutral under materially different external APIs.

There is no fixed architectural maximum number of brokers inside Core because Core does not own concrete broker integrations. New providers must be added through independently certified adapters.

## Market Data Edge certification

Market Data and Execution are separate certification surfaces.

Each provider adapter must independently demonstrate:

- authenticated or otherwise approved read-only market-data connectivity where required;
- futures instrument identity mapping;
- provider timestamp preservation;
- bid/ask/trade normalization as applicable;
- deterministic conversion into canonical QORE market-data contracts;
- no provider-specific object leakage into Core;
- duplicate detection;
- out-of-order detection;
- gap detection;
- malformed payload rejection;
- stale/delayed-data detection;
- reconnect behavior;
- source identity preservation;
- sanitized operational evidence;
- no secret values in logs, snapshots or repository state.

## Candle-quality certification

The Reliability/Data Integrity boundary must continuously verify that the stream presented to Core is internally coherent.

At minimum it must observe and report:

- candle interval continuity;
- open/high/low/close invariants;
- volume/trade-count semantics when provided;
- missing intervals;
- duplicated intervals;
- out-of-order events;
- timestamp drift;
- late updates;
- provider/source mismatch;
- impossible price relationships;
- normalization anomalies;
- divergence between provider event and canonical Core input.

The Lab may classify or quarantine suspect data according to approved contracts. It must not silently fabricate or rewrite market history merely to make the feed look valid.

Expected closed-state vocabulary should distinguish at least concepts equivalent to:

```text
VALID
DELAYED
GAP_DETECTED
OUT_OF_ORDER
CORRUPTED
QUARANTINED
```

Exact enum names belong to the implementation mission.

## Cross-provider market-data comparison

The minimum three adapters must be capable of running in parallel for comparable futures instruments/sessions so the certification system can compare provider behavior.

The comparison boundary should analyze:

```text
provider timestamp
arrival timestamp
price / quote shape
OHLC construction
trades / volume semantics
continuity
missing messages
duplicates
out-of-order events
latency
jitter
reconnect behavior
```

Cross-provider disagreement is evidence requiring classification; it is not automatic permission for one provider to overwrite another provider's canonical evidence.

## Hosting I/O certification

Hosting must never be certified with a single aggregate latency number.

Every relevant flow must preserve sufficient monotonic timing evidence to separate:

```text
PROVIDER EVENT
 -> HOSTING INGRESS
 -> NORMALIZATION START/END
 -> CORE INGRESS
 -> CORE PROCESSING / DECISION
 -> HOSTING EGRESS
 -> ADAPTER RECEIVE
 -> PAPER/SIMULATOR/BROKER ACK WHEN APPLICABLE
```

Required independent certification surfaces:

1. **Ingress Certificate** — external provider to Hosting arrival.
2. **Internal Processing Certificate** — Hosting ingress through normalization and Core delivery/processing.
3. **Egress Certificate** — authorized Core output through Hosting to the selected adapter boundary.
4. **Round-Trip Evidence** — end-to-end timing where an acknowledgement exists.
5. **Availability & Failover Certificate** — continuity and safe authority transfer across redundant servers.

A healthy ingress does not imply a healthy egress. A healthy egress does not imply valid market-data ingress. Each surface fails and recovers independently.

## Latency Safety Envelope

The Reliability Lab must maintain a certified operating valley/envelope instead of relying only on an average latency value.

Conceptual states:

```text
CERTIFIED / OPTIMAL VALLEY
 -> WARNING
 -> DEGRADED
 -> CONTAINED
 -> EMERGENCY
 -> FAILOVER ELIGIBLE
 -> FAILOVER AUTHORIZED
 -> RECOVERING
 -> CERTIFIED
```

The implementation must measure at least:

- minimum observed latency;
- p50;
- p95;
- p99;
- maximum;
- jitter;
- packet/message loss when measurable;
- spike count;
- sustained-threshold duration;
- ingress latency;
- internal processing latency;
- egress latency;
- end-to-end latency.

### Relative thresholds

The Lab must react to statistically significant deterioration from the certified normal valley before an absolute catastrophic ceiling is reached.

A path that normally operates at materially lower latency may enter WARNING or DEGRADED even while still below the absolute hard ceiling.

### Initial emergency hard ceiling

For initial non-production Futures testing, **300 ms is a provisional catastrophic hard ceiling**, not a normal operating target.

Any measured critical path that breaches the approved hard ceiling must immediately:

```text
CONTAIN NEW WORK
 -> OPEN RELIABILITY INCIDENT
 -> CAPTURE EVIDENCE
 -> IDENTIFY INGRESS / INTERNAL / EGRESS SOURCE
 -> EXECUTE AUTHORIZED STABILIZATION POLICY
```

A hard-ceiling breach does **not** by itself authorize blind server replacement. The Lab must still establish whether the active runtime is unsafe and whether a replacement runtime is safe.

The 300 ms value must be recalibrated — normally downward for latency-sensitive Futures operation — from actual measured provider/server distributions during the certification program. Any production threshold would require separate explicit authorization.

## Periodic Reliability reporting

The Lab must report normal operation as well as incidents.

At minimum the future implementation must produce three evidence classes.

### Periodic Reliability Report

Must include, per server/runtime and relevant provider route:

- current certification state;
- ingress, internal and egress distributions;
- p50/p95/p99/max;
- jitter;
- loss/gaps;
- heartbeat/health;
- current execution-authority identity without exposing secrets;
- market-data integrity status;
- candle-quality status;
- reconnect history;
- failover-readiness observation;
- reporting window and evidence timestamp.

### Anomaly Report

Must include:

- anomaly identity;
- start/detection timestamp;
- affected boundary;
- severity;
- measured evidence;
- violated threshold/policy;
- whether new work was contained;
- stabilization actions attempted;
- result.

### Incident / Recovery Report

Must include:

- initiating evidence;
- rationale;
- policy authorizing action;
- previous runtime/server;
- replacement runtime/server when applicable;
- lease/fencing evidence;
- reconciliation status;
- ambiguity status;
- recovery action sequence;
- post-action ingress certification;
- post-action egress certification;
- final stability result.

## Stabilization before failover

The Lab's primary mission is stability, not server churn.

When degradation is detected, approved stabilization procedures should run according to policy before failover when the incident allows it.

A conceptual decision path is:

```text
ANOMALY
 -> CLASSIFY
 -> CONTAIN WHEN REQUIRED
 -> DIAGNOSE LOCATION
 -> AUTHORIZED STABILIZATION ATTEMPT(S)
 -> RE-MEASURE
 -> STABLE ? CERTIFY : EVALUATE FAILOVER
```

Policies must define which emergency classes may bypass slower stabilization attempts while still preserving fencing and reconciliation requirements.

## Evidence-based server failover

Hosting redundancy requires at least one active runtime and one or more eligible replacement runtimes; redundancy itself grants no trading authority.

The Lab may initiate failover only when all required evidence gates are satisfied.

Canonical safety assertion:

```text
CURRENT RUNTIME UNSAFE
AND
REPLACEMENT RUNTIME CERTIFIED SAFE
AND
AUTHORIZED FAILOVER POLICY SATISFIED
AND
PREVIOUS AUTHORITY REVOKED OR EXPIRED
AND
PREVIOUS GENERATION FENCED
AND
EXTERNAL / EXECUTION STATE RECONCILED
AND
NO BLOCKING AMBIGUITY
=
NEW LEASE MAY BE ACQUIRED
```

The existing MISSION-08 sequence remains mandatory:

```text
contain new work
 -> revoke/expire current lease
 -> fence previous generation
 -> reconcile
 -> resolve ambiguity
 -> certify replacement health
 -> acquire new fenced lease generation
 -> verify ingress
 -> verify egress
 -> resume authorized work
```

`UNREACHABLE`, high latency or a missed heartbeat may trigger containment/incident handling but must never directly create a second writer.

## Failure-domain separation

The program must keep three redundancy domains distinct.

### Infrastructure redundancy

```text
Hosting Server A -> Hosting Server B
```

### Market-data provider redundancy

```text
Market Data Provider A -> Provider B
```

### Execution-provider portability

```text
Broker Adapter A / Broker Adapter B / Broker Adapter N
```

A failure in one domain must not automatically imply a switch in another domain without an explicit policy, evidence and authority boundary.

## Shadow Core validation

Before any paper-order certification, Core must run in shadow mode against real or otherwise approved futures market data.

Required proof:

- Core remains provider-neutral;
- Core consumes only canonical normalized messages;
- Core processes complete sessions continuously;
- no live order can leave the system;
- decisions/rationales remain auditable;
- market-data anomalies fail closed according to approved policy;
- Hosting degradation can contain new executable work without changing Core strategy;
- the Lab cannot create a Core Decision.

## Paper / simulated execution validation

Only after read-only market data, candle quality, Hosting I/O and shadow Core are certified may an adapter enter paper/simulated execution testing.

The execution path must measure at least:

```text
CORE DECISION
 -> AUTHORIZED EXECUTION ENVELOPE
 -> HOSTING EGRESS
 -> BROKER ADAPTER
 -> PAPER/SIM ORDER ACK
 -> FILL / PARTIAL / REJECT
 -> EXECUTION RECONCILIATION
```

The program must verify:

- no decisionless orders;
- no duplicate redispatch after ambiguity;
- ACK latency;
- reject handling;
- partial-fill handling;
- execution reconciliation;
- single-writer authority;
- safe reconnect;
- safe failover with no duplicate order emission.

## Provider certification matrix

Each adapter must carry independent certification states rather than one global PASS flag.

Required certification dimensions:

```text
MARKET DATA CONNECTIVITY
MARKET DATA QUALITY
CANDLE INTEGRITY
INGRESS LATENCY
INTERNAL DELIVERY
HOSTING EGRESS
RECONNECT
SHADOW CORE
PAPER EXECUTION
EXECUTION RECONCILIATION
FAILOVER SAFETY
SECRET / LOG SANITIZATION
```

A provider is not considered fully certified merely because its API can connect.

## Planned construction sequence

The exact mission identifier is intentionally not invented here. After MISSION-08 closure, the next authorized mission should convert the following ordered work packages into repository deliveries.

1. **Program Scope & Authority Contracts**
   - formalize Futures/Hosting Reliability mission boundary;
   - preserve `NO CORE DECISION -> NO NEW TRADING ACTION`;
   - formalize `NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION`.

2. **Hosting Reliability Lab Contracts**
   - observations, evidence, assessments, policies, rationale and action records;
   - no trading authority.

3. **Latency Safety Envelope**
   - independent ingress/internal/egress distributions;
   - warning/degraded/emergency states;
   - provisional 300 ms non-production catastrophic ceiling;
   - dynamic recalibration contracts.

4. **Hosting I/O Measurement & Certification**
   - event timestamps;
   - ingress/internal/egress/round-trip certificates;
   - periodic reporting.

5. **Market Data Integrity & Candle Certification**
   - gaps, duplicates, out-of-order, timestamp/OHLC invariants and quarantine evidence.

6. **Reliability Incident & Rationale Genealogy**
   - observation -> evidence -> policy -> assessment -> rationale -> action -> result;
   - justified non-action evidence.

7. **Evidence-Governed Stabilization & Failover**
   - stabilization procedures;
   - emergency containment;
   - reuse MISSION-08 lease/fencing/reconciliation;
   - certify replacement before transfer.

8. **Futures Provider-Neutral Adapter Contracts**
   - market-data and execution boundaries separated;
   - no concrete provider imports into Core.

9. **Broker Adapter #1 — TradeStation**
   - read-only market data first;
   - shadow validation;
   - paper/SIM only after certification.

10. **Broker Adapter #2 — IBKR**
    - same canonical requirements independently verified.

11. **Broker Adapter #3 — tastytrade**
    - same canonical requirements independently verified.

12. **Three-Provider Cross-Certification**
    - parallel comparable instrument/session observation;
    - provider-neutrality evidence;
    - divergence and latency analysis.

13. **Tradovate/NinjaTrader Candidate Adapter**
    - optional fourth provider once access requirements are confirmed;
    - cannot replace the mandatory three-provider minimum unless the future mission explicitly revises the target set with rationale.

14. **Shadow Futures Core Runtime Certification**
    - prolonged real-market-data observation;
    - no order authority.

15. **Hosting Redundancy & Emergency Drill**
    - controlled latency degradation;
    - server failure;
    - fencing;
    - reconciliation;
    - certified failover;
    - no split-brain.

16. **Paper Futures Execution E2E**
    - Core Decision -> authorized paper execution -> ACK/fill/reject -> reconciliation;
    - ingress and egress measurement maintained throughout.

17. **Program Closure / Certification Review**
    - re-audit all authority boundaries;
    - verify minimum three adapters certified;
    - verify Lab reporting and evidence genealogy;
    - verify failover without duplicate writer/action;
    - verify Production remains CLOSED unless separately authorized.

## Required failure-injection program

The certification mission must intentionally test at least:

- feed disconnect;
- provider throttling/unavailable state;
- malformed market message;
- missing candle interval;
- duplicated event;
- out-of-order event;
- delayed event;
- latency spike;
- sustained latency deterioration;
- ingress healthy / egress degraded;
- egress healthy / ingress degraded;
- runtime CPU/resource pressure where safely reproducible;
- heartbeat loss;
- active-server failure;
- replacement server unhealthy;
- ambiguous external execution state;
- stale fencing generation;
- reconnect during open authorized lifecycle;
- paper-order acknowledgement delay;
- partial fill;
- reject;
- ambiguous execution acknowledgement;
- attempted duplicate redispatch.

Every test must be deterministic where possible and must never require real-capital execution.

## Evidence genealogy

Trading/execution evidence continues to preserve the canonical genealogy:

```text
ACTION -> POSITION -> CORE DECISION -> POLICY -> RATIONALE -> EVIDENCE
```

Reliability actions add a parallel infrastructure genealogy:

```text
INFRASTRUCTURE ACTION
 -> LAB ASSESSMENT
 -> RELIABILITY POLICY
 -> RATIONALE
 -> OBSERVATIONS
 -> MEASUREMENTS
 -> EVIDENCE
```

The two genealogies may be correlated but must never be collapsed into a single authority domain.

## Production boundary

Nothing in this roadmap authorizes:

- real-capital futures orders;
- Production broker execution;
- productive credentials committed to repository state;
- automatic provider switching without approved policy/evidence;
- automatic order redispatch after ambiguity;
- Lab-created trading decisions;
- Billing-created trading actions;
- Widget-created trading actions;
- two simultaneous execution writers for one TradingAccountId;
- bypassing MISSION-03 issue #146 acceptance criteria;
- declaring Hosting/Futures pricing without separate commercial authorization.

Production remains **CLOSED** until a later explicit repository authorization and independent operational certification.

## Entry condition

Implementation of this roadmap begins only after formal MISSION-08 closure and verification of the then-current repository state.

The future mission must re-check provider/API availability from official documentation, define exact acceptance evidence, create dedicated branches/PRs per delivery, and merge only exact heads with GREEN QORE CI.

## Quality Gate

Every implementation delivery created from this roadmap must continue to pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No safety test may be deleted merely to obtain GREEN CI. No `type: ignore`, unsafe cast or suppression shortcut is authorized without exceptional architectural justification.