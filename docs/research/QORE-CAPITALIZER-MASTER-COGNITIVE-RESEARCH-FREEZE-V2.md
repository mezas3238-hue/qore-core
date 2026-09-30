# QORE CAPITALIZER — MASTER COGNITIVE & RESEARCH CHAIN FREEZE V2

**Identity:** `QORE_CAPITALIZER_COGNITIVE_SCALPER_V1`  
**Owner approval:** 2026-09-20  
**Status:** COGNITIVE_TARGET_FROZEN / IMPLEMENTATION_IN_PROGRESS / NOT_CERTIFIED  
**Branch:** `agent/qore-capitalizer-cognitive-v1-001`

## 1. Owner intent

Capitalizer is the most demanding cognitive trader in QORE Core because it must reason across
three intraday sessions and nine markets while remaining a same-session scalper.

It must not behave as a signal robot. Every action must have an auditable causal "why":
what the market was doing, what changed, what evidence existed at decision time, what contradicted
the thesis, what destination was available, why one market deserved attention/capital over
another, and why HOLD / PROTECT / EXIT / WAIT / ABSTAIN was chosen.

"Human-like" in this contract means causal, contextual, memory-aware, uncertainty-aware,
counterfactual and auditable reasoning. It does not mean unrestricted self-modification,
unbounded discretion, hidden rules, or retrospective outcome knowledge.

## 2. Frozen research universe

### ASIA
- USDJPY
- AUDJPY
- AUDUSD
- GBPJPY

### LONDON
- EURUSD
- GBPUSD

### NEW YORK
- XAUUSD
- USDCAD
- NAS100

All nine markets have consumed CIBO historical memory/corpora covering approximately ten years.
For Capitalizer simulation, research may duplicate/materialize immutable copies of those market
corpora. The copied data is test evidence only; Capitalizer must not mutate CIBO master memory.

## 3. Frozen session execution contract

- Maximum executions per session: **3**.
- Maximum theoretical daily executions: **9**.
- MAX3 is a ceiling, never a quota.
- Zero trades is valid.
- Positive realized PnL alone does not stop a session.
- Every position must close inside its originating session.
- A second/third trade requires a genuinely new causal opportunity.
- Revenge, unchanged-thesis retry and same-source resurrection are forbidden.
- QORE Risk remains final capital authority.

## 4. Cognitive closure comes before strategy/economic closure

The mandatory order is:

1. **Close and freeze Cognitive V2.**
2. **Close and freeze exact ICT/TTrades strategy-source grammar.**
3. **Run integrated nine-market historical simulation using immutable CIBO 10Y copies.**
4. **Study market families/regimes and causal market behavior deeply.**
5. **Close Loss/Stop Intelligence.**
6. **Close Target Intelligence.**
7. **Study BE, structural trailing stop, trailing target and Zig-Zig separately.**
8. **Close Daily Loss / funded-account survivability.**
9. **Only then freeze an economic candidate and enter costs/WFO/MC/stress/holdout/certification.**

No later stage may silently rewrite a previously frozen chain. A required change opens an
explicit new version and forces downstream revalidation.

## 5. Maximum cognitive hierarchy

```text
CAPITALIZER MASTER BRAIN
        |
GLOBAL WORLD MODEL
        |
+------------------+------------------+------------------+
|                  |                  |                  |
SESSION/JOURNEY    9 MARKET BRAINS    DATA/PERCEPTION
INTELLIGENCE                          INTEGRITY
|                  |                  |
+------------------+------------------+
        |
REGIME / MARKET-FAMILY INTELLIGENCE
        |
CROSS-MARKET CAUSAL + INDEPENDENCE GRAPH
        |
ATTENTION SYSTEM
(BACKGROUND -> WATCH -> FOCUSED -> DECISION -> POSITION)
        |
HYPOTHESIS LIFECYCLE
(OBSERVED -> FORMING -> AWAITING_CONFIRMATION -> CONFIRMED
 -> EXECUTABLE -> ACTIVE -> STRENGTHENING/STABLE/WEAKENING
 -> INVALIDATED/KILLED)
        |
OPPORTUNITY COMPETITION / SLOT ARBITRATION
        |
UNCERTAINTY + CONTRADICTION + METACOGNITION
        |
COUNTERFACTUAL / ADVERSARIAL REASONING
        |
EXECUTE / WAIT / ABSTAIN
        |
PORTFOLIO POSITION SUPERVISOR
        |
POSITION INTELLIGENCE
        |
CIBO (ADVISORY/CONTEXT)
        |
QORE RISK (FINAL CAPITAL AUTHORITY)
        |
EXECUTION
```

