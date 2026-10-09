# QORE CORE — VT31 MASTER CONTINUITY HANDOFF

## DUAL-SESSION CERTIFICATION · COGNITIVE SENSORS · 3Y SINGLE BASE · URGENT REPAIR

**Owner / CEO:** Sergio Meza  
**Repository:** `mezas3238-hue/qore-core`  
**Working branch:** `agent/vt31-edge-position-cert-b-001`  
**Handoff date:** 2026-10-09  
**Source HEAD before this handoff:** `e0f7294f9ad19ad0da8b3c49bd845518b02fd4f4`  
**Status:** ACTIVE CONTINUITY CONTRACT  
**VT31 CERTIFIED:** FALSE  
**Fresh Holdout:** SEALED  
**LIVE / REAL-CAPITAL / PRODUCTION AUTHORITY:** FALSE

---

# 0. OWNER DIRECTIVE — TWO VT31 OPERATING MODELS

From this handoff forward VT31 is not a single-session trader.

VT31 must be developed and certified as two explicit operating models:

1. **VT31_NY** — New York session model.
2. **VT31_LONDON** — London session model.

These are sibling models under the same VT31 strategy identity, but they are
**not allowed to share a certification result**.

Certification law:

```text
VT31_NY must pass every required certification gate independently.
VT31_LONDON must pass every required certification gate independently.
Only after both pass independently may VT31_DUAL_SESSION be integrated.
The combined NY+London system must then pass a final interaction/system gate.
```

A PASS by New York does not certify London.

A PASS by London does not certify New York.

A combined aggregate metric cannot hide a failing session.

No session may rescue the other through capital allocation, position sizing,
lower exposure, leverage, compounding, portfolio weighting, or any other
financial engineering.

At the source HEAD of this handoff, no VT31 London implementation or London
certification contract exists in the repository. A repository search found no
VT31/London model. Therefore London must be created as a real second model,
not represented as a renamed New York replay.

---

# 1. SOVEREIGN PURE-EDGE CERTIFICATION LAW

VT31 certification is PURE EDGE ONLY.

Forbidden as a means to obtain, improve, or rescue certification:

- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation;
- equity-dependent risk reduction;
- reduced monetary exposure;
- CIBO capital rescue;
- volume engineering;
- date/fold/session-result lookup;
- future bars;
- terminal-outcome oracle.

Allowed:

- methodology-native stop placement;
- methodology-native stop movement;
- breakeven;
- structural trailing;
- partials if methodologically justified;
- causal early exits;
- causal target extension;
- R-native trader logic based on fixed initial risk;
- maximum cognition using information available no later than the decision
  timestamp.

Hard observed drawdown gate:

```text
MAX OBSERVED DD <= 6R = PASS
MAX OBSERVED DD > 6R = FAIL
```

The trader must use maximum applicable intelligence. A reduced subset of
cognition is not acceptable merely because it produces prettier replay
economics.

---

# 2. CURRENT OPERATING DATA POLICY — ONE CONTIGUOUS 3Y BASE

The owner rejected the old R5/R6/R8 operating basis.

Current research and certification development uses one contiguous
three-year NAS100 base:

```text
BASE_ID = VT31_NAS100_OWNER_3Y_BASE_001
start   = 2023-10-01 inclusive
end     = 2026-10-01 exclusive
length  = 1096 calendar days
```

Canonical evidence:

```text
run            = 37569578605
head           = 8f91ee489d33c1fa0b90972270d4ac6c32fcca32
artifact_id    = 11459859004
artifact_name  = qore-vt31-nas100-owner-3y-base-v1
```

This base is now consumed development evidence. It is NOT Fresh Holdout.

For VT31_LONDON:

- first audit whether this exact immutable 3Y evidence contains complete
  causal London-session coverage;
- if it does, reuse the same evidence identity and exact 3Y dates;
- if it does not, acquire a London-complete artifact over the exact same
  frozen 3Y interval;
- never silently change the 3Y date window between NY and London.

No return to R5/R6/R8 as the current operating baseline.

---

# 3. CURRENT NEW YORK 3Y BASELINE

