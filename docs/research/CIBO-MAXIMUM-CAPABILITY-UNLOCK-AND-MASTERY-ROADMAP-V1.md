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

Post zero-lock baseline:

- replay #105 / run 37177606960;
- HEAD 5583e9752fa57794be87146c9d9c71b0a103c2e1;
- G1 / G2 / G3 / global sensor: SUCCESS;
- function surface: 53/53 accounted;
- repair-required functions: 0;
- AUTHORITY_LOCKED / SAFETY_LOCKED / SCIENCE_LOCKED / BLOCKED: 0;
- SHADOW_ONLY / DEGRADED / UNOBSERVABLE: 0;
- CF10 universal availability: closed;
- T14 economic actuation: closed at the current prefill de-risk seam;
- T06 real CMA consumption: closed;
- Full Function Availability gate: CLOSED;
- Maximum Economic Capability gate: OPEN.

This checkpoint proves function availability and integration. It does **not** prove
that CIBO captures the maximum causal economic opportunity.

## 15. Two mastery claims must remain separate

### 15.1 Full Function Availability Mastery — CLOSED

```text
53/53 FUNCTIONALLY ACCOUNTED
+ 0 REPAIR-REQUIRED FUNCTION GAPS
+ 0 LOCKED / BLOCKED / SHADOW / DEGRADED / UNOBSERVABLE FUNCTIONS
```

### 15.2 Maximum Economic Capability Mastery — OPEN

A terminal balance, even a very strong one, is not itself a mastery proof.

```text
GOOD RETURN != MAXIMUM CAUSAL ECONOMIC INTELLIGENCE
```

Maximum Economic Capability Mastery requires:

```text
COGNITIVE ECONOMIC ACTUATION
+ POSITION LIFECYCLE INTELLIGENCE
+ CAPITAL VELOCITY / COMPOUND / PORTFOLIO OPTIMIZATION
+ ADAPTIVE LEVERAGE + PROTECTION + REDEPLOYMENT
+ FUNCTION-LEVEL ECONOMIC ATTRIBUTION
+ MAXIMUM CAPABILITY FRONTIER
+ CIBO / FRONTIER CAPTURE RATIO
+ ROBUSTNESS
```

No arbitrary target balance such as USD500, USD1,000 or USD10,000 is a valid
optimization objective. Increasing risk merely to increase terminal P/L is not
evidence of intelligence.

## 16. Zero-lock closure amendment — T06

The last observed post-T14 lock was T06 Self-Financing Expansion:
`SAFETY_LOCKED / base capital remains at risk`.

Owner ruling: base-capital exposure may constrain downstream Risk policy, but may
not disable the T06 engine. T06 must remain callable in every environment and may
propose only from proven non-base economic capacity. ORIGINAL_BASE_CAPITAL remains
forbidden as an expansion source. The Compound Portfolio must consume the real T06
plan before emitting its CMA Risk request so replay telemetry proves:
INPUT -> T06 -> OUTPUT -> CMA CONSUMER -> QORE RISK.


## 17. Owner directive — Maximum Economic Capability Program

### 17.1 Governing question

The laboratory must answer:

> Of all economic opportunity that was causally available at each instant, how
> much did CIBO capture with the lowest reasonable risk and the best preservation
> of future optionality?

The objective is **not** to make the replay print more money. Money is a
consequence of better causal decisions.

### 17.2 Mandatory Economic Efficiency scorecard

Every 3x1Y replay must measure:

1. percentage of risk and margin headroom left idle while legally deployable;
2. positive causal-expectancy opportunities not selected by CIBO, separated
   into context vetoes and allocator misses;
3. capital allocated to trades that later lost, while proving that the later
   loss was not available to the decision;
4. release-to-redeploy latency and capital occupation time;
5. Compound incremental value over Core;
6. Compound Portfolio incremental value over Compound;
7. real 0x/1x/2x/3x/4x leverage distribution plus causal reason;
8. stop-risk and margin released by T14 before settlement;
9. marginal value of breakeven, trailing, profit-lock, partial realization and
   extended target;
10. economic attribution across CF01-CF19, T01-T20 and GEN-C1-GEN-C14, with
    shared-block attribution explicitly distinguished from unique attribution;
11. distance between actual CIBO and the Maximum Capability Frontier.

### 17.3 Maximum Capability Frontier V1

The new frontier is a separate non-certifying research lane. It does not replace
the validated Core replay.

At each decision epoch it may use only:

- the frozen causal expectation known at time t;
- provider-normalized risk, margin and cost geometry;
- current realized capital and currently occupied capital;
- CF01-CF19 consultation already completed at time t;
- causal context-quality disposition;
- market/regime information observed by time t;
- provider volume constraints.

It solves the discrete action surface:

```text
ADMISSION: 0 = abstain, 1 = admit
LEVERAGE: 0x / 1x / 2x / 3x / 4x
ALLOCATION: simultaneous account-level portfolio competition
OBJECTIVE: expected net economic value per capital-minute
CONSTRAINTS: risk + margin + provider + cognitive capital-intensity ceiling
```

Future outcome, later bars, realized P/L and exit reason are forbidden from this
choice.

Only **after** the decision has been frozen may the evaluator use subsequent
market path to score the decision.

### 17.4 Cognitive Economic Actuation V1

The frontier must consume the complete CF01-CF19 orchestration. The first
separable capital-control seam binds:

- CF02 Market Intelligence Mesh;
- CF06 Portfolio Intelligence;
- CF07 Economic Intelligence;
- CF10 Quantitative Intelligence;
- CF12 Risk-Aware Recommendation.

These functions jointly create a causal capital-intensity ceiling from regime,
provider condition, opportunity competition and current risk/margin/drawdown
utilization. QORE Risk remains sovereign.

The laboratory must run cognition ON versus cognition OFF and report the economic
and drawdown delta. Functions without a currently separable numeric capital
control must be reported honestly as `NO_SEPARABLE_DIRECT_CAPITAL_CONTROL_YET`,
not assigned invented value.

### 17.5 Position Lifecycle Intelligence V1

The frontier must consume the same frozen Market Atlas M5 evidence used by the
replay, extended to NAS100 so the complete six-symbol Trader surface is covered.

Rules:

- only fully closed post-entry M5 bars are eligible;
- the partial bar containing entry is excluded;
- existing stop is evaluated before a new favorable trigger when both occur in
  the same unresolved M5 bar;
- no structural stop may be widened;
- breakeven is provider-cost aware;
- trailing is monotonic;
- all actions are chronological.

V1 action set:

```text
MOVE_TO_BREAKEVEN
PROFIT_LOCK
TRAIL_STOP
PARTIAL_REALIZATION
TARGET_PARTIAL_AND_EXTEND
TARGET_EXIT
PROTECTED_STOP
HORIZON_MARK_TO_MARKET
```

The laboratory must run leave-one-feature-out ablations for:

- breakeven;
- trailing;
- profit-lock;
- partial realization;
- extended target.

The result must quantify value and risk release rather than merely count calls.

### 17.6 Capital Velocity / Compound / Portfolio optimization

The Maximum Capability lane must maintain one chronological account state.

Realized partial profits may become available only after their causal realization
time. Risk and margin released by protection/reduction may become reusable only
after the corresponding lifecycle event.

Required ablations:

- Compound ON vs OFF;
- portfolio competition ON vs greedy/noncompetitive allocation;
- adaptive leverage vs fixed 1x;
- position lifecycle ON vs OFF;
- cognition ON vs OFF.

This makes it possible to identify whether CIBO is losing value because of poor
selection, slow capital recycling, excessive conservatism, poor leverage,
position management, or low-quality opportunity supply.

### 17.7 Capture ratio

For every group report:

```text
actual_profit = actual_cibo_ending - 60
frontier_profit = causal_frontier_ending - 60
capture_ratio = actual_profit / frontier_profit
frontier_gap = causal_frontier_ending - actual_cibo_ending
```

Interpretation must be causal:

- a large positive frontier gap means CIBO is leaving economically available
  capacity unused;
- a small gap means the current CIBO is already efficient relative to the causal
  opportunity set;
- if actual CIBO exceeds the frontier, the frontier policy is too conservative
  or incomplete and must be improved rather than declaring impossible
  superiority.

### 17.8 Four engineering blocks remain OPEN until measured jointly

1. **Cognitive Economic Actuation**
2. **Position Lifecycle Intelligence**
3. **Capital Velocity / Compound / Portfolio Optimization**
4. **Adaptive Leverage + Protection / Redeployment**

Maximum Economic Capability may not be declared until the four are exercised
jointly in the same chronology and their ablations are visible.

### 17.9 Research integrity

The frontier is explicitly:

- NON_CERTIFYING;
- reused/burned-holdout research;
- outcome-blind at decision time;
- Trader-logic immutable;
- provider-normalized;
- QORE-Risk respecting;
- broker-mutation free;
- not authority for LIVE/Production execution by itself.

A GREEN workflow is only transport evidence. The economic report and frontier gap
are the actual research output.