## 6. Cognitive components to implement and close

### 6.1 Global World Model

One causal snapshot of the complete trading day. It must know, at decision time:

- current session and phase;
- state of all nine Market Brains;
- active/focused/background markets;
- active hypotheses and killed hypotheses;
- consumed and remaining liquidity/destinations;
- currently open positions;
- factor and causal exposure;
- realized daily/session R;
- unresolved failure fingerprints;
- execution quality;
- knowledge/uncertainty state;
- available session slots;
- prior Asia -> London -> New York handoff.

The World Model must never contain future bars, later MFE/MAE, eventual outcome or any fact that
did not exist at the decision timestamp.

### 6.2 Nine Market Brains

Every market receives its own experience and behavior memory. One market may not be treated as
a generic copy of another.

Each Market Brain must learn/reason about:

- its session behavior;
- liquidity behavior;
- structural transitions;
- range/trend/compression/expansion behavior;
- volatility behavior;
- failure modes;
- good/bad hours;
- unsuitable hours;
- target behavior;
- stop behavior;
- recurrent causal states;
- interactions with the other eight markets;
- evidence quality and uncertainty.

### 6.3 Session/Journey Intelligence

Asia, London and New York are connected parts of the same day.

Later sessions receive forward-only causal handoff including:

- what liquidity was consumed;
- what remained;
- which hypotheses failed;
- which causal failure families remain unresolved;
- factor exposure;
- realized day/session result;
- dominant context;
- open questions requiring stronger evidence.

A new session does not reset the trader's memory of the day.

### 6.4 Regime / Market-Family Intelligence

Dedicated laboratories must study the market-family taxonomy instead of assuming it.

The target research program is **nine market families**. Their final names/definitions must be
earned from causal evidence, but the research must explicitly explain states such as:

- directional trend;
- balance/range;
- compression;
- expansion;
- transition;
- exhaustion;
- volatility/disorder;
- reversal;
- failure/failed expansion or equivalent causal family.

For every family the lab must answer:

- why the market entered that family;
- what preceded it;
- what evidence identifies it before the trade;
- what tends to invalidate it;
- what liquidity/destination usually matters;
- which hours/sessions are favorable/unfavorable;
- what entry behavior is compatible/incompatible;
- what stop/target behavior it tends to require.

No family may be defined by knowing the future terminal outcome.

### 6.5 Cross-Market Causal & Independence Brain

Correlation alone is insufficient.

The brain must determine whether opportunities are:

- independent causal opportunities;
- the same factor exposure under different symbols;
- leader/follower expressions;
- reinforcing;
- contradictory;
- redundant;
- mutually invalidating;
- uncertain.

Three tickets are not automatically three independent risks.

### 6.6 Attention Intelligence

The nine markets do not receive equal decision priority at every instant.

Frozen attention states:

- `BACKGROUND`
- `WATCH`
- `FOCUSED`
- `DECISION`
- `POSITION`

Attention is causal and reversible. It is not a performance ranking and cannot use future
outcomes.

### 6.7 Hypothesis Lifecycle

Every opportunity must have an explicit lifecycle:

- `OBSERVED_EVENT`
- `HYPOTHESIS_FORMING`
- `AWAITING_CONFIRMATION`
- `CONFIRMED`
- `EXECUTABLE`
- `POSITION_ACTIVE`
- `THESIS_STRENGTHENING`
- `THESIS_STABLE`
- `THESIS_WEAKENING`
- `THESIS_INVALIDATED`
- `THESIS_KILLED`

Killed hypotheses cannot be resurrected. Rearm requires a genuinely new source event,
hypothesis identity and later event generation.

### 6.8 Opportunity Competition / Slot Arbitration

MAX3 does not mean "take the first three signals".

Valid opportunities compete for capital/slots using decision-time evidence:

- methodology fidelity;
- causal clarity;
- market-family compatibility;
- destination quality;
- contradiction state;
- execution quality;
- cross-market causal independence;
- prior failure state;
- session/day context;
- knowledge state.

The arbiter may choose fewer than three opportunities.

It must not use terminal PnL, future MFE/MAE or retrospective ranking.

### 6.9 Confidence, uncertainty and metacognition

No fabricated percentages.

The brain distinguishes what it knows from what it does not know using evidence/provenance.

Required conceptual states include:

- strong/clear opportunity;
- normal valid opportunity;
- doubtful/partial opportunity;
- conflicted opportunity;
- unknown/insufficient evidence.

A strong opportunity may deserve a slot over a doubtful one, but this must never become
martingale behavior or "recover the previous loss".

### 6.10 Counterfactual / adversarial reasoning

Before EXECUTE, the brain must try to falsify its own thesis.

It must ask, deterministically:

- what observation would make this thesis wrong?
- is that contradictory evidence already present?
- is the apparent setup actually a repeated unresolved failure?
- is destination still available?
- is the move late?
- is another market showing the opposite causal story?
- is execution quality sufficient?
- is the perceived opportunity merely redundant exposure?

### 6.11 Data & Perception Integrity

Before interpreting the market, cognition verifies the evidence itself:

- quote freshness;
- missing bars;
- duplicated/out-of-order timestamps;
- stale state;
- session-clock integrity;
- spread/commission/slippage context;
- incomplete microstructure evidence;
- source provenance.

Bad evidence fails toward WAIT/ABSTAIN.

### 6.12 Daily Failure-State / Cognitive Pressure

The trader must recognize causal deterioration before a funded-account daily limit is threatened.

Cognitive pressure is not a recovery system and does not change lot size.

Required postures:

- `NORMAL`
- `CAUTIOUS`
- `HIGH_SELECTIVITY`
- `RECOVERY_OBSERVATION`
- `STOP_SESSION`
- `STOP_DAY`

Losses are grouped by causal family. Repeated failure of the same unresolved state increases
selectivity even if the numeric daily loss is still small.

The trader must never increase aggressiveness merely to recover prior losses.

### 6.13 Portfolio Position Supervisor

When multiple positions exist, management is portfolio-aware.

It must know:

- shared causal/factor exposure;
- which position is leader/follower;
- which thesis has strengthened/weakened;
- whether protection of one position changes portfolio risk;
- whether a new candidate duplicates active risk.

Position management cannot widen a stop or grant capital authority.

### 6.14 Position Intelligence expansion target

The current HOLD/PROTECT/EXIT contract is the base, not the completed intelligence.

Future dedicated chains will evaluate, separately:

- structural stop placement;
- stop-loss failure taxonomy;
- break-even;
- structural trailing stop;
- target placement;
- target extension/trailing target;
- invalidation exit;
- protected swing/structure;
- Zig-Zig applicability.

These are not to be optimized simultaneously.

### 6.15 Cognitive Audit / Explanation Ledger

Every decision must be reconstructable.

The ledger must record:

- what the trader observed;
- what it believed/considered;
- what it did not know;
- contradictions;
- causal thesis;
- adversarial findings;
- why EXECUTE/WAIT/ABSTAIN was chosen;
- why one market received a slot and another did not;
- what changed after entry;
- why HOLD/PROTECT/EXIT occurred.

