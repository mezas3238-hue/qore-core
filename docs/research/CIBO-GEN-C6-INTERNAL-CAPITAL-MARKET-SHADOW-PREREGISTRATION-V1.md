# CIBO GEN-C6 — INTERNAL CAPITAL MARKET SHADOW PREREGISTRATION V1

Status: PREREGISTERED / PRE-OUTCOME / RESEARCH ONLY  
Primary PR: #651  
Research lineage: CIBO_SOVEREIGN_CAPITAL_COMPOUNDING_RESEARCH_V1  
Market identity: QORE_CIBO_INTERNAL_CAPITAL_MARKET  
Policy identity: CIBO_GENC6_ROBUST_PARETO_MARGINAL_CAPITAL_MARKET_SHADOW_V1  
Frozen effective time: 2026-09-29T20:00:00+00:00

## 1. Purpose

GEN-C6 tests how one account-local unit or economically atomic lot of already
eligible compound capital should be allocated when multiple valid opportunities
compete for scarce capital.

GEN-C6 does not rank Traders.

Binding question:

```text
WHERE DOES THE NEXT AVAILABLE UNIT OF ACCOUNT-LOCAL CAPITAL
CREATE THE HIGHEST ROBUST MARGINAL VALUE FOR CORE?
```

Trader identity is provenance only.

## 2. Constitutional boundaries

GEN-C6 extends:

```text
T09 Opportunity Competition
+ T18 Cross-Trader Capital Allocation
+ T19 Portfolio Reservation Accounting
+ T20 Capital Release Accounting
+ GEN-C3 Core Compound Portfolio
+ GEN-C4 Marginal Capital Utility Evidence
+ GEN-C5 Sequential Compounding Eligibility
```

It does not modify the frozen GEN-C5 policy.

It does not modify:

`CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3`

It does not consume or inspect:

`CIBO_USD60_6M_HOLDOUT_2017H1_V1`

Money remains account-local.

Global intelligence may be read-only; no cross-account capital transfer exists.

## 3. Unit of decision

One GEN-C6 clearing decision allocates only the **next marginal legal action**.

An action may be:

- one candidate's exact GEN-C4 marginal capital request; or
- RESERVE / NO_DEPLOYMENT.

A later marginal unit requires a new decision epoch with newly sealed portfolio
state and newly valid candidate evidence.

This creates a discrete marginal utility curve without assuming linear utility
with size.

## 4. Candidate identity

Each opportunity candidate must bind:

- account identity;
- Trader identity for provenance only;
- signal fingerprint;
- qore/provider symbol;
- same decision epoch;
- valid_from / valid_until;
- technical validity;
- cancellation state;
- exact durable GEN-C4 evidence SHA;
- exact durable GEN-C5 decision SHA where GEN-C5 is applicable;
- exact proposed incremental capital;
- exact stop-risk, margin, execution-cost, concentration, drawdown, optionality
  and capital-duration evidence;
- provider feasibility evidence;
- evidence-use metadata.

Candidate membership becomes immutable after the event is sealed.

## 5. Capital-eligible evidence law

Every evidence input exposed to the policy must declare:

- evidence SHA-256;
- produced_at;
- observed_at;
- source;
- policy version;
- calibration lineage;
- eligible_for_capital_use;
- observe_only.

If evidence is not capital-eligible, it may be recorded but it cannot influence
the V1 treatment decision.

Expected value additionally requires model identity and calibration/OOS status.

## 6. Same-time causality

All compared candidates must be causally present at the same decision timestamp.

A candidate discovered after the clearing timestamp cannot be inserted
retrospectively.

No future opportunity arrival or terminal outcome may influence the decision.

## 7. Opportunity validity

A candidate is legally comparable only when at decision time:

- valid_from <= decision_at <= valid_until;
- technical_valid = true;
- cancelled = false;
- it is not expired;
- its account matches the clearing account;
- its GEN-C4 decision timestamp equals the clearing timestamp;
- its GEN-C5 eligibility decision, when required, binds the same GEN-C4 evidence
  and forwards the exact same amount to downstream Risk review.

## 8. Portfolio state

Every clearing must bind a same-account pre-outcome portfolio state containing:

- current compound capacity;
- currently available compound capital;
- active reservations;
- T19 remaining stop-risk headroom;
- T19 remaining margin headroom;
- concentration headroom;
- protected floor;
- distance-to-floor evidence when available;
- compound DD evidence when available;
- base DD evidence when available;
- current deployments;
- factor exposure evidence when available;
- Risk headroom evidence;
- portfolio SHA-256;
- T19 ledger SHA-256.

