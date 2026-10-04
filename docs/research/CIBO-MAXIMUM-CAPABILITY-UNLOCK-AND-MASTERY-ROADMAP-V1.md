# CIBO MAXIMUM CAPABILITY UNLOCK + MASTERY ROADMAP V1

**Status:** ACTIVE / OWNER-AUTHORIZED / UNIVERSAL FUNCTION AVAILABILITY / UNMERGED  
**Effective date:** 04-OCT-2026  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Current research lane:** `agent/cibo-post-repair-3x1y-validation-001`

## 0. Purpose

This roadmap converts the current CIBO repair program from an ad-hoc chat sequence
into a durable repository-governed program.

The immediate objective is not certification and not a headline P/L target.

The immediate objective is:

```text
ALL CIBO FUNCTIONS FUNCTIONALLY EXERCISED
+ ALL CAUSALLY APPLICABLE FUNCTIONS CONSUMED
+ ALL ECONOMICALLY RELEVANT FUNCTIONS ABLE TO ACT
+ ZERO UNEXPLAINED SHADOW / AUTHORITY / INTEGRATION LOCKS
```

Only after the full-function mastery gate is closed may the program move to
maximum-capability economic research.

## 1. Owner universal-function authorization

The Owner establishes **universal availability** as a CIBO architectural law.
A CIBO function must not exist in separate holdout/research/DEMO/LIVE
implementations and must not become unavailable merely because the caller is in a
different environment.

The same native function contract must be callable from:

- historical holdout / replay;
- TEST and validation;
- DEMO;
- LIVE;
- Production;
- any future provider/account environment.

Availability does **not** mean that a function owns order, Risk, capital-transfer,
or broker authority. Those are separate downstream authorities. The function must
still execute, preserve causal provenance and expose its output; the consumer then
applies the authority appropriate to its environment.

```text
FUNCTION AVAILABILITY != EXECUTION AUTHORITY
FUNCTION AVAILABILITY != RISK AUTHORITY
FUNCTION AVAILABILITY != BROKER MUTATION
EVIDENCE QUALITY != ENGINE AVAILABILITY
INSUFFICIENT EVIDENCE -> EXPLICIT OUTPUT / ABSTENTION / QUALITY FLAG
INSUFFICIENT EVIDENCE != HIDDEN OR DISABLED FUNCTION
```

Trader Lab remains a validation/certification consumer where applicable, but it is
not a runtime availability switch for CIBO functions. No function may depend on a
Trader Lab PASS merely to run and expose its deterministic output.

Causal integrity remains mandatory: no current/future outcome may enter a
predecision function, no fabricated market/provider evidence is allowed, and no
Trader methodology is mutated to improve replay results.

## 2. Absolute first priority — Full Function Mastery Gate

CIBO does not advance to maximum-capability optimization until the function
surface is closed.

Required surface:

- CF01-CF19;
- CE2I T01-T20;
- GEN-C1-GEN-C14.

Mandatory telemetry for every causally applicable call:

```text
INPUT
-> NATIVE ENGINE CALLED
-> OUTPUT
-> DOWNSTREAM CONSUMER
-> CONSUMER ACTION
-> DECISION / NO-CHANGE DISPOSITION
-> ECONOMIC EFFECT OR JUSTIFIED NO-CHANGE
```

Mandatory distinction:

- ACTUATING;
- USED_NO_CHANGE;
- ADVISORY_USED;
- JUSTIFIED_NOT_APPLICABLE;
- SAFETY_LOCKED;
- DATA_BLOCKED;
- AUTHORITY_LOCKED;
- SCIENCE_LOCKED;
- SHADOW_ONLY;
- UNOBSERVABLE.

Exit gate:

```text
function_count = 53
repair_required_count = 0
unexplained_shadow_count = 0
unexplained_authority_lock_count = 0
safety_locked_count = 0
science_locked_count = 0
blocked_count = 0
unobservable_count = 0
```

A contextual no-change is valid only when the native engine was actually called,
its input/output is observable, and a downstream consumer received the result.
A zero-call `SAFETY_LOCKED` state is not Full Function Mastery.

A GREEN workflow alone does not satisfy this gate.

## 3. Immediate repair A — CF10 Quantitative Intelligence

Observed defect:

```text
CF10 native engine executes
but normal authoritative result requires Trader Lab PASS
=> AUTHORITY_LOCKED
```

Owner decision:

CF10 no longer depends on Trader Lab PASS for engine availability in **any**
environment.

Required implementation:

