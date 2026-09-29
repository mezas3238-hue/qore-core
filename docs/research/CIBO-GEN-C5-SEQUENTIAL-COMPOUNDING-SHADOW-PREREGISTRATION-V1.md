# CIBO GEN-C5 — SEQUENTIAL COMPOUNDING SHADOW PREREGISTRATION V1

Status: PREREGISTERED / PRE-OUTCOME / RESEARCH ONLY  
Primary PR: #651  
Research lineage: CIBO_SOVEREIGN_CAPITAL_COMPOUNDING_RESEARCH_V1  
Policy identity: CIBO_GENC5_PROTECTED_FLOOR_GATED_SEQUENTIAL_COMPOUND_SHADOW_V1  
Frozen effective time: 2026-09-29T17:10:00+00:00

## 1. Purpose

GEN-C5 tests whether a causal sequential gate can decide when already-accounted
compound capital is eligible to be forwarded to downstream QORE Risk review.

GEN-C5 V1 does **not** optimize size.

The incremental amount is supplied by the already sealed GEN-C4 marginal-capital
evidence contract and GEN-C5 either:

- holds the capital state; or
- forwards that exact proposed amount for downstream Risk review in shadow.

No broker mutation occurs.

## 2. Control

The control is:

```text
posture = COMPOUND_PAUSED
action  = HOLD_CURRENT_STATE
requested_downstream_risk_review_usd = 0
```

The control represents no sequential compound activation.

## 3. Treatment

The treatment may emit:

```text
posture = CAUTIOUS_COMPOUND
action  = REQUEST_DOWNSTREAM_RISK_REVIEW
requested_downstream_risk_review_usd
    = GEN-C4 requested_incremental_capital_usd
```

only when all of the following are true before outcomes:

1. the GEN-C4 evidence and account portfolio bind to the same account;
2. the GEN-C4 decision time is on/after this policy freeze;
3. the source compound lot is currently one of:
   - COMPOUNDABLE;
   - ACTIVE_COMPOUND_CAPACITY;
   - RELEASED_COMPOUND_CAPITAL;
4. the source lot amount is at least the requested incremental amount;
5. the GEN-C4 current compound capacity exactly matches the portfolio's current
   candidate compound capacity;
6. the account has strictly positive POLICY_PROTECTED or BROKER_GUARANTEED floor;
7. the GEN-C4 evidence contains no outcome and no utility score;
8. every Shared fact actually used by GEN-C4 is already eligible for capital use
   under GEN-C4 validation law.

If any treatment gate is not satisfied, treatment reproduces the control:
COMPOUND_PAUSED / HOLD_CURRENT_STATE / zero requested downstream amount.

## 4. Candidate compound capacity

For this V1 preregistration:

```text
candidate_compound_capacity
=
COMPOUNDABLE
+
ACTIVE_COMPOUND_CAPACITY
+
RELEASED_COMPOUND_CAPITAL
```

The following do not count as current candidate deployable compound capacity:

- REALIZED_PROFIT;
- PROTECTED_PROFIT;
- STRATEGIC_RESERVE;
- OPPORTUNITY_RESERVE;
- DEPLOYED_COMPOUND_CAPITAL;
- RETIRED_TO_PROTECTED_FLOOR;
- CONSUMED.

This is an accounting eligibility definition, not a claim that all candidate
capacity should be deployed.

## 5. Posture ceiling

GEN-C5 V1 may emit only:

- COMPOUND_PAUSED;
- DEFENSIVE;
- CAUTIOUS_COMPOUND.

GEN-C5 V1 may not emit:

- NORMAL_COMPOUND;
- ACCELERATED_COMPOUND;
- SURVIVAL.

Reason:

- NORMAL/ACCELERATED require calibrated economic evidence that does not yet exist.
- SURVIVAL is a Risk-governance concept and GEN-C5 must not infer or usurp QORE
  Risk authority.

DEFENSIVE may be used only to describe an account that has candidate compound
capacity but no policy-protected floor. It still performs HOLD_CURRENT_STATE.

## 6. No amount optimization

GEN-C5 V1 never increases, decreases or synthesizes the GEN-C4 requested
incremental amount.

Binding law:

```text
GEN-C4 PROPOSED INCREMENT
-> GEN-C5 ELIGIBILITY GATE
-> DOWNSTREAM QORE RISK REVIEW
```

Later generations may research marginal amount optimization, but not under this
policy identity.

## 7. Shared boundary

Shared remains read-only.

GEN-C5 may consume only Shared facts already admitted by GEN-C4 as
eligible_for_capital_use.

```text
SHARED INFORMS
CIBO DECIDES WHETHER TO REQUEST CAPITAL REVIEW
RISK AUTHORIZES OR REJECTS
EXECUTION REMAINS DOWNSTREAM
```

## 8. Causal sealing

Each shadow decision must bind:

- policy id;
- policy SHA-256;
- policy frozen time;
- decision time;
- account identity;
- source compound lot id/state/amount;
- account Core Compound Portfolio SHA-256;
- GEN-C4 evidence SHA-256;
- control posture/action/amount;
- treatment posture/action/amount;
- treatment blocker codes;
- whether treatment differs from control.

The decision must contain:

```text
outcome_present_at_seal = false
runtime_authority       = false
risk_authority          = false
execution_authority     = false
live_authority          = false
real_capital_authority  = false
```

## 9. Durable evidence

GEN-C5 shadow decisions must be persisted append-only before any later outcome
reconciliation.

The store must provide:

- SHA-256 payload integrity;
- hash-chain integrity;
- generation CAS;
- cross-process writer lock;
- idempotent identical reseal;
- conflicting rewrite rejection;
- account identity preservation;
- policy identity preservation.

## 10. Outcome evaluation

This preregistration freezes the treatment mechanics before outcomes.

It does not freeze a claim that the treatment is economically superior.

A later GEN-C5 OOS utility protocol must compare treatment and control on the
same causally eligible opportunities and at minimum examine:

- realized ending capital delta;
- settlement-cash drawdown;
- profit retention;
- protected-floor growth;
- time underwater;
- recovery duration;
- optionality consumed/preserved;
- capital-risk-time productivity;
- provider/execution costs;
- tail/stress behavior.

No outcome may be used to rewrite this V1 policy and still be represented as the
same preregistered experiment.

## 11. Holdout / V3 protection

Forbidden development evidence:

`CIBO_USD60_6M_HOLDOUT_2017H1_V1`

It remains SEALED_UNTOUCHED.

GEN-C5 V1 does not modify:

`CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3`

GEN-C5 is a parallel compounding research lineage.

## 12. Authority

This preregistration grants:

- no merge authority;
- no VPS authority;
- no DEMO-governed execution authority;
- no LIVE authority;
- no real-capital authority;
- no Risk authority;
- no broker mutation authority.

## 13. Falsification rule

If fresh OOS/stress evidence later shows that protected-floor-gated sequential
forwarding does not improve the declared compound objective without unacceptable
drawdown, tail, optionality or survival degradation, the policy is FALSIFIED.

The response is not to retune this policy on the same outcomes.

A new policy identity and new preregistration are required.