This ledger is required for nine-market simulation and later certification.

## 7. Methodology fidelity — ICT + TTrades

After Cognitive V2 is closed, the next chain is the exact strategy-source contract.

The strategy must be a faithful deterministic operationalization of the approved source material,
not a generic "SMC/ICT-inspired" strategy and not a strategy rewritten from profitable backtest
cells.

Approved source family currently includes:

- ICT Asian Killzone;
- ICT Mastering High Probability Scalping;
- ICT London Killzone;
- ICT New York Killzone;
- TTrades Scalping Model;
- TTrades Failure to Manipulate, only after original-source review is completed.

Required source work:

1. retrieve/review the original approved sources;
2. extract exact entry/context/invalidity/target semantics;
3. distinguish verbatim/source-supported principles from QORE operationalization;
4. encode every operational rule with provenance;
5. test deterministic equivalence;
6. freeze the source grammar before economic optimization.

If an entry form cannot be supported by the approved authors, it cannot be presented as their
methodology.

## 8. Nine-market integrated simulation

After Cognitive + Strategy Source are frozen:

- duplicate/materialize immutable research copies of the nine CIBO 10Y market corpora;
- align them chronologically so the Capitalizer experiences the markets as one simulated day;
- preserve true Asia -> London -> New York ordering;
- present all eligible contemporaneous markets to the Master Brain;
- capture every cognitive decision and handoff;
- do not reveal future bars/outcomes to the decision engine;
- do not mutate CIBO memory;
- keep development evidence separate from later sealed holdouts.

The simulation must answer not only "did the trade win?", but:

- what did the trader see?
- what did it think the market was doing?
- why?
- which market received attention?
- what opportunity was rejected and why?
- what did the prior session teach the next?
- what causal factor linked concurrent markets?
- how did the thesis evolve after entry?
- what would have invalidated the trade?
- what actually caused losses?

## 9. Deep market understanding laboratories

Capitalizer requires dedicated labs plus reusable QORE Core labs.

The research must explain, for each of the nine markets:

- why price moved from a specific area;
- where it appears to be seeking liquidity/destination;
- why a trend exists;
- why a range exists;
- why volatility expanded/contracted;
- what preceded good days and bad days;
- good hours;
- bad hours;
- hours unsuitable for trading;
- earliest time/context in which the methodology becomes reliable;
- session transitions;
- false expansion;
- failed manipulation;
- continuation vs reversal evidence;
- interaction with structural targets;
- interaction with other portfolio markets.

"Because the backtest won" is never an acceptable causal explanation.

## 10. Economic/risk acceptance already frozen

For this scalper:

- target observed strategy drawdown: **3R–5R**;
- absolute maximum acceptable observed drawdown: **6R**;
- >6R = `REJECTED_FOR_ACCEPTANCE`;
- the solution must be structural/cognitive, not cosmetic risk scaling;
- daily loss behavior must be substantially tighter than total DD and gets its own laboratory;
- funded-account survivability is mandatory;
- PF, density, costs, stability, WFO, MC, stress, robustness and fresh holdout remain independent gates.

## 11. Chain closure law

Every major intelligence chain ends in one status:

- `FROZEN_APT`
- `REJECTED`
- `RESEARCH_OPEN`

Only `FROZEN_APT` knowledge may become an input to the next frozen chain.

A frozen chain is versioned and immutable. A later contradiction does not silently edit history;
it opens a new version and revalidates all dependent chains.

## 12. Authority

This freeze grants no execution authority.

- PR remains DRAFT / OPEN / UNMERGED.
- No merge without Owner order.
- No VPS mutation.
- No broker order path.
- No DEMO/LIVE/real-capital use.
- No certification claim.
- CIBO remains advisory/contextual.
- QORE Risk remains sovereign.
