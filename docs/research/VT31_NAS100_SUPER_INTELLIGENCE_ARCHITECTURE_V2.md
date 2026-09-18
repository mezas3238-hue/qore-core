# VT31_NAS100 — Super Intelligence Architecture V2

**Status:** ACTIVE RESEARCH / CONSUMED EVIDENCE ONLY / NO HOLDOUT OPENED  
**Scope:** VT31_NAS100 only  
**Methodology:** AM Silver Bullet / VT31  
**Market knowledge source:** CIBO Atlas + causal M1 state reconstruction

## 1. Objective

VT31_NAS100 must evolve from a static setup executor into a deterministic,
auditable NAS100 specialist capable of:

```text
OBSERVE
→ UNDERSTAND CONTEXT
→ RECOGNIZE JOURNEY / SEQUENCE
→ REASON ABOUT WHAT IS STILL VALID
→ WAIT / EXECUTE / ABSTAIN
→ CHOOSE STRUCTURAL INVALIDATION
→ CHOOSE FEASIBLE DESTINATION
→ MANAGE WITHOUT DESTROYING THE THESIS
```

"Human-like" does not mean arbitrary or non-reproducible.  Given the same
information available at the same timestamp, the specialist must make the same
decision and explain it.

## 2. Three-memory cognitive architecture

VT31_NAS100 carries three explicitly separated memories.

### A. Long-Term Semantic Memory

Persistent, immutable-at-runtime NAS100 knowledge distilled from consumed CIBO
Atlas evidence:

- sequence / departure timing priors;
- liquidity and structure behavior;
- stop / premature-management lessons;
- structural destinations and conditional extension behavior.

This memory contains no historical date-to-outcome map and performs no runtime
CIBO lookup.

### B. Episodic / Research Memory

Persistent development memory distilled from the VT31 laboratory:

- supported mechanisms;
- rejected / falsified hypotheses;
- failure lessons;
- consumed-evidence governance;
- unresolved warnings that must block premature freeze.

This is the specialist's memory of what the research program already learned,
including what must not be tried again as if it were new evidence.

### C. Working Memory

Ephemeral causal state rebuilt at every decision from market information known
at that timestamp:

- decision time;
- latest observed structure/liquidity event;
- event age / sequence freshness;
- current path compression;
- reference volatility state;
- current thesis-relevant state.

Working Memory is never populated from future bars, terminal PnL, or historical
date-level outcomes.

### Cognitive flow

```text
LONG-TERM SEMANTIC MEMORY
        +
EPISODIC / RESEARCH MEMORY
        +
WORKING MEMORY (NOW)
        ↓
REASONING ENGINE
        ↓
THESIS
SUPPORT
CONTRADICTIONS
UNCERTAINTY
        ↓
EXECUTE / WAIT / ABSTAIN
        ↓
STOP / TARGET / MANAGEMENT
```

Every reasoning decision records the fingerprints of all three memory layers
(the working-memory fingerprint is per decision) plus the composite cognitive
memory fingerprint.

The architecture is deliberately **internal**:

```text
external CIBO runtime dependency = FALSE
date-level historical lookup     = FALSE
future-bar lookup                = FALSE
runtime long-term retraining     = FALSE
```

CIBO remains the research teacher. VT31 receives a new long-term/episodic
memory version only through an explicit research, revalidation and fingerprint
change cycle.

## 3. Immutable CIBO Intelligence Bridge

Workflow:

```text
QORE VT31 NAS100 CIBO Intelligence Bridge V1
run: 35288950361
SHA: 279335bf61b131d3b028e41bc6357ece418f696f
status: SUCCESS
```

Artifacts:

```text
R8: 10525486699
    sha256:a9b5693095b15f6bd9067d935c1472081b1a61e56ba2d5d58514d645a5487b99

R6: 10525421953
    sha256:6bc95bc5f6a836c373b33d7ab6dba05f2b6c5caf89e89fdb08351529a33b0aa0

R5: 10525736274
    sha256:26716fb1e2546e0176bd12170a13d4a5ea06bb1f44f1d30ef4028040af020fe5
```

