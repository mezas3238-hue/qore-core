# QORE Shared↔Trader Intelligence — ADR-001

## Status

**PROPOSED / OWNER-DIRECTIVE IMPLEMENTATION / NON-PRODUCTIVE**

Primary PR: #635  
Owner law: `QORE_SHARED_PROACTIVE_TRADER_INTELLIGENCE_OWNER_DIRECTIVE_007.md`

## Decision

Adopt the following canonical authority chain:

```text
WORLD
  ↓
SHARED
  cognition / discovery / warning / support / explanation
  ↓
TRADER
  setup / trade thesis / entry / position management / exit
  ↓
CIBO
  sizing / allocation / reserve / release / compounding
  ↓
RISK
  hard survivability authorization
  ↓
EXECUTION
  broker mutation
```

Binding summary:

```text
SHARED DISCOVERS AND WARNS.
TRADER TRADES.
CIBO CAPITALIZES.
RISK PROTECTS.
EXECUTION MATERIALIZES.
```

## 1. Why this ADR exists

Shared's existing Cognitive OS and Global Perception architecture allows deep
observation, inference and communication, but it did not yet define a precise
machine boundary for proactive Trader-facing cognition.

This ADR prevents the new proactive role from becoming a hidden strategy,
capital allocator, Risk governor or broker actor.

## 2. Authority matrix

| Capability | Shared | Trader | CIBO | Risk | Execution |
|---|---:|---:|---:|---:|---:|
| observe global world | yes | bounded | bounded | bounded | bounded |
| form market hypothesis | yes | yes within methodology | no trade setup authority | no | no |
| discover attention-worthy market | yes | may consume | no | no | no |
| validate Trader setup | no | **yes** | no | no | no |
| choose entry timing | no | **yes** | no | no | no |
| define technical stop/target | no | **yes** | no | no | no |
| monitor world around position | **yes** | yes | may consume facts | may consume facts | no |
| emit position-threat evidence | **yes** | consume | consume if certified | consume if relevant | no |
| choose HOLD/PROTECT/PARTIAL/EXIT | no | **yes** | no | survivability only | materialize only |
| position sizing | no | no | **yes** | reduce/reject safety | no |
| capital allocation | no | no | **yes** | safety constraints | no |
| Risk ALLOW/REDUCE/REJECT | no | no | no | **yes** | no |
| broker mutation | no | no | no | no | **yes** |

## 3. Shared cognition products

Shared may publish typed products:

```text
SharedTraderIntelligenceSnapshot
SharedOpportunityAlert
SharedRegimeTransitionAlert
SharedContinuationSupport
SharedWorldExplanation
SharedPositionObservationSubscription
SharedPositionThesisDelta
SharedPositionThreatAlert
SharedTraderRelevantProjection
```

These products carry facts/hypotheses/evidence only.

They contain no executable order intent, quantity, volume, stop replacement,
target replacement, capital amount, Risk authorization or broker instruction.

## 4. Opportunity boundary

```text
SharedOpportunityAlert
!=
Trader Valid Trade
```

A Shared opportunity means:

> this market deserves attention under the current evidence.

A Trader trade means:

> this Trader's certified methodology has independently produced a valid trade.

No adapter may automatically transform the first into the second.

Required transition:

```text
SHARED ATTENTION CANDIDATE
→ TRADER EVALUATION
→ EXECUTE / WAIT / ABSTAIN
```

Only the Trader's valid opportunity can proceed to CIBO.

## 5. Position boundary

Shared may observe the world around an open position.

It may compare:

```text
ENTRY_WORLD_SNAPSHOT
vs
CURRENT_WORLD_SNAPSHOT
```

and produce deltas.

It may not:

- move stop;
- move target;
- close;
- partially close;
- add;
- reduce;
- resize;
- hedge;
- extend expiry;
- alter Trader methodology.

The Trader consumes the delta according to its own certified Position
Intelligence.

## 6. CIBO boundary

CIBO may later consume certified Shared facts only through a read-only
evidence contract after a Trader has emitted a valid opportunity.

CIBO owns:

- requested sizing;
- marginal capital utility;
- portfolio allocation;
- reserve;
- release;
- protection;
- compounding;
- Internal Capital Market;
- Core Compound Portfolio.

Shared cannot express those decisions.

## 7. Risk boundary

Risk remains the hard survivability governor.

Shared systemic-stress intelligence is not a Risk decision and may not create a
global fear blocker.

Risk remains free to reject despite:

- Trader validation;
- positive Shared intelligence;
- CIBO allocation intent.

## 8. Execution boundary

There is no direct Shared→Execution path.

There is no direct Shared→broker path.

Any module importing a broker-mutation boundary into the canonical STI contract
layer is a governance defect.

## 9. Global truth and projection

Canonical separation:

```text
GLOBAL_WORLD_STATE
→ TRADER_RELEVANT_PROJECTION
```

Projection is a relevance filter only.

Projection cannot modify, reinterpret or fabricate the underlying global
state.

Trader methodology is not copied into Shared world truth.

## 10. Causal time

Every STI product carries causal time.

Minimum invariant:

```text
evidence_cutoff_at <= observed_at
```

A consumer additionally requires:

```text
observed_at <= consumer_decision_time
```

Future outcomes, future prices, future reports, future weather, future rolls or
future position outcomes are forbidden.

## 11. Confidence law

STI separates:

- support strength;
- uncertainty;
- epistemic state;
- calibration status.

A support score is not a probability.

A confidence value may not be labeled calibrated unless tied to explicit
calibration evidence/version.

## 12. Alert law

Alerts are state transitions, not repeated prose.

Every alert carries:

- stable alert identity;
- hypothesis identity;
- lifecycle state;
- created-at;
- updated-at;
- evidence cutoff;
- version;
- evidence refs.

Unchanged state is not a new alert.

## 13. Fast path / deep path

STI consumes precomputed Shared cognition.

```text
DEEP PATH:
world reconstruction
relation science
regime research
opportunity research

FAST PATH:
read latest admissible snapshot
project relevance
emit material transition
```

No Trader hot path may synchronously reconstruct the global world.

## 14. Failure semantics

Fail closed to:

```text
INSUFFICIENT
UNKNOWN
CONTRADICTORY
DATA_UNRELIABLE
STALE
HORIZON_MISMATCH
RELATION_NOT_COMPARABLE
```

No state is forced bullish/bearish.

An empty opportunity board is legal.

## 15. Productive-admission law

Architecture, passing tests and deterministic synthetic state machines do not
certify predictive value.

Productive use requires separate:

```text
PREREGISTRATION
→ CONTROL/TREATMENT
→ OOS
→ STRESS
→ REPLICATION
→ GOVERNANCE
→ PROMOTION
```

Shared certification and Swing Trader certification remain separate.

## 16. Consequences

This ADR intentionally creates a powerful proactive cognitive role while
preserving authority separation.

It enables Shared to say:

```text
"potential opportunity"
"regime transition risk rising"
"position thesis support deteriorating"
"continuation support remains strong"
```

It does not enable Shared to say:

```text
"enter now"
"buy this size"
"move stop"
"exit now"
"Risk must reject"
```

unless a future explicit Owner ADR changes the relevant authority.