Current VT31_NY baseline from:

`docs/research/VT31_3Y_BASELINE_FINDINGS_001.md`

First successful single-base 3Y Trader Lab:

```text
run    = 37569578605
head   = 8f91ee489d33c1fa0b90972270d4ac6c32fcca32
status = SUCCESS
```

Density:

```text
market days          936
eligible NY sessions 769
admitted trades       55
owner target         ~450 trades / 3Y
gap                  395
target fraction      12.22%
```

Trade count by year:

```text
2023 Oct-Dec   8
2024          18
2025          17
2026 Jan-Sep  12
```

Attrition across 769 eligible NY sessions:

```text
terminal structural trades                    79
no-fill                                       29
censored-fill-bar-path                        16
source-not-executable                         57
no-source-setup                               86
intelligence-abstain                         496
intelligence-abstain-source-invalidated        6
```

After the downstream Comparator-009 admission stack:

```text
structural terminal population = 79
final admitted population      = 55
downstream removals             = 24
```

Current 3Y economics at baseline 0.05R friction:

```text
trades              55
wins                11
losses              44
total R          +25.4956512133R
mean R           +0.4635572948R
PF                   1.6326693583
max DD              21.3585957183R   FAIL
max losing streak   23
payoff                6.5306774333
Sharpe                0.5619175332   FAIL
Sortino               2.3569608716
MC positive           0.8147         FAIL
MC p95 DD            27.5956317826R FAIL
0.10R friction PF     1.5352101839
```

Current hard disposition:

PASS:
- PF >=1.50;
- expectancy >=+0.15R;
- payoff >=1.20;
- Sortino >=2;
- degraded 0.10R PF >1.

FAIL:
- density;
- observed DD <=6R;
- Sharpe >=1.50;
- MC positive >=0.90;
- MC p95 DD <=15R.

Therefore VT31_NY is NOT CERTIFIED.

---

# 4. LATEST 3Y DENSITY INVESTIGATION

The latest branch work at source HEAD
`e0f7294f9ad19ad0da8b3c49bd845518b02fd4f4` traced the exact density attrition.

Workflow:

```text
QORE VT31 NAS100 3Y Fast Density Truth V1
run      = 37600743174
head     = e0f7294f9ad19ad0da8b3c49bd845518b02fd4f4
status   = SUCCESS
artifact = 11472049775
```

A deliberately relaxed cognitive-selection study reached:

```text
selected EXECUTE days       609
structural terminal trades  348
final admitted trades       183
gap to 450                  267
```

Downstream attrition of 348 terminal structural trades:

```text
ADMISSION_BASE                         348 -> 203   removed 145
RECOVERY_FILTER                        203 -> 199   removed   4
FVG_SHORT_COMPRESSED_FRESH_FAST        199 -> 198   removed   1
BREAKER_BEARISH_COMPRESSED_BULLISH     198 -> 196   removed   2
RAPID_BREAKER_CONFLICT_UNION           196 -> 190   removed   6
BULLISH_H1_MID_CONFIRMATION_CONFLICT   190 -> 183   removed   7
```

Important conclusion:

The system has much more structural opportunity capacity than the original
55-trade baseline, but naive admission relaxation destroys the economics.

Structural-exit truth for the 183 final trades:

```text
PF            ~1.0260
mean R        ~+0.0227R
max DD        ~62.8838R
wins          31
losses        152
```

A second replay applying the existing downstream position economics to the
same density direction:

```text
workflow = QORE VT31 NAS100 3Y Relax-All-Four Economics V1
run      = 37600292603
head     = 9d76edb64e3aa8532a99bab722cfac911f71c4bb
status   = SUCCESS
artifact = 11472049508
```

Result:

```text
trades              183
wins                 25
losses              158
PF                   1.108147333
mean R              +0.077425682R
max DD              45.462716155R
Sharpe               0.200510224
Sortino               0.742392318
MC positive           0.6178
MC p95 DD            65.532168371R
0.10R PF              1.036129342
```

This candidate fails almost every certification gate and must not be promoted.

Research implication:

```text
DENSITY EXISTS
BUT CURRENT COGNITIVE/ADMISSION DISCRIMINATION CANNOT YET EXPAND DENSITY
WITHOUT IMPORTING LARGE LOSS MASS.
```

Do not solve the density problem by simply demoting all contradictions.

---

# 5. WORK COMPLETED — COGNITIVE SENSOR PROGRAM

A read-only sensor architecture was installed specifically to determine where
VT31 intelligence is missing, blocked, ignored, or failing to reach execution.

The sensor stack is observation-only. It has no authority to change entries,
stops, exits, targets, size, leverage, capital, or outcomes.

Primary telemetry/runtime files in this lineage include:

- `src/qore/infrastructure/traders/vt31_nas100_cognitive_telemetry.py`;
- `src/qore/infrastructure/traders/vt31_nas100_cognitive_plumbing.py`;
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py`;
- `src/qore/infrastructure/traders/vt31_nas100_market_context_runtime.py`;
- `scripts/vt31_nas100_cognitive_sensor_audit_v1.py`;
- `.github/workflows/vt31-cognitive-sensor-audit-v1.yml`.

The other architect is explicitly authorized to add complementary sensors,
provided the canonical telemetry and decision engine are reused and not
duplicated.

---

# 6. SENSOR TYPES INSTALLED

## 6.1 INPUT SENSOR

Purpose:

Observe exactly what the cognitive engine receives at every causal
post-entry evaluation.

Inputs covered include:

- as-of timestamp;
- session;
- weekday;
- setup family;
- confirmation state;
- prior-day state;
- H4;
- H1;
- M15;
- premarket;
- cash-open;
- prior-range location;
- range state;
- volatility state;
- current-path ratio;
- reference-width ratio;
- raid depth;
- recent path efficiency;
- overlap;
- reference reclaim state/age;
- last structure event family/age;
- trailing liquidity-event count;
- displacement;
- risk geometry;
- structural destination;
- journey stage;
- DOL states;
- extension capacity;
- exhaustion;
- cross-index context;
- current_open_r;
- `market.next_structural_target`.

It reports missing/unavailable/unwired inputs rather than silently synthesizing
them.

## 6.2 COGNITION SENSOR

Purpose:

Prove whether full cognition and maximum intelligence actually ran.

It records:

- full cognitive accounting verified;
- maximum cognition verified;
- maximum-intelligence blockers;
- cognitive domains consulted;
- support/caution state;
- destination state;
- observation-only context fields.

## 6.3 REASONING SENSOR

Purpose:

Observe the canonical reasoning output rather than a sidecar policy.

It records the current reasoning action and its causal context.

Expected surfaces include:

- EXECUTE;
- WAIT;
- ABSTAIN;

with post-entry admission-only contradictions demoted appropriately so an
already-open position is not falsely treated as a new entry.

## 6.4 OUTPUT / POSITION SENSOR

Purpose:

Observe the complete canonical PositionAction surface.

Outputs:

- HOLD;
- TRAIL;
- EXTEND;
- EXIT.

It records the exact position reason, not only a boolean such as
`trail_authorized`.

## 6.5 ACTUATION SENSOR

Purpose:

Prove that a cognitive output actually reaches execution.

It correlates:

```text
cognitive output
-> route
-> expected next valid M1 actuator
-> actual executed action
```

Possible statuses include:

- ALIGNED_NO_ACTION;
- ROUTED_AND_EXECUTED;
- ROUTED_NOT_EXECUTED;
- ROUTED_EXECUTION_UNOBSERVED;
- REQUIRED_ACTION_NOT_ROUTED;
- REQUIRED_ACTION_UNOBSERVED.

## 6.6 SENSOR-INTEGRITY SENSOR

Purpose:

Fail closed if a required action or cognitive call disappears.

It counts:

- missing sensor calls;
- required action unobserved;
- required action not routed;
- required action not executed.

## 6.7 TIMING / CAUSALITY OBSERVABILITY

The telemetry preserves the decision timestamp and requires execution only on
the next valid M1 open after a fully closed causal observation.

Same-bar lookahead is forbidden.

## 6.8 ATTRITION / DENSITY SENSORS

The 3Y program separately instruments the complete opportunity funnel:

```text
RAW / ELIGIBLE SESSION
-> SOURCE SETUP
-> SOURCE EXECUTABLE
-> COGNITIVE OBSERVATION
-> REASONING
-> FILL
-> STRUCTURAL TERMINAL
-> DOWNSTREAM ADMISSION
-> FINAL TRADE
```

Every disappearance must have a machine-readable reason.

---

# 7. LATEST VERIFIED SENSOR RESULT

Latest fully green cognitive sensor checkpoint:

```text
workflow = QORE VT31 GitHub Trader Lab Cognitive Sensors V1
run      = 37558597362
head     = 626b6a6789752233f1ec85955adc1a939fad38df
status   = SUCCESS
artifact = 11455624711
```

Aggregate sensor result:

```text
trades                                109
cognitive calls                     3,219
average calls/trade             29.53211009
maximum calls/trade                  239
minimum calls/trade                    0
missing sensor calls                   0