The causal firewall asserts:

```text
historical_knowledge_is_aggregate_only = TRUE
runtime_date_level_outcome_lookup = FALSE
runtime_future_structure_touch_lookup = FALSE
runtime_future_peer_breach_lookup = FALSE
runtime_future_peer_confirmation_lookup = FALSE
```

Runtime-prohibited fields include:

```text
day_regime
departure_pivot_at
last_structure_before_departure
opposite_boundary_at
opposite_boundary_hit_by_16
post_boundary_extension_ref
post_boundary_ladder
post_objective_farthest_at
terminal_family
terminal_r
terminal_status
trader_stopped_before_eventual_source_objective
```

## 4. CIBO historical knowledge that matters to the reasoning architecture

Across 547 completed NAS100 reversal episodes:

```text
last structure before final departure:

local-liquidity-sweep      431
reference-liquidity-sweep   79
FVG                         19
Breaker                     13
Order Block                  4
none                         1
```

Liquidity events therefore account for approximately 93.2% of the final
observed pre-departure structures.

More importantly, the timing from the **last structure touch** to final
departure is temporally similar across the three consumed partitions:

```text
R8: P25 1m / P50 8m / P75 14m
R6: P25 1m / P50 6m / P75 12m
R5: P25 1m / P50 5m / P75 11m
```

This is consistent with the independent Market State V2 finding that sequence
freshness matters.  It does not create a mechanical "14-minute rule".  It
supports representing freshness as a continuously updated state.

Once final departure occurs, travel to the opposite source boundary is much
faster:

```text
R8: P25 3m / P50 5m / P75 8m
R6: P25 4m / P50 5m / P75 8m
R5: P25 3m / P50 5m / P75 8m
```

The reasoning engine must therefore distinguish the long **formation /
reaction journey** from the often fast **actual departure / delivery phase**.

## 5. Development observations from causal CIBO runtime state

These are diagnostics, **not selected rules**.

### Last observed CIBO event = reference-liquidity-sweep

Net mean R under the existing baseline economics:

```text
R8: +0.479R
R6: +0.334R
R5: +0.595R
```

This is directionally positive across all three consumed folds.

### Cross-index state: both SP500 and US30 already breached the same expected side

```text
R8: +0.151R
R6: +0.632R
R5: +0.452R
```

Again directionally positive across all three consumed folds.

### Cross-index state: both peers already breached the opposite side

```text
R8: -0.717R
R6: -0.207R
R5: -0.418R
```

Directionally negative across all three consumed folds.

These observations justify adding **intermarket state** and **latest causal
liquidity event** to the trader's understanding.  They do not justify a binary
filter without block-level stability and mechanism validation.

## 6. Sequence freshness already demonstrated

Market State V2 predeclared the reclaim-latency buckets before their economics
were read.

The 8–14 minute reclaim-latency state was negative in all three consumed folds
and negative in 9/10 eligible half-year blocks in the first stability study.

The isolated V2A abstention test improved mean R, PF and drawdown in R8/R6/R5,
but worsened R5 losing streak.  Therefore:

```text
SEQUENCE_FRESHNESS_MECHANISM = SUPPORTED
STATIC_STALE_FILTER = NOT FREEZE READY
```

A subsequent WAIT → renewed local structure → fresh FVG experiment succeeded in
R8/R6 but failed severely in R5, proving that sequence renewal itself also
requires higher market context.

## 7. Market Context V3

The corrected Context V3 now uses:

- last prior admitted NY market session;
- previous-day direction / body strength / range;
- 08:00–09:00 premarket state;
- frozen 09:00–10:00 reference state;
- 09:30–10:00 cash-open state;
- rolling prior reference-width volatility;
- current-day path only through decision_at;
- position relative to previous-day range.