1. one universal CF10 engine path, not separate research/LIVE implementations;
2. deterministic exact Decimal output;
3. retain typed evidence and its quality/provenance in the result;
4. never upgrade INSUFFICIENT/EVIDENCE_DEPENDENT evidence merely to run CF10;
5. expose input/output/result value to telemetry;
6. keep Risk/Execution/Broker authority outside CF10;
7. allow holdout, TEST, DEMO, LIVE and Production consumers to call the same API.

Exit gate:

- CF10 native status SUCCESS in G1/G2/G3;
- zero Trader Lab dependency for CF10 execution;
- exact result visible in telemetry;
- evidence quality preserved rather than fabricated;
- downstream consumer observed;
- same native API is environment-neutral.

## 4. Immediate repair B — T14 Dynamic De-risking

Observed defect:

```text
T14 engine works
but current replay use is SHADOW_ONLY
=> it does not change position/risk lifecycle
```

Required implementation:

1. create/complete a causal research position-lifecycle seam;
2. evaluate T14 only from information available at time t;
3. allow HOLD / REDUCE / RELEASE_ALL;
4. any reduction must be step-aligned and provider-valid;
5. released stop-risk and margin must return to account headroom exactly once;
6. realized economics after a reduction must reflect the retained exposure;
7. no synthetic stop movement and no widening of structural risk;
8. QORE Risk remains sovereign;
9. every T14 action receives before/after receipts and economic attribution;
10. if required intraposition market evidence is unavailable, classify the call
    DATA_BLOCKED rather than inventing a path.

Exit gate:

- T14 is no longer SHADOW_ONLY;
- at least one valid replay population exercises actual T14 actuation when
  causal evidence warrants it;
- HOLD is accepted as healthy no-change when ceilings are already satisfied;
- release conservation passes;
- no double release;
- no outcome-aware action.

## 5. Universal-availability sweep for every remaining lock

After CF10/T14, inspect every function still classified AUTHORITY_LOCKED,
SCIENCE_LOCKED, BLOCKED or SHADOW_ONLY.

For each function:

1. determine whether the lock is authority-only, data/science, safety, temporal
   not-applicability, or actual engine defect;
2. authority-only locks must not disable engine execution in any environment;
3. data/science insufficiency must become explicit output/abstention/quality
   telemetry rather than making the native function unavailable;
4. Risk/execution safety remains a separate downstream authority boundary;
5. temporally post-outcome functions must be exercised in their correct
   post-settlement phase, not forced into predecision;
6. no function is marked MASTERED merely because it was called.

## 6. Phase after 53/53 — Cognitive Economic Actuation

Goal:

convert successful CF outputs from advisory presence into economically useful
CIBO CMA inputs while preserving authority separation.

Target chain:

```text
CF OUTPUT
-> CIBO SYNTHESIS
-> CMA CAPITAL DECISION
-> QORE RISK
-> APPLIED ACTION
-> ECONOMIC ATTRIBUTION
```

Required ablation:

- cognition OFF;
- each functional family independently;
- complete cognition ON;
- same causal input and same replay chronology.

## 7. Position Lifecycle Intelligence

Required action vocabulary:

- KEEP;
- MOVE_TO_BREAKEVEN;
- TRAIL_STOP;
- TIGHTEN_STOP;
- REDUCE_EXPOSURE;
- RELEASE_ALL;
- PROTECT_PROFIT;
- PARTIAL_REALIZATION;
- EXTEND_TARGET;
- LET_RUN;
- EXIT.

Rules:

- causal closed-bar evidence only;
- breakeven is provider-cost aware;
- trailing is monotonic;
- no structural stop loosening;
- conservative ordering when stop/target cross in the same unresolved bar;
- M1 evidence preferred when needed to resolve path ambiguity;
- every action has proposed / authorized / applied receipts.

## 8. Capital Velocity / Compound / Compound Portfolio mastery

Measure and repair:

- deployable realized profit utilization;
- protected-capacity utilization;
- capital idle time;
- release-to-redeploy latency;
- rejected positive causal opportunities;
- Compound incremental value over Core;
- Compound Portfolio incremental value over Compound;
- cross-Trader opportunity competition;
- concentration;
- reserve efficiency;
- optionality preservation.

A higher multiplier is not evidence of intelligence.

## 9. Adaptive leverage mastery

Replace static multiplier semantics with a causal per-opportunity/per-epoch choice
from the governed discrete research set:

```text
0 = abstain/reject
1x
2x
3x
4x
```

Leverage must be a consequence of:

- causal expected utility;
- risk/margin headroom;
- provider cost;
- regime;
- uncertainty;
- concentration;
- drawdown;
- protected capital;
- capital velocity;
- opportunity competition.

No post-hoc P/L scaling.

## 10. Maximum Capability Frontier

After functional mastery, build a causal frontier that answers:

```text
HOW MUCH OF THE CAUSALLY AVAILABLE ECONOMIC OPPORTUNITY
DID CIBO CAPTURE?
```

The frontier may optimize only with information available at each historical
decision time. It may not use later outcomes to choose the current action.

Required metrics:

- CIBO realized capital;
- causal frontier realized capital;
- CIBO / frontier capture ratio;
- unused capital opportunity;
- avoidable capital occupation;
- release/redeploy latency;
- value of cognition;
- value of T01-T20;
- value of GEN-C1-GEN-C14;
- value of position lifecycle;
- value of Compound;
- value of Compound Portfolio;
- value of adaptive leverage;
- incremental P/L;
- incremental DD;
- risk-adjusted marginal value.

## 11. Trader rescue exam

The seven Traders remain frozen opportunity producers.

CIBO must demonstrate that its universal capital intelligence can transform bad
or regime-sensitive Trader economics without changing Trader methodology.

Per group and same CIBO configuration:

- 7/7 participate;
- 7/7 P/L > 0;
- 7/7 PF > 1;
- 7/7 expectancy > 0.

Trader identity is an evaluation dimension, never a decision predicate.

## 12. Robustness gate

Required after economic repair:

- chronological blocks 5/6 positive;
- WFO5 all tests positive;
- WFO6 all tests positive;
- MC 5,000 median > 0;
- MC p05 > 0;
- provider cost x2 > 0;
- slippage +100% > 0;
- remove best 1/2/3 > 0;
- protected capital breaches = 0.

## 13. Research iteration law

Every repair cycle is:

```text
READ REPLAY
-> IDENTIFY ROOT CAUSE
-> REPAIR ONE CAUSAL MECHANISM
-> TRACE INPUT/OUTPUT/CONSUMER/EFFECT
-> RUN SAME 3x1Y
-> COMPARE AGAINST LAST GREEN BASELINE
-> KEEP / REVERT / REFINE
```

No repair closes because tests are GREEN.

It closes only when its intended functional and economic behavior is observed.

## 14. Current checkpoint

Baseline before this roadmap:

- full-stack runtime traversal: complete;
- utilization accounting: approximately 96.23%;
- current repair queue: CF10 + T14;
- G1: 7/7 positive;
- G2: residual R43 GBPUSD + VT31 NAS100 failure;
- G3: residual R34 XAUUSD + R38 EURUSD + R42 AUDJPY failure;
- cross-holdout full-pass count: 0;
- status: CONTINUE_SEARCH.

This checkpoint is adaptive/burned research evidence only and is not Fresh OOS
or certification evidence.

## 15. Final mastery criterion

CIBO may be called functionally mastered only when:

```text
53/53 FUNCTIONALLY ACCOUNTED
+ 0 REPAIR-REQUIRED FUNCTION GAPS
+ ALL CAUSALLY APPLICABLE ENGINES EXECUTED
+ ALL ECONOMICALLY RELEVANT OUTPUTS CONSUMED
+ POSITION LIFECYCLE ACTIVE
+ COMPOUND / PORTFOLIO / LEVERAGE CAUSALLY ACTIVE
+ ROBUSTNESS PASSES
+ 7/7 TRADERS POSITIVE ACROSS THE REQUIRED HOLDOUTS
+ MAXIMUM-CAPABILITY FRONTIER GAP EXPLAINED
```

This roadmap grants no automatic certification, merge, Risk, execution or broker
authority. It establishes that the same CIBO function implementations are
available to holdout, TEST, DEMO, LIVE and Production consumers; those consumers
remain responsible for their own authority gates.

## 16. Zero-lock closure amendment — T06

The last observed post-T14 lock was T06 Self-Financing Expansion:
`SAFETY_LOCKED / base capital remains at risk`.

Owner ruling: base-capital exposure may constrain downstream Risk policy, but may
not disable the T06 engine. T06 must remain callable in every environment and may
propose only from proven non-base economic capacity. ORIGINAL_BASE_CAPITAL remains
forbidden as an expansion source. The Compound Portfolio must consume the real T06
plan before emitting its CMA Risk request so replay telemetry proves:
INPUT -> T06 -> OUTPUT -> CMA CONSUMER -> QORE RISK.