full accounting verified          3,219 / 3,219
maximum cognition verified        3,219 / 3,219
maximum-intelligence blockers         0

canonical PositionAction:
  HOLD                             3,192
  EXIT                                27

actuation:
  HOLD -> ALIGNED_NO_ACTION        3,192
  EXIT -> ROUTED_AND_EXECUTED         27

required action unobserved             0
required action not routed             0
required action not executed           0
```

This proves that the earlier canonical-output-to-actuator break was repaired.

It does NOT prove that every required market fact feeding cognition is
complete.

---

# 8. SENSOR-PROVEN PROBLEMS STILL OPEN

## 8.1 `market.next_structural_target` IS MISSING

Latest sensor aggregate:

```text
missing market.next_structural_target = 3,219 / 3,219 cognitive calls
```

This must be adjudicated urgently.

Either:

1. it is legitimately non-applicable on a path and must be represented
   explicitly as a meaningful state; or
2. the producer/consumer plumbing is missing.

Silent `None` on every call is not acceptable before certification.

This may be directly related to why EXTEND never appears in the observed
PositionAction distribution.

## 8.2 THREE MARKET-NATIVE FAILURE FACTS NEED PRODUCTIVE CAUSAL PRODUCERS

The runtime contract supports:

- `structure_invalidated`;
- `liquidity_failure_confirmed`;
- `regime_changed_against_thesis`.

Earlier audits showed these facts effectively dead/false in the research
sensor path even when the contract exposed them.

The next architect must install producer/consumer sensors around each fact:

```text
SOURCE FACT
-> CAUSAL TIMESTAMP
-> PRODUCER VALUE
-> PostEntryMarketFacts VALUE
-> COGNITIVE DECISION
-> PositionAction
-> ACTUATOR
```

No fact may be inferred from a known terminal loss.

## 8.3 ZERO-CALL TRADE CLASS

The sensor population contains a nonzero zero-call class.

Latest lineage identified 18 zero-call trades, dominated by Breaker
structural-invalidations.

These trades can terminate before the post-entry system gets a usable closed
M1 evaluation.

Later cognition cannot fix a trade that received no post-fill cognitive call.

The already-predeclared solution path is fill-time thesis revalidation:

`docs/research/VT31_ARCH2_CAUSAL_FILL_TIME_THESIS_REVALIDATION_GATE_001.md`

At a prospective fill T:

- use only data closed <=T;
- retain frozen setup/source/thesis identity;
- rebuild current Situation;
- require maximum applicable fill-time intelligence;
- revalidate the thesis before accepting the fill.

No arbitrary delay timer.

## 8.4 LONDON HAS NO SENSOR COVERAGE BECAUSE LONDON DOES NOT YET EXIST

The current sensor stack is reusable infrastructure, but there is no
VT31_LONDON operating model to instrument.

The London implementation must be sensor-first from day one.

---

# 9. COGNITIVE / RUNTIME WORK ALREADY COMPLETED — DO NOT REPEAT

The following substantial work has already been performed:

- separated entry admission reasoning from live-position reasoning;
- introduced `reason_position()` so admission-only contradictions do not
  automatically invalidate an already-open trade;
- built causal post-entry Situation reconstruction;
- introduced strategy-native `current_open_r` independent of sizing/capital;
- implemented full-cognition post-entry reassessment;
- implemented H3/post-1R management experiments;
- validated DOL1 touch versus DOL1 acceptance distinction;
- validated DOL2 research path and rejected DOL3;
- built multiple adverse-context exit studies;
- fixed the `NO_CONFIRMED_EXHAUSTION` substring collision;
- built causal Breaker/FVG/Order Block admission research;
- built rapid Breaker conflict studies;
- froze Comparator 008 and Comparator 009 research lineage;
- froze Sharpe/Sortino/payoff/cost-stress metric conventions;
- discovered that per-partition DD can hide a larger continuous stitched DD;
- built Comparator 010 live-context exits and falsified them as insufficient;
- tested old deep-giveback transfer and rejected it when it destroyed winners;
- studied sudden structural invalidations;
- audited rejected structural candidates for positive edge;
- built full PositionAction replay interface parity;
- wired causal 10-minute liquidity event count;
- repaired H4 causal-history/carry-forward availability;
- installed cognitive input/process/output/actuation telemetry;
- closed EXIT routing/execution observability;
- built the single 3Y evidence/replay path;
- built 3Y density capacity/selection/attrition tooling;
- proved that naive density expansion imports unacceptable loss mass.

Rejected ideas must not be recycled without genuinely new causal evidence.

---

# 10. IMPORTANT REJECTED / FALSIFIED RESEARCH

Do not repeat as generic fixes:

- broad H4/H1 directional veto;
- side-relative HTF veto;
- Comparator010 neutral-destination exit;
- Comparator010 live-context variants as sufficient closure;
- old Comparator011 deep-giveback transfer;
- blind fixed adverse-R exits;
- broad reopening of rejected structural setups;
- arbitrary fill-delay timers;
- DGR threshold mining against known losers;
- demoting all cognitive contradictions merely to gain density;
- sizing/leverage/capital rescue.

The 3Y Relax-All-Four study is direct evidence that indiscriminate admission
relaxation can increase trades while destroying edge.

---

# 11. URGENT REPAIR ORDER — NEXT ARCHITECT

Execute in this order.

## P0.1 FREEZE SESSION IDENTITIES

Create explicit identities/contracts:

```text
VT31_NY
VT31_LONDON
VT31_DUAL_SESSION
```

Do not implement London as a runtime flag inside an unnamed generic policy.

Freeze:

- session timezone;
- DST semantics;
- reference window;
- execution window;
- lifecycle cutoff;
- setup families allowed;
- structural destination definition;
- one-trade/rearm semantics;
- evidence coverage requirements.

New York must use `America/New_York` session semantics.

London must use `Europe/London` semantics and must handle UK DST causally.
Do not hardcode fixed UTC offsets.

## P0.2 REPAIR THE THREE MARKET-NATIVE FACT PRODUCERS

Implement causal producers and sensors for:

1. `structure_invalidated`;
2. `liquidity_failure_confirmed`;
3. `regime_changed_against_thesis`.

For each event report:

- producer call count;
- true/false count;
- first causal observable timestamp;
- consumer call count;
- canonical PositionAction result;
- route;
- execution acknowledgement.

## P0.3 RESOLVE `next_structural_target`

Every cognition call currently sees it missing.

Determine whether:

- destination chaining is genuinely unavailable;
- a producer is missing;
- the field should be an explicit enum/state instead of silent None.

Add sensor coverage and tests.

## P0.4 IMPLEMENT FILL-TIME THESIS REVALIDATION

Close the zero-call class without future leakage.

Run CONTROL vs FILL_REVALIDATE unchanged.

Report:

- accepted/rejected fills;
- rejected winners;
- rejected losses;
- zero-call losses affected;
- density delta;
- PF;
- expectancy;
- DD;
- Sharpe;
- Sortino;
- MC;
- winner count/R preservation.

## P0.5 RE-RUN VT31_NY SENSOR AUDIT

Required before economic replay:

- missing sensor calls = 0;
- full cognition = all required calls;
- maximum cognition = all required calls or truthful fail-closed blockers;
- all required outputs routed;
- all routed outputs execution-observed;
- market-native fact producer/consumer counts non-silent;
- next_structural_target semantics explicit;
- no date/fold/outcome authority.

## P0.6 RE-RUN VT31_NY 3Y ECONOMIC REPLAY

Immediately after repairs, replay the unchanged truthful NY system on the
single canonical 3Y base.

Use GitHub Trader Lab / prepared-ledger fast path for research iteration.

Do not return to R5/R6/R8 operating folds.

## P0.7 BUILD VT31_LONDON AS A SEPARATE MODEL

Only after the shared cognitive plumbing is truthful enough to support a second
session.

Required London work:

1. prove data coverage for the frozen 3Y interval;
2. freeze London session contract;
3. implement London reference/execution lifecycle causally;
4. reuse shared cognition modules where semantically valid;
5. prohibit NY-specific assumptions from leaking into London;
6. install the same sensors from the first replay;
7. establish London opportunity/density map;
8. establish London truthful control baseline;
9. perform pure-edge research;
10. pass every certification gate independently.

## P0.8 AFTER BOTH PASS — DUAL-SESSION INTEGRATION REPLAY

Only when NY and London independently pass.

The integrated replay must test:

- chronological combined trade stream;
- combined observed DD;
- combined PF/expectancy;
- combined Sharpe/Sortino;
- combined Monte Carlo;
- same-day correlated loss clusters;
- simultaneous/opposing thesis interaction;
- duplicate setup/thesis detection;
- session-boundary handoff;
- shared-position lifecycle conflicts;
- no duplicate trade generated by the same structural event;
- no one session masking the other.

Both session-level gates remain mandatory even if the aggregate is excellent.

---

# 12. CERTIFICATION GATES — APPLY INDEPENDENTLY TO NY AND LONDON

Unless the owner later explicitly changes a threshold, both models must pass
the same certification law.

## Density

Current owner objective:

```text
~450 real trades / 3Y
reasonable density floor currently used by 3Y adjudication: >=400
```

Because the owner requires both models to pass all gates, this density gate is
to be treated independently for NY and London unless explicitly redefined.

No signal duplication, artificial slicing, repeated counting, or causality
relaxation.

## Edge

- PF >=1.50 in required eras/partitions;
- combined/session PF >=1.70 where applicable;
- expectancy >0;
- operational expectancy target >=+0.15R/trade;
- payoff >=1.20, preferred >=1.50;
- degraded 0.10R all-in friction PF >1;
- temporal/year/era/regime robustness;
- no severe clustering.

## Observed risk

- observed maximum DD <=6R;
- continuous chronological DD <=6R;
- no partition/session reset may hide drawdown.

## Risk adjusted

Frozen convention must not be changed after seeing results.

- annualized Sharpe >=1.50;
- annualized Sortino >=2.00.

For NY, the existing eligible-session convention is frozen.

For London, freeze an equivalent London eligible-session daily-R convention
before optimization and do not retune it afterward.

## Monte Carlo

- positive terminal probability >=90%, preferred >=95%;
- p95 maximum DD <=~15R.

## Winner preservation

When comparing to a frozen control:

- winner count preservation >=80%;
- winner-R preservation >=90%.

## Cognition / architecture

- maximum applicable cognition;
- no mandatory input falsely reported green when missing;
- causal M15/H1/H4/structure/liquidity/regime/volatility inputs;
- canonical reasoning;
- canonical PositionAction;
- complete action routing/execution observability;
- research/runtime parity;
- no sidecar decision bypassing canonical cognition.

## Semantic integrity

Before freeze:

- audit categorical parsing;
- remove unsafe substring collisions;
- prove exact-state behavior for economically meaningful enums;
- audit `startswith` / token semantics in reasoning.

## No leakage

Prove:

- no future bars;
- no same-bar close used at same-bar open;
- no terminal PnL runtime authority;
- no date identity;
- no fold identity;
- no hidden holdout access;
- correct next-open execution.

---

# 13. FINAL DUAL-SESSION CERTIFICATION STATE MACHINE

The required order is:

```text
SHARED COGNITIVE PLUMBING TRUTH
        |
        +--> VT31_NY 3Y development
        |       -> sensors green
        |       -> economics green
        |       -> runtime/replay parity
        |       -> freeze
        |       -> Fresh Holdout NY exactly once
        |       -> NY CERTIFIED
        |
        +--> VT31_LONDON 3Y development
                -> sensors green
                -> economics green
                -> runtime/replay parity
                -> freeze
                -> Fresh Holdout London exactly once
                -> LONDON CERTIFIED