Corrected run:

```text
QORE VT31 NAS100 Market Context Lab V3
run: 35288495678
SHA: 31a3da4b65536f54f60148ccf9067803b69f0d66
status: SUCCESS
```

Artifacts:

```text
R8: 10524987758
R6: 10525247580
R5: 10525022828
```

No single higher-context categorical variable has yet demonstrated enough
stability to become a policy.  Context must remain multidimensional.

## 8. Cognitive state required for the specialist

The eventual reasoning snapshot should contain, at minimum:

### MARKET / REGIME STATE

```text
prior-day structure
premarket structure
reference behavior
cash-open behavior
trend / rotation / expansion / compression proxies
relative volatility
position inside larger ranges
```

### LIQUIDITY / SEQUENCE STATE

```text
first raid
raid side / depth
double-sided behavior
reclaim state
age of reclaim
latest local/reference liquidity event
latest PD-array
displacement state
time since meaningful structural event
sequence freshness
sequence renewal / invalidation
```

### INTERMARKET STATE

```text
SP500 breach observed?
US30 breach observed?
same-side / opposite-side / divergent state
peer source confirmation observed?
lead / lag only from already-observed events
```

### ENTRY STATE

```text
Silver Bullet thesis exists?
entry evidence exists?
entry evidence fresh?
wait for additional evidence?
old entry invalid?
new causal entry family available?
```

### STOP / INVALIDATION STATE

```text
source swing
raid extreme
latest causal structural extreme
reference geometry
volatility
MAE priors
distance relative to reference
whether stop actually invalidates the thesis
```

### TARGET / DESTINATION STATE

```text
local liquidity destination
opposite 09 boundary
distance in points
distance in reference units
distance in R
historical travel feasibility
remaining lifecycle time
volatility / expansion capacity
partial objective
boundary
possible extension / runner
```

### MANAGEMENT STATE

```text
thesis still valid?
new structural information?
adverse excursion
favorable excursion
destination reached?
extension justified?
hold / realize / trail / exit
```

## 9. Decision model

The eventual trader should not behave as:

```python
if filter_good:
    trade()
```

The intended model is stateful:

```text
OBSERVE
→ UPDATE MARKET MODEL
→ UPDATE JOURNEY / SEQUENCE
→ CONSULT HISTORICAL KNOWLEDGE
→ TEST CURRENT THESIS
→ TEST ENTRY FRESHNESS
→ TEST INVALIDATION GEOMETRY
→ TEST DESTINATION FEASIBILITY
→ EXECUTE / WAIT / ABSTAIN
→ CONTINUE REASONING AFTER ENTRY
```

The action may change only when new causal evidence changes the state.

## 10. Intelligence is not an unconstrained black box

The production concept must remain:

```text
causal
deterministic
auditable
reproducible
explainable
```

A language model or opaque discretionary component must not be allowed to
invent an entry, stop or target in production.  Human-like behavior is achieved
through richer observation, memory, state transitions, causal hypotheses and
explicit reasoning traces.

## 11. Current status

```text
CIBO historical memory bridge      ✅
CIBO causal runtime observation    ✅
Market State V2                    ✅
Sequence freshness mechanism       ✅ supported
Market Context V3 corrected        ✅
Cross-index causal perception      ✅
Human-like state architecture      ✅ defined

final entry intelligence           ❌ not frozen
stop intelligence                  ❌ not solved
target intelligence                ❌ not solved
management intelligence            ❌ not solved
candidate freeze                   ❌
fresh holdout                      ❌ unopened
live authorization                 ❌
production authorization           ❌
```

The next research stage must combine these causal dimensions into one
**Market Understanding Snapshot** and test whether it explains the temporal
regime changes without collapsing into post-hoc filters.  Only after that
should entry, stop and target policies be frozen.