The state is descriptive evidence. GEN-C6 does not gain Risk authority.

## 9. True scarcity

A clearing event is TRUE_SCARCITY only when:

```text
simultaneously valid fundable candidates >= 2
AND
total requested marginal capital > available compound capital
```

The event records:

- candidate count;
- simultaneous valid count;
- available capital;
- requested capital;
- capital shortfall;
- mutually fundable candidate count;
- competition intensity.

A single-candidate event may be processed but is not evidence of cross-Trader
competition utility.

## 10. Reserve competitor

Every clearing contains one explicit:

`RESERVE_NO_DEPLOYMENT`

alternative.

Reserve is not a failure state.

It represents preserved:

- survival capacity;
- future optionality;
- crisis capacity;
- margin buffer.

V1 does not fabricate a scalar reserve utility.

Reserve becomes the treatment action when the evidence does not establish a
unique robust capital use.

## 11. No weighted-score theater

GEN-C6 V1 does not compute:

```text
w1*expected_value
+ w2*Shared
- w3*uncertainty
...
```

No arbitrary fitted weights exist.

Candidate comparison is based on a preregistered non-compensatory Pareto rule.

## 12. Comparable V1 dimensions

The mandatory V1 capital-eligible comparable dimensions are:

- EXPECTED_NET_VALUE_PER_CAPITAL — higher is better;
- EPISTEMIC_UNCERTAINTY — lower is better;
- CAPITAL_DURATION_MINUTES — lower is better;
- MARGIN_PER_CAPITAL — lower is better;
- EXECUTION_COST_PER_CAPITAL — lower is better;
- CONCENTRATION_RISK_PER_CAPITAL — lower is better;
- DRAWDOWN_RISK_PER_CAPITAL — lower is better;
- OPTIONALITY_CONSUMED_PER_CAPITAL — lower is better.

They must reproduce the bound GEN-C4 values exactly.

The contract also supports:

- FAILURE_HAZARD;
- POSITIVE_TAIL_POTENTIAL;
- FACTOR_CONCENTRATION;
- TAIL_DEPENDENCE;
- PROVIDER_CONSTRAINT_PRESSURE;
- SYSTEMIC_STRESS;
- REGIME_STABILITY;
- CROSS_MARKET_COHERENCE;
- CONTINUATION_SUPPORT;
- OPPORTUNITY_QUALITY;
- RESERVE_VALUE;
- FLOOR_DISTANCE;
- COMPOUND_DD;
- BASE_DD;
- RISK_HEADROOM.

Optional dimensions may influence V1 only when the same dimension is present and
capital-eligible for every treatment-eligible opportunity in that clearing.
Otherwise they remain OBSERVE_ONLY.

## 13. Control

The frozen control is:

`CURRENT_T09_T18_STYLE_RISK_TIME_BASELINE_V1`

It uses the same legal candidate set and chooses the feasible opportunity with
the highest causal:

```text
(expected_incremental_return
 - incremental_execution_cost
 - incremental_optionality_consumed)
/
(incremental_stop_risk * expected_capital_minutes)
```

Tie-break:

1. higher adjusted net value per stop-risk;
2. higher adjusted net value;
3. canonical signal fingerprint lexical order.

Trader identity is never a tie-break.

If no feasible candidate has positive adjusted expected net value, control
chooses RESERVE_NO_DEPLOYMENT.

This control represents the existing T09/T18-style capital-velocity baseline.

## 14. Treatment

The frozen treatment is:

`ROBUST_PARETO_MARGINAL_WITH_RESERVE_V1`

First construct the legal action set.

A candidate is treatment-eligible only when:

- all mandatory V1 dimension evidence is capital-eligible;
- opportunity validity passes;
- exact GEN-C4 binding passes;
- GEN-C5 exact-amount forwarding passes;
- requested capital <= available account-local compound capital;
- T19 stop-risk headroom can absorb the marginal stop risk;
- T19 margin headroom can absorb the marginal margin;
- T19 concentration headroom can absorb the marginal concentration;
- provider feasibility evidence is capital-eligible and says feasible.

For the legal candidate set, A robustly dominates B only if A is no worse than B
on every active comparable dimension and strictly better on at least one.

Treatment chooses a candidate only when exactly one candidate robustly dominates
every other treatment-eligible candidate and its adjusted expected net value is
positive.

Otherwise:

`RESERVE_NO_DEPLOYMENT`

This includes ties, incomparable frontiers, incomplete capital-eligible
evidence, no legal candidate and ambiguous competition.

## 15. No winner-takes-all assumption

One clearing allocates at most one candidate marginal lot.