NY CERTIFIED + LONDON CERTIFIED
        ->
VT31_DUAL_SESSION integration replay
        ->
combined interaction/system gates
        ->
final dual-session freeze
        ->
DUAL-SESSION AUTHORITY
```

If either NY or London fails its Fresh Holdout, that model is not certified and
its holdout is consumed.

Do not let the other session compensate for it.

---

# 14. CURRENT CERTIFICATION STATUS MATRIX

```text
VT31_NY implemented                         YES
VT31_NY single 3Y baseline                 YES
VT31_NY density gate                       FAIL
VT31_NY DD <=6R                            FAIL
VT31_NY Sharpe >=1.50                      FAIL
VT31_NY MC gates                           FAIL
VT31_NY sensor architecture                YES
VT31_NY sensor execution parity            YES for observed canonical EXIT
VT31_NY missing next_structural_target     OPEN
VT31_NY market-native fact producers       OPEN
VT31_NY fill-time revalidation             OPEN
VT31_NY certified                          NO

VT31_LONDON implementation                 NOT YET BUILT
VT31_LONDON session contract               NOT YET FROZEN
VT31_LONDON sensor replay                  NOT RUN
VT31_LONDON 3Y baseline                    NOT RUN
VT31_LONDON certification gates            NOT RUN
VT31_LONDON certified                      NO

VT31_DUAL_SESSION integrated replay         NOT RUN
VT31_DUAL_SESSION certified                 NO

Fresh Holdout                              SEALED
LIVE                                       NOT AUTHORIZED
REAL CAPITAL                               NOT AUTHORIZED
PRODUCTION                                 NOT AUTHORIZED
```

---

# 15. PARALLEL ARCHITECT DIRECTIVE — SENSORS ARE AUTHORIZED

The owner explicitly authorizes the parallel architect to install additional
read-only sensors.

Rules:

1. Reuse `vt31_nas100_cognitive_telemetry.py`.
2. Do not create a second reasoning engine.
3. Do not create a second PositionAction authority.
4. Sensors may observe, count, timestamp and attribute.
5. Sensors may not modify a trade.
6. Post-outcome attribution is permitted only after terminal resolution and
   cannot become runtime authority.
7. Every new sensor must report producer -> consumer -> decision -> actuator.
8. New York and London sensors must use the same telemetry schema where
   possible, with `session_model_id` as explicit identity.
9. Do not merge NY and London counters into a single number if that hides a
   session failure.

Recommended complementary sensor targets:

- structure_invalidated producer;
- liquidity_failure_confirmed producer;
- regime_changed_against_thesis producer;
- next_structural_target producer;
- fill-time reasoning;
- session identity;
- setup source;
- reference-window provenance;
- rearm opportunity;
- session-boundary lifecycle;
- duplicate-thesis detector;
- cross-session conflict detector.

---

# 16. TRADER LAB DIRECTIVE

Research replays should use GitHub Trader Lab.

A prepared-ledger hot path exists on:

`agent/github-trader-lab-001`

Historical hot compute was measured near ~3.2 seconds for cached VT31-style
multi-fold scientific work.

For the current 3Y program:

- cache immutable 3Y evidence;
- cache expensive causal upstream reconstruction;
- keep downstream candidate evaluation fast;
- include sensors in the prepared ledger;
- calculate all certification metrics after each candidate;
- use sovereign workflows only for formal confirmation, not every hypothesis.

Build separate Trader Lab profiles for:

- VT31_NY;
- VT31_LONDON;
- VT31_DUAL_SESSION integration.

---

# 17. WORK THE NEXT ARCHITECT MUST NOT SKIP BEFORE FRESH HOLDOUT

Even after a candidate passes development economics:

1. semantic parser audit;
2. no-leakage audit;
3. exact runtime/replay parity;
4. sensor completeness;
5. action-routing/execution completeness;
6. code/config freeze;
7. memory fingerprint freeze;
8. evidence hash freeze;
9. candidate ID freeze;
10. full consumed scientific battery;
11. session-specific gate matrix;
12. dual-session interaction gate if both models are being promoted.

Only then may the appropriate Fresh Holdout be opened exactly once.

---

# 18. CURRENT SOURCE-OF-TRUTH FILES

Read these before editing:

- `docs/research/VT31_MASTER_CONTINUITY_HANDOFF_2026-10-07_3Y_SINGLE_BASE.md`;
- `docs/research/VT31_3Y_BASELINE_FINDINGS_001.md`;
- `docs/research/VT31_MASTER_CONTINUITY_HANDOFF_2026-10-06_COGNITIVE_SENSORS.md`;
- `docs/research/VT31_PARALLEL_ARCHITECT_COORDINATION_WALL_2026-10-07.md`;
- `docs/research/VT31_ARCH2_CAUSAL_FILL_TIME_THESIS_REVALIDATION_GATE_001.md`;
- `docs/research/VT31_COGNITIVE_SENSOR_PARALLEL_DIRECTIVE_001.md`;
- `scripts/vt31_nas100_cognitive_sensor_audit_v1.py`;
- `scripts/vt31_nas100_3y_replay_v1.py`;
- `scripts/vt31_nas100_3y_density_selection_map_v1.py`;
- `scripts/vt31_nas100_3y_capacity_audit_v1.py`;
- `scripts/vt31_nas100_3y_relax_all_four_economics_v1.py`;
- `src/qore/infrastructure/traders/vt31_nas100_cognitive_telemetry.py`;
- `src/qore/infrastructure/traders/vt31_nas100_cognitive_plumbing.py`;
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py`;
- `src/qore/infrastructure/traders/vt31_nas100_market_context_runtime.py`.