After that hypothetical allocation, a further unit requires a new clearing with
updated state.

Therefore:

```text
unit 1 -> candidate A
new state
unit 2 -> candidate B
new state
unit 3 -> reserve
```

is representable without assuming that A deserves all capital.

## 16. T19 reservation law

GEN-C6 V1 is shadow-only and does not mutate the runtime T19 ledger.

However every candidate action must pass the exact T19 remaining-budget contract
before it is legal.

The shadow decision seals:

- T19 ledger SHA-256;
- pre-allocation remaining budget;
- proposed shadow reservation;
- no-double-spend guard.

A future promoted implementation must reserve atomically before another
candidate can consume the same capacity.

## 17. T20 release law

GEN-C6 V1 does not fabricate release.

Outcome analysis must later bind to actual settlement/release evidence.

It must distinguish:

- requested capital;
- Risk-authorized capital;
- execution-realized capital;
- release time;
- release latency;
- realized settlement.

Missing release evidence remains missing.

## 18. Control/treatment outputs

Each decision seals:

- control action;
- control selected candidate / reserve;
- control amount;
- treatment action;
- treatment selected candidate / reserve;
- treatment amount;
- treatment/control divergence;
- reasons/blockers;
- true-scarcity flag.

No allocation is sent to Risk by this shadow policy.

## 19. Durable pre-outcome sealing

Each decision must bind:

- decision_id;
- scarcity_event_id;
- policy identity/SHA/frozen time;
- account identity;
- candidate-set SHA;
- candidate evidence SHA list;
- GEN-C4 SHA list;
- GEN-C5 SHA list;
- portfolio-state SHA;
- T19 ledger SHA;
- available compound capital;
- control allocation;
- treatment allocation;
- reserve allocation;
- decision reason;
- outcome_present_at_seal = false;
- runtime_authority = false;
- risk_authority = false;
- execution_authority = false;
- live_authority = false;
- real_capital_authority = false.

Store requirements:

- append-only;
- payload SHA-256;
- hash chain;
- generation CAS;
- writer lock;
- restart persistence;
- idempotent identical reseal;
- conflicting rewrite rejection.

## 20. Fresh scarcity population

GENC6_FRESH_SCARCITY_POPULATION is descriptive only.

It may report:

- decision epochs;
- true-scarcity epochs;
- candidate counts;
- candidate coverage;
- treatment/control divergences;
- accounts;
- Traders;
- calendar/trading days;
- requested capital;
- available capital;
- capital shortfall;
- mutually fundable candidates;
- competition intensity;
- outcome coverage;
- settlement/release coverage when available;
- blockers.

It must retain:

```text
descriptive_only = true
economic_utility_ready = false
certification_ready = false
```

until a separate economic protocol is preregistered.

## 21. OOS binder law

A later/parallel binder must require:

```text
GEN-C6 decision
-> candidate durable GEN-C4 evidence
-> GEN-C5 eligibility where applicable
-> Phase20 source decision
-> policy lineage
-> actual terminal outcome
-> actual capital settlement/release
```

If any required link is absent:

PARTIAL / INVALID.

No imputation.

No simple historical-R multiplication.

## 22. Future economic protocol

Before inspecting GEN-C6 outcomes for policy utility, freeze:

- minimum true-scarcity epochs;
- minimum candidate/outcome/settlement coverage;
- temporal folds;
- ending-capital metrics;
- DD / tail non-compensatory gates;
- capital-risk-time productivity;
- capital velocity;
- optionality;
- reserve value;
- missed opportunities;
- overallocation / underallocation;
- leverage-normalized attribution;
- stress tests.

This V1 preregistration intentionally does not choose those empirical thresholds.

## 23. Oracle boundary

Perfect-future allocation may exist only as:

`NON_CAUSAL_ORACLE_FEASIBILITY_UPPER_BOUND`

It is diagnostic only.

It is not implementable policy evidence and cannot certify GEN-C6.

## 24. Authority

GEN-C6 V1 grants:

- no merge authority;
- no VPS authority;
- no DEMO-governed execution authority;
- no LIVE authority;
- no real-capital authority;
- no Risk authority;
- no broker mutation authority.

## 25. Falsification

GEN-C6 V1 is not successful because it makes money.

Its value-add must eventually be measured on the same opportunity population:

```text
CONTROL CAPITAL POLICY
vs
ROBUST_PARETO_MARGINAL_WITH_RESERVE_V1
```

If fresh OOS/stress/replication evidence fails the frozen future economic gate,
the policy is falsified.

Do not retune this identity on the same outcomes.

A different policy requires a new policy id and new preregistration.