This handoff supersedes older continuity instructions where they conflict with
the dual-session directive.

---

# 19. IMMEDIATE RESUME ORDER

The next architect should begin with:

```text
1. Read this handoff completely.
2. Refresh branch HEAD.
3. Read the 2026-10-09 coordination wall.
4. Claim files before editing shared runtime.
5. Repair market-native fact producers.
6. Resolve next_structural_target.
7. Implement fill-time thesis revalidation.
8. Re-run VT31_NY sensors.
9. Re-run VT31_NY 3Y replay.
10. In parallel, freeze VT31_LONDON session/evidence contract.
11. Build London sensor-first baseline.
12. Certify NY and London independently.
13. Only then test dual-session integration.
```

---

# 20. SAFE RESUME PROMPT

```text
QORE CORE / VT31

Repository: mezas3238-hue/qore-core
Branch: agent/vt31-edge-position-cert-b-001

Read:
docs/research/VT31_MASTER_CONTINUITY_HANDOFF_2026-10-09_DUAL_SESSION_COGNITIVE_SENSORS.md
and:
docs/research/VT31_PARALLEL_ARCHITECT_COORDINATION_WALL_2026-10-09_DUAL_SESSION.md

Owner law:
- one contiguous 3Y operating base;
- no R5/R6/R8 operating basis;
- pure edge only;
- observed DD <=6R hard gate;
- maximum intelligence required;
- VT31 has two operating models: VT31_NY and VT31_LONDON;
- BOTH must independently pass all certification gates;
- then VT31_DUAL_SESSION must pass the combined interaction/system gates;
- sensors are read-only and authorized for both architects;
- Fresh Holdout remains sealed until pre-holdout freeze is complete.

Urgent:
repair structure_invalidated / liquidity_failure_confirmed /
regime_changed_against_thesis producers, resolve next_structural_target,
implement fill-time thesis revalidation, rerun NY sensors + 3Y replay,
and build the London session model with the same sensor and certification law.
```

**VT31 remains NOT CERTIFIED.**
