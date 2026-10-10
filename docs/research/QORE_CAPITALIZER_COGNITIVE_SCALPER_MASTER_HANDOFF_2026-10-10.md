# QORE CAPITALIZER COGNITIVE SCALPER — MASTER HANDOFF

**Date:** 2026-10-10  
**Repository:** `mezas3238-hue/qore-core`  
**PR:** #623 — `[DRAFT] QORE Capitalizer Cognitive Scalper V1`  
**Branch:** `agent/qore-capitalizer-cognitive-v1-001`  
**Canonical engineering HEAD at handoff:** `db0fec90c95bb434e1828aa862de622f3653348d`  
**PR state at handoff:** OPEN / DRAFT / UNMERGED / MERGEABLE  
**Owner mission:** preserve real trading edge while reducing drawdown and raising Profit Factor until the Scalper satisfies the full Certification Standard V2.

---

# 0. START HERE — NEXT ARCHITECT

Do **not** restart the Scalper from zero.

The active Trader is the high-frequency H1 -> M15 -> M1 Capitalizer architecture that evolved from V49 and is now being repaired through V50+ cognition, geometry, re-arm and lifecycle work.

The immediate continuation order is:

1. **Keep GitHub as the only engineering/evidence surface.**
   - Do not use VPS, even read-only.
   - Do not deploy.
   - Do not touch LIVE/production/real capital.
   - Keep PR #623 DRAFT and UNMERGED unless the Owner explicitly authorizes otherwise.

2. **Repair the five blocked corrected-core research workflows before opening any new hypothesis.**
   - V50-R: Mypy key-type collision.
   - V51: two Mypy errors.
   - V53: Ruff import-order error.
   - V54-A: Mypy key-type collision.
   - V54-B: Ruff import-order error.
   - Then rerun each from GitHub Actions.

3. **Owner rejection — V50-G 90-trade architecture is NOT a viable final candidate.**
   - Corrected-core run `36788519476` remains the authoritative **diagnostic geometry reference only**.
   - 9/9 market jobs GREEN; aggregate GREEN.
   - Cognitive Geometry: 90 trades, PF 1.53459, +26.1231R, expectancy +0.29026R, DD 9R.
   - On 2026-10-10 the Owner explicitly **REJECTED** this architecture as a candidate because density collapsed to only 90 trades.
   - Do not promote, certify, or optimize around keeping only these 90 trades.
   - Use it only to identify what the positive-edge subset is teaching us about execution geometry.
   - The next candidate must recover materially more of the original high-frequency opportunity stream while preserving positive edge, low DD and winner mass.
   - No new exact density threshold was frozen by this rejection; the design goal remains genuinely high-frequency behavior, not a tiny survivor set.

4. **Do not return to simple admission filtering.**
   - V52 falsified single-cell decision-time filtering as a viable edge-repair mechanism.
   - The active research direction is winner-preserving **transformation**:
     re-arm, execution geometry, causal stop rescue, target/lifecycle management and portfolio recompetition.

5. **Do not promote any result that destroys edge.**
   - Winner Count Preservation target/gate: >= 80%.
   - Winner-R Preservation target/gate: >= 90%.
   - A higher PF obtained by deleting most winners is a rejection, not a repair.

6. **After corrected-core V50-R/V51/V53/V54 close, freeze one candidate and only then run the complete certification battery.**

---

# 1. GOVERNANCE AND OWNER DIRECTIVES

## 1.1 GitHub-only rule

Owner directive is explicit:

> All Scalper research, engineering, tests, workflows, evidence and documentation must be performed in GitHub.

Authorized:
- repository code;
- branch `agent/qore-capitalizer-cognitive-v1-001`;
- PR #623;
- GitHub Actions;
- GitHub logs;
- GitHub retained artifacts;
- PR comments;
- repository research documents.

Not authorized during this research phase:
- VPS filesystem;
- VPS terminal;
- VPS services;
- VPS runtime;
- VPS deployment;
- VPS read-only diagnostics.

Recorded in PR comment: **5920623212**.

## 1.2 No deployment authority

Nothing in this branch grants:
- LIVE authority;
- production authority;
- real-capital authority;
- sizing authority;
- broker execution authority;
- merge authority.

The Trader cognition is advisory and QORE Risk remains sovereign over capital.

## 1.3 Historical-data override

Owner later overrode the earlier “preserve all holdouts sealed” approach.

Current law:
- any historical period may be used for diagnosis, repair and falsification;
- once a historical period influences methodology, it becomes **consumed research evidence**;
- consumed historical data may never be relabelled as final fresh certification evidence;
- final certification still requires a genuinely independent governed source or a prospective frozen evaluation period after candidate freeze.

The certification documentation was amended accordingly.

---

# 3. AUTHOR / SOURCE PROVENANCE AND FIDELITY AUDIT

This section is mandatory continuity context. The next architect must verify the Trader against the author's own material before claiming source fidelity.

## 2.1 What is the author-source of the Scalper?

The direct published source for the **TTrades Scalping Model** used in the QORE reconstruction is the first-party TTrades publication:

**TTrades — “TTrades Scalping Model – Simple Day Trading Strategy”**  
Publication date shown by TTrades: 2026-02-07  
Primary first-party URL:  
https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/

The public first-party site attributes the article/model to **TTrades**. The repository currently has no independently verified personal/legal name behind the TTrades public author identity. Therefore:

- record the author/publisher as **TTrades**;
- do not invent or infer a personal name;
- treat first-party TTrades pages/videos/PDFs as primary material for the TTrades Fractal/Scalping Model.

The first-party TTrades model states the top-down structure as:

- Daily = broader directional context;
- H1 = scalping bias;
- M15 = swing structure;
- M1 = execution.

It further states that M1 is where the trade is executed, not where the core decision should be invented, and describes M1 continuation behavior using concepts such as FVG interaction, CISD and protected-swing formation.

This first-party page is the main author-source against which the generic QORE Scalper route must be audited.

## 2.2 TTrades first-party source pack

The following first-party sources are part of the canonical source pack.

### Generic Scalping Model

**TTrades Scalping Model – Simple Day Trading Strategy**  
https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/

Use it to verify:
- top-down timeframe roles;
- H1 bias;
- M15 swing formation;
- M1 execution role;
- protected-swing stop concept;
- higher-timeframe objective targeting;
- whether M1 techniques are examples/alternatives or universal simultaneous requirements.

### TTrades Fractal Model library

**Trading Education Center — Fractal Model**  
https://ttrades.com/trading-education-center/ttfm/

Use it as the first-party index for current Fractal Model material.

### Asia

**How to Trade Asia Using the TTrades Fractal Model**  
https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/

The source explicitly describes two primary Asia routes:

1. positional entry when a completed higher-timeframe framework/protected swing already exists; or
2. wait for 4H Candle-2 confirmation, then use the 15M fractal model.

This means a universal H1 -> M15 -> M1 route for Asia is **not automatically source-faithful** merely because it resembles the generic scalping model.

### London

**How to Trade London Using TTrades Fractal Model**  
https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/

The first-party London material describes:
- Daily bias;
- daily wick formation;
- 4H swing/wick structure;
- 15M protected-swing/CISD confirmation;
- expansion toward higher-timeframe objectives.

Therefore the current QORE universal H1 -> M15 -> M1 London route must be treated as a **QORE operating specialization requiring explicit fidelity adjudication**, not silently labelled as the author's exact London model.

### New York manipulation

**Daily Profile: Understanding the New York Manipulation**  
https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/

Use it to verify:
- session liquidity sweep/manipulation logic;
- CISD confirmation;
- expansion logic;
- whether FVG / Order Block / other entry techniques are alternatives rather than a universal AND gate.

### Failure To Manipulate / breakout continuation

**How to Trade Breakouts (Failure to Manipulate)**  
https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/

Use it to verify:
- high/low taken;
- expected reversal fails to confirm;
- continuation becomes the working hypothesis;
- higher-timeframe bias provides the reason;
- lower-timeframe structure confirms continuation/protected swing.

Do not treat Failure To Manipulate as a standalone universal entry gate unless the author's source explicitly says so.

### Additional first-party context

**The Best Timeframes for TTrades Fractal Model (Simple)**  
https://ttrades.com/the-best-timeframes-for-ttrades-fractal-model-simple/

**Why Your Continuations Fail (Order Blocks + CISD Explained)**  
https://ttrades.com/why-your-continuations-fail-order-blocks-cisd-explained/

**Best Trading Strategy for 2026 – TTFM**  
https://ttrades.com/best-trading-strategy-for-2026-ttfm/

These may be used to resolve exact route semantics, but no rule should be promoted from a title/summary alone. Bind the exact claim to the article/video/PDF passage.

## 2.3 ICT primary-source ancestry

QORE also uses ICT concepts. The primary public author identity for ICT is:

**Michael J. Huddleston — The Inner Circle Trader (ICT).**

Official ICT site:
https://theinnercircletrader.com/

The official site identifies Michael J. Huddleston as The Inner Circle Trader and as the author/teacher of ICT trading concepts.

Primary retained ICT material already referenced by the repository:

**2022 ICT Mentorship — Episode 2**  
https://www.youtube.com/watch?v=tmeCWULSTHc

Important boundary:

- ICT is primary authority for claims attributed to ICT;
- TTrades is primary authority for claims attributed to the TTrades Scalping/Fractal Model;
- do not use a TTrades explanation as proof that ICT himself required a rule;
- do not use an ICT concept as proof that TTrades makes it mandatory in every route;
- exact ICT claims still require timestamp-level provenance where QORE turns them into executable hard rules.

The repository's V48 source reconstruction explicitly states that timestamp-level binding of every current ICT field was not yet complete. That unresolved provenance work remains open.

## 2.4 Existing canonical source-reconstruction document

Before modifying source methodology, read:

`docs/research/QORE-CAPITALIZER-V48-SOURCE-RECONSTRUCTION.md`

That document established the mandatory rule classifications:

- `SOURCE_EXPLICIT`
- `SOURCE_STRONGLY_IMPLIED`
- `INTERPRETATION`
- `QORE_ENGINEERING_RULE`
- `UNRESOLVED`

Critical governance law:

> `INTERPRETATION`, `QORE_ENGINEERING_RULE` and `UNRESOLVED` must never silently become universal hard gates.

## 2.5 Current source-fidelity status of the QORE Scalper

### Generic H1 -> M15 -> M1 route

**PARTIALLY SOURCE-ALIGNED, NOT YET FULLY CERTIFIED AS SOURCE-FAITHFUL.**

Aligned with TTrades generic Scalping Model:
- H1 supplies scalping bias/context;
- M15 supplies swing structure;
- M1 supplies execution;
- M1 should not become an independent second strategy;
- protected swings define logical invalidation;
- targets should relate to higher-timeframe objectives.

Current QORE deviation:
- the TTrades generic source includes Daily as broader directional context;
- Owner/QORE identity currently forbids Daily/H4 as decision/gating layers and freezes H1 -> M15 -> M1;
- therefore this is a deliberate QORE specialization and must not be described as a verbatim copy of every author rule.

### Asia

**SOURCE-FIDELITY CONFLICT / UNRESOLVED.**

TTrades' current first-party Asia material includes:
- positional higher-timeframe route; or
- 4H -> 15M route.

Current universal QORE H1 -> M15 -> M1 Asia path is not proven to be the author's exact Asia methodology.

### London

**SOURCE-FIDELITY CONFLICT / UNRESOLVED.**

TTrades' first-party London material uses Daily -> 4H -> 15M logic.
Current universal QORE H1 -> M15 -> M1 London path is not the author's published London route.

### New York

**PARTIALLY RESOLVED / ROUTE-SPECIFIC AUDIT REQUIRED.**

TTrades New York manipulation material supports sweep -> CISD -> expansion and plural entry refinement techniques.
The next architect must determine which QORE New York route is:
- generic H1 scalping;
- New York manipulation profile;
- continuation;
- Failure To Manipulate;
- another explicitly sourced route.

Do not collapse these into one universal AND gate.

## 2.6 Mandatory author-fidelity verification protocol

Before declaring any QORE Scalper architecture “faithful to the author,” build a rule ledger with one row per executable rule.

Required columns:

| Field | Meaning |
|---|---|
| QORE rule ID | exact executable rule/module |
| Session | Asia / London / New York / generic |
| Route | exact source route |
| Timeframe | H1 / M15 / M1 / author HTF if applicable |
| QORE behavior | what the code actually requires |
| Source author | TTrades or ICT/Michael J. Huddleston |
| Primary source | exact first-party URL/video/PDF |
| Timestamp/page | exact location of claim |
| Source wording summary | short paraphrase only |
| Classification | SOURCE_EXPLICIT / STRONGLY_IMPLIED / INTERPRETATION / QORE_ENGINEERING_RULE / UNRESOLVED |
| Mandatory vs alternative | whether author requires it or presents it as one route/technique |
| Fidelity verdict | MATCH / PARTIAL / CONFLICT / UNRESOLVED |
| Action | keep / route-scope / remove-as-hard-gate / research |

No architecture may receive `SOURCE_FAITHFUL` status while mandatory rows remain CONFLICT or UNRESOLVED.

## 2.7 Source-fidelity graph required before certification

The next architect must construct:

`AUTHOR SOURCE GRAPH -> QORE RULE GRAPH -> DIFFERENTIAL`

At minimum by:
- generic Scalping route;
- Asia route(s);
- London route(s);
- New York route(s);
- FTM/continuation route;
- M1 execution family.

For each route answer:

1. What supplies bias?
2. What confirms the swing?
3. What confirms continuation/reversal?
4. What timeframe executes?
5. What are valid alternative entries?
6. What invalidates execution?
7. What invalidates thesis?
8. What is the target/draw?
9. What is mandatory?
10. What is optional/contextual?
11. Which QORE rules are engineering additions rather than author rules?

## 2.8 Certification implication

Source fidelity and statistical certification are separate gates.

A model can be:
- statistically strong but source-unfaithful;
- source-faithful but statistically weak;
- both;
- neither.

For this Trader, both are required before describing it as a certified source-faithful Scalper.

Therefore final certification must include an explicit **Author Fidelity Audit** in addition to PF, expectancy, DD, Sharpe, Sortino, Monte Carlo, cost, winner preservation, anti-leakage and independent/prospective OOS.

---

# 3. FROZEN TRADER IDENTITY

Core contract identity:
`QORE_CAPITALIZER_COGNITIVE_SCALPER_V1`

High-frequency research identity:
`QORE_CAPITALIZER_HIGH_FREQUENCY_SCALPER_V49`

The key frozen rules are:

- decision stack is **exactly H1 -> M15 -> M1**;
- Daily is forbidden as a decision/gating layer;
- H4 is forbidden as a decision/gating layer;
- H1 is persistent context, not a one-trade ticket;
- multiple M15 setups may form under one valid H1 state;
- multiple intrastate opportunities are allowed;
- M1 contains execution triggers;
- trigger techniques are alternatives, not a universal superintersection;
- MAX3 executions per session is a ceiling, never a quota;
- theoretical maximum is 9 executions/day across three sessions;
- candidate generation/selection may not see future outcome;
- positions close in the same session;
- no runtime self-mutation;
- no capital authority.

Primary contracts:
- `capitalizer_contract.py`
- `capitalizer_high_frequency_identity_v49.py`
- `capitalizer_high_frequency_decision_graph_v49.py`
- `capitalizer_high_frequency_trader_v49.py`

---

# 4. OPERATING UNIVERSE AND SESSION MODEL

Session segmentation is DST-aware and based on America/New_York.

## ASIA
NY time: **20:00 -> 02:00**

Markets:
- USDJPY
- AUDJPY
- AUDUSD
- GBPJPY

## LONDON
NY time: **02:00 -> 08:30**

Markets:
- EURUSD
- GBPUSD

## NEW YORK
NY time: **08:30 -> 16:00**

Markets:
- XAUUSD
- USDCAD
- NAS100

Outside those broad research buckets, Capitalizer has no active session bucket.

Source:
`capitalizer_session_clock.py`

These are broad research/operating buckets, not claims that the bucket itself creates edge.

---

# 5. SCALPER OPERATIONAL MODEL — H1 -> M15 -> M1

## 4.1 H1 — persistent context state

H1 establishes persistent directional/liquidity context.

The H1 state:
- is formed from causal H1 bias events;
- may be inherited into a session if still valid;
- stays alive until causal replacement/invalidation;
- may support multiple M15 setups;
- is not consumed after the first trade.

This change was the core V49 topology correction that solved the V48 density failure.

## 4.2 M15 — setup formation

Inside the active H1 state, the engine scans for multiple distinct source-valid structural setups.

Current V49 implementation uses structural CISD/protected-swing setup observations.

Each M15 setup has:
- confirmation timestamp;
- protected swing;
- causal identity;
- a deadline at the next M15 setup or H1-state boundary.

The M15 protected swing is the **thesis invalidation**, not automatically the economic execution stop.

## 4.3 M1 — execution trigger

For a source-valid M15 setup, M1 supplies execution confirmation.

Current documented trigger families include:
- `LIQUIDITY_SWEEP_CISD`
- `FVG_RETRACE_CISD`

These are alternatives. They are not required simultaneously.

In frozen V49, each M15 setup uses the earliest valid M1 trigger before the setup boundary.

V50-R research extends this by allowing a strictly later source-valid M1 event for the **same parent H1/M15 thesis** if the first execution geometry is unsuitable and the M15 protected swing remains intact.

## 4.4 Entry

Baseline V49:
- entry timestamp = M1 trigger confirmation;
- entry price = trigger confirmation close.

V50+ research keeps source methodology intact and changes execution geometry/lifecycle only when causally justified.

## 4.5 MAX3 portfolio semantics

MAX3 is portfolio-wide per session/operating date:
- chronological eligible opportunities compete;
- first three executable candidates may consume slots;
- WAIT does not consume a slot;
- a rejected/blocked candidate can allow a later source-valid candidate to enter competition;
- no outcome-aware ranking;
- MAX3 is never a requirement to force three trades.

---

# 6. STOP AND TARGET MODEL

## 5.1 Dual invalidation

V50 separates:

**Execution invalidation**
- causal M1 pivot;
- economic stop candidate.

**Thesis invalidation**
- M15 protected swing;
- structural point beyond which the parent setup is dead.

This prevents paying M15-scale risk mechanically on every trade.

## 5.2 Critical corrected stop hierarchy

A core defect was found during the current work.

Old V50 could select:
1. a confirmed M1 pivot that had already been touched/breached before entry;
2. an M1 execution stop at or beyond the M15 thesis stop.

Both are now forbidden.

Canonical corrected rule:

> **M1 execution pivot must be causally confirmed + remain intact through the decision timestamp + remain strictly inside the M15 thesis boundary.**

Relevant commits:
- `47a1dc67e42aa7693c07fd2c01130c3c0e9868b6` — require intact execution pivot;
- `bcd50645418d981b484c2e065a59841e0b33b58d` — long/short breached-pivot regression tests;
- `68121971eed5670a5af5dfa6330ee9c8ce2fb2b0` — execution stop strictly inside M15 thesis;
- `57bc33c78cf1635f9c1d0939adf0b68e229b2ade` — long/short thesis-boundary tests;
- `86ee65961cc3239d3df7bc6455902d1feeac34b1` — bind downstream workflows to stop dependency;
- `db0fec90c95bb434e1828aa862de622f3653348d` — make stop-integrity regression an explicit downstream quality gate.

After entry:
- stop may HOLD;
- stop may IMPROVE/tighten;
- stop may **never widen**.

## 5.3 Local breathing/noise

V50 geometry compares M1 execution-stop distance with recent local M1 range.

Current development hypothesis:
- <4x recent M1 range -> too tight / inside local noise;
- 4x–8x -> candidate balanced execution breathing;
- >8x -> too wide for scalp execution.

These are **development hypotheses from consumed evidence**, not certified source rules.

## 5.4 H1 causal target ladder

V50 builds an outcome-blind ladder of:
- confirmed H1 pivots;
- ahead of entry;
- still untouched at the decision timestamp.

Candidates are ordered causally/structurally and do not use future outcome.

Current geometry hypothesis:
- T1 = first causal ladder destination that provides >=1R versus execution stop;
- a later H1 destination may be exposed as a structural runner;
- preferred runner research threshold has been >=1.5R.

Again, these are development hypotheses until independent validation.

---

# 7. COGNITIVE ARCHITECTURE — COMPONENTS AND FUNCTIONS

The Scalper cognition is not one filter. It is a layered decision-time architecture.

## 6.1 Global World Model
File: `capitalizer_global_world_model.py`

Function:
- immutable snapshot of the whole trading day;
- contains all nine Market Brains;
- current Session Brain;
- one ledger per session;
- Daily Journey;
- unresolved loss memory;
- open positions;
- derived factor exposures.

Safety:
- future state cannot enter;
- positions cannot roll across sessions;
- no capital authority.

## 6.2 Master Brain
File: `capitalizer_master_brain.py`

Function:
- synthesizes the complete global state;
- tracks current session and slots remaining;
- groups symbols by attention and knowledge state;
- exposes active hypotheses;
- unresolved failure fingerprints;
- factor exposure;
- causal warnings.

Important:
- does not rank a winner;
- does not grant capital.

## 6.3 Master Cognitive Frame
File: `capitalizer_master_cognitive_frame.py`

Function:
- combines world model, perception, regimes, session journey, cross-market graph, pressure, opportunity competition and candidate context;
- creates candidate-level metacognition, adversarial assessment and pre-strategy cognitive gate.

It is explicitly pre-strategy:
- no outcome visibility;
- no entry authority;
- no capital authority.

## 6.4 Market Brains and Session Brain
File: `capitalizer_context_brains.py`

Market Brain holds:
- symbol;
- session;
- state-family identity;
- microstructure trace;
- optional exact governed experience profile.

Session Brain holds:
- session;
- phase: PREOPEN / OPEN / ACTIVE / LATE / HANDOFF;
- prior causal session handoff where applicable.

## 6.5 Market Brain Registry
File: `capitalizer_market_brain_registry.py`

Function:
- guarantees exactly one governed Market Brain for each of the nine frozen markets;
- integrity/identity infrastructure;
- not a signal selector.

## 6.6 Perception Integrity
File: `capitalizer_perception_integrity.py`

Checks:
- quote freshness;
- bar completeness;
- timestamp ordering;
- session clock validity;
- provenance;
- microstructure completeness.

States:
- GOOD
- DEGRADED
- BAD

Hard-fails incomplete bars, broken chronology, invalid session clock or bad provenance.

## 6.7 Attention
File: `capitalizer_attention.py`

Allocates:
- BACKGROUND
- WATCH
- FOCUSED
- DECISION
- POSITION

Attention depends on:
- relevant event;
- hypothesis stage;
- knowledge state;
- open position.

It does not use future outcome.

## 6.8 Regime Intelligence
File: `capitalizer_regime_intelligence.py`

Represents evidence-bound regime hypotheses.

Resolutions:
- SUPPORTED
- UNRESOLVED
- CONFLICTED

It does not hard-code an economic rule and does not grant entry/capital authority.

## 6.9 Session Journey Intelligence
File: `capitalizer_session_journey_intelligence.py`

Makes the day continuous:

Asia -> London -> New York.

Carries forward:
- completed-session information;
- realized day R;
- consumed destinations;
- failed/killed hypotheses;
- killed source events;
- unresolved failure states;
- dominant causal factors.

It does **not** carry positions across sessions.

## 6.10 Memory / Session Ledger / Daily Journey
File: `capitalizer_memory.py`

### Loss Memory
Stores causal losing-hypothesis fingerprints and causes.

Purpose:
- recognize unresolved failure repetition;
- avoid blindly repeating the same causal failure.

### Session Ledger
Stores:
- execution count;
- killed hypotheses;
- killed source events.

Rules:
- EXECUTE consumes one session slot;
- ABSTAIN kills the current hypothesis/source identity;
- WAIT leaves it alive.

### Daily Journey
Stores:
- completed sessions;
- consumed destinations;
- failed hypotheses;
- dominant factors;
- realized day R.

## 6.11 Experience Memory
File: `capitalizer_experience_memory.py`

Immutable governed profiles keyed by:
- symbol;
- session;
- exact state-family id.

Contains:
- evidence calibration;
- behavior tags;
- failure tags.

Rules:
- learned outside live critical path;
- cannot self-train at runtime;
- cannot rewrite strategy identity.

## 6.12 Confidence / Knowledge
File: `capitalizer_confidence.py`

Knowledge states:
- KNOWN
- PARTIAL
- UNKNOWN
- CONFLICTED

Confidence is evidence/provenance-bound.
The system does **not** invent arbitrary numeric win probabilities.

## 6.13 Metacognition
File: `capitalizer_metacognition_v2.py`

Question:
> “What do I actually know at this decision timestamp?”

Readiness:
- WELL_SUPPORTED
- CONDITIONALLY_SUPPORTED
- UNRESOLVED
- CONFLICTED

Inputs:
- knowledge;
- perception;
- regime resolution;
- contradictions;
- evidence provenance;
- destination context.

No numeric-confidence fabrication and no capital authority.

## 6.14 Adversarial Reasoning
File: `capitalizer_adversarial_reasoning_v2.py`

Purpose:
- actively attempt to falsify a candidate before source strategy acts.

Hard findings can include:
- BAD perception;
- conflicted regime/metacognition;
- contradictions;
- stale event;
- known unavailable destination;
- repeat of unresolved failure without genuinely new causal evidence;
- duplicate open symbol;
- redundant/mutually invalidating cross-market exposure.

Verdicts:
- PASSED
- CHALLENGED
- FALSIFIED

It asks explicit counterfactual questions such as:
- what observation would invalidate the thesis?
- is destination still available?
- is this genuinely new causal evidence?
- is portfolio exposure causally independent?
- is evidence complete at decision time?

## 6.15 Cross-Market Causality
File: `capitalizer_cross_market_causality.py`

Decision-time graph relations:
- INDEPENDENT
- SHARED_CAUSE
- LEADER_FOLLOWER
- REINFORCING
- CONTRADICTORY
- REDUNDANT
- MUTUALLY_INVALIDATING
- UNKNOWN

Correlation alone is not sufficient.
This is causal context, not capital authority.

## 6.16 Exposure Graph
File: `capitalizer_exposure_graph.py`

Function:
- translate open positions into common factor exposures;
- expose hidden shared-factor concentration to cognition.

## 6.17 Portfolio Position Supervisor
File: `capitalizer_portfolio_position_supervisor.py`

Function:
- flag simultaneous positions sharing factors;
- flag multiple open positions;
- request review when portfolio causal concentration exists.

Cannot:
- size;
- widen stop;
- force exit;
- grant capital.

## 6.18 Opportunity Competition
File: `capitalizer_opportunity_competition.py`

Function:
- identify DECISION-state candidates eligible for arbitration;
- expose blockers;
- compare candidate demand with remaining MAX3 slots.

Critically:
- does not select a winner at this pre-strategy layer;
- no outcome-aware ranking;
- no capital authority.

## 6.19 Cognitive Pressure
File: `capitalizer_cognitive_pressure.py`

Postures:
- NORMAL
- CAUTIOUS
- HIGH_SELECTIVITY
- RECOVERY_OBSERVATION
- STOP_SESSION
- STOP_DAY

Inputs include:
- upstream stop requirement;
- same-failure repeat;
- loss cluster;
- uncertainty;
- degraded execution;
- genuinely new causal event.

Rule:
- cognition may increase selectivity/observation;
- cognition may **never increase risk to recover losses**.

## 6.20 Decision Sovereignty
File: `capitalizer_decision_sovereignty.py`

Pre-strategy decisions:
- PASS_TO_STRATEGY
- WAIT
- ABSTAIN

Fail-closed on:
- no slots;
- STOP pressure;
- adversarial falsification;
- conflicted metacognition.

WAIT on:
- insufficient attention;
- immature hypothesis;
- insufficient epistemic readiness;
- challenged candidate;
- not competition-eligible;
- recovery observation without new evidence.

Cognition passes the candidate to source strategy; it does not bypass the source methodology.

## 6.21 Fast Reasoning / Cognitive Engine
Files:
- `capitalizer_reasoning.py`
- `capitalizer_cognitive_engine.py`

Legacy/top-level deterministic fast brain.

Uses:
- situation;
- session ledger;
- loss memory;
- portfolio governor.

Outputs:
- EXECUTE / WAIT / ABSTAIN in its governed path.

The modern Master Frame architecture must preserve source-strategy sovereignty and QORE Risk authority.

## 6.22 Market Stop Cognitive Engine
File: `capitalizer_market_stop_cognitive_engine_v1.py`

Architecture:

`M1 ENTRY CONTRACT -> STOP INTELLIGENCE -> QORE RISK -> EXECUTION`

Internal concepts:
- Structural Brain: where thesis is invalidated;
- Market Memory Brain: what equivalent structure historically required;
- Adversarial Brain: whether a buffer is causal or merely trying to rescue a weak entry.

Rules:
- does not alter ICT/TTrades entry methodology;
- broad historical recovery evidence is insufficient by itself;
- requires exact pre-trade state-family evidence;
- after entry stop can HOLD or IMPROVE;
- never WIDEN.

## 6.23 V50 High-Frequency Cognitive Bridge
File: `capitalizer_v50_cognitive_hf_bridge.py`

Converts each HF opportunity into an auditable state family using:
- H1 state age;
- M15->M1 delay;
- remaining session runway;
- stop/noise;
- destination room;
- trigger family;
- H1 basis;
- session slot;
- metacognitive readiness;
- exact immutable experience memory;
- repeated failure/new-cause state.

Dispositions:
- PASS_TO_COMPETITION
- WAIT_EPISTEMIC
- WAIT_REFRESH_H1
- WAIT_REFRESH_M15
- WAIT_SESSION_RUNWAY
- REFINE_STOP_GEOMETRY
- REFINE_TARGET_LADDER
- ABSTAIN_CONFLICTED
- ABSTAIN_KNOWN_NEGATIVE_STATE

Current consumed-development feature bands:
- H1 FRESH <=60m, AGING <=180m, then STALE;
- M15->M1 IMMEDIATE <=10m, AGING <=45m, then LATE;
- session runway EXHAUSTING <=30m, LIMITED <=60m, otherwise AMPLE;
- stop/noise <=4 tight, <=8 balanced, <=12 wide-watch, otherwise too-wide;
- destination <=0.5R tiny, <=2R balanced, above 2R ambitious.

These bands are hypotheses, **not certified source rules**.

## 6.24 V50 Cognitive Opportunity Snapshot
File: `capitalizer_v50_cognitive_opportunity.py`

Builds one integrated candidate snapshot containing:
- source V49 opportunity;
- V50 cognitive state;
- H1 target ladder;
- dual invalidation;
- recent local M1 range;
- thesis-stop distance;
- execution-stop distance;
- session runway;
- refinement availability.

Refinement routing:
- bad stop geometry -> stop specialist;
- target issue -> target intelligence;
- ready candidate -> opportunity competition.

## 6.25 V50 Target/Stop Intelligence
File: `capitalizer_v50_target_stop_intelligence.py`

Responsibilities:
- causal untouched H1 target ladder;
- M1 execution invalidation;
- M15 thesis invalidation;
- no future-outcome selection.

This is where the current stop-integrity correction lives.

## 6.26 V50 Cognitive Geometry Specialist
File: `capitalizer_v50_cognitive_geometry_specialist.py`

Possible states:
- READY
- WAIT_EXECUTION_STOP
- WAIT_STOP_BREATHING
- WAIT_DESTINATION
- WAIT_ECONOMIC_ASYMMETRY

Purpose:
- repair V49 payoff mismatch without fabricating future targets or widening stops.

## 6.27 V50 -> Master Cognitive Adapter
File: `capitalizer_v50_master_cognitive_adapter.py`

Maps V50 HF candidate state back into the existing Master Cognitive Frame.

Carries:
- freshness;
- destination-known/available;
- state-family failure fingerprint;
- provenance;
- observation tokens.

Rules:
- Master Frame remains mandatory;
- V50 cannot bypass source strategy;
- no entry/capital authority.

## 6.28 Cognitive Feature Atlas
File: `capitalizer_v50_cognitive_feature_atlas.py`

Research dataset of:
- decision-time causal features;
- realized outcomes as **evaluation labels**.

Outcome labels are legal for offline analysis only and must never leak into runtime decisions.

## 6.29 Prequential Cognitive Memory
File: `capitalizer_v50_prequential_cognitive_memory.py`

Causal memory laboratory.

At each candidate:
1. only current causal features are visible;
2. memory can update only from previously accepted trades already closed;
3. blocked outcomes remain invisible;
4. current outcome is never visible before decision.

Tested policies:
- BASELINE_FIRST3
- STRUCTURAL_COGNITION
- MEMORY_CONSENSUS_2
- MEMORY_CONSENSUS_3
- KNN_NEGATIVE
- STRUCTURAL_PLUS_HYBRID

Result: selection-only memory/cognition was economically insufficient. Do not return to memory retuning before geometry/re-arm is solved.

## 6.30 Hierarchical Memory Representation
File: `capitalizer_v50_hierarchical_memory.py`

Corrects a representation defect:
- symbol/session = context;
- they must not become direct negative evidence;
- causal evidence is separated from context and derived dispositions.

This module is architecture-only and does not define an admission rule.

---

# 8. RESEARCH LINEAGE AND WHAT WAS LEARNED

## V48 — density failure

Topology effectively collapsed into one H1 -> one M15 -> one M1 opportunity.

Result:
- only ~159 source-complete opportunities/year.

Conclusion:
- unacceptable for intended high-frequency identity;
- topology rejected.

## V49 — density recovered, economics falsified

Key architecture:
- H1 persistent;
- multiple M15 setups;
- M1 execution.

Capacity holdout 2024-09-17 -> 2025-09-17, already consumed:
- 2,888 pre-MAX3 opportunities;
- 2,007 selected;
- ~6.39/day active;
- capacity PASS.

Development 2025-09-17 -> 2026-09-17:
- 2,857 candidates;
- 2,010 selected after MAX3;
- PF 0.6799468;
- total -227.6746R;
- expectancy -0.11327R;
- DD 229.1673R.

Root cause:
- not lack of targets;
- payoff geometry was incoherent;
- -1R stops were paired with winners averaging only about +0.427R;
- M1 entry + M15 economic stop + nearest H1 destination did not create enough asymmetry.

Important forensic findings:
- H1 context ages badly;
- M15->M1 freshness matters;
- FVG_RETRACE_CISD was better than LIQUIDITY_SWEEP_CISD, but neither family alone solved economics;
- simple MAX1/slot pruning remained negative.

## V50 — cognition reconnected

V50 reconnected the existing cognitive stack to each high-frequency candidate.

Old development cognitive-selection run:
`36744782860`

Results:
- V49 baseline: 2,010 trades, PF 0.67995;
- STRUCTURAL_COGNITION: 467 trades, PF 0.6769;
- MEMORY_CONSENSUS_2: 224 trades, PF 0.5704;
- MEMORY_CONSENSUS_3: 1,332 trades, PF 0.729756;
- KNN_NEGATIVE: 1,592 trades, PF 0.697515;
- STRUCTURAL_PLUS_HYBRID: 412 trades, PF 0.666611.

Conclusion:
- cognition can change selectivity;
- selection-only cognition does not create the missing economic asymmetry;
- do not spend the next cycle retuning memory before geometry.

## V50-G — causal execution geometry

Purpose:
- same V49 M1 entry;
- causal M1 execution stop;
- M15 thesis stop kept separately;
- first causal H1 ladder destination >=1R;
- isolate geometry.

A lookback parity defect was found and corrected before authoritative runs.

Later, the **core stop-integrity defects** described in section 5 were also found.
Therefore old V50-G results are diagnostic only.

### Current corrected-core V50-G diagnostic reference — OWNER-REJECTED AS FINAL CANDIDATE

Run:
`36788519476`

HEAD:
`db0fec90c95bb434e1828aa862de622f3653348d`

Status:
- quality GREEN;
- all 9 market jobs GREEN;
- aggregate GREEN.

Artifact:
`11140305850`  
`qore-capitalizer-v50-g-matrix-db0fec90c95bb434e1828aa862de622f3653348d`

### COGNITIVE_GEOMETRY — corrected core

- trades: **90**
- wins: 39
- losses: 51
- PF: **1.53458998595**
- Total-R: **+26.12311835R**
- expectancy: **+0.29025687R/trade**
- observed DD: **9.0R**
- max losing streak: 9
- stops: 48
- targets: 21
- session exits: 21
- median planned reward: ~2.5714R

Cost stress:
- 0.01R/trade -> PF 1.51084, expectancy +0.28026R, DD 9.09R;
- 0.025R/trade -> PF 1.47601, expectancy +0.26526R, DD 9.225R;
- 0.05R/trade -> PF 1.42025, expectancy +0.24026R, DD 9.45R.

By session:
- ASIA: 39 trades, PF 1.29959, +6.6971R, DD 10.7291R;
- LONDON: 23 trades, PF **3.11872**, +21.1872R, DD 4R;
- NEW_YORK: 28 trades, PF **0.89334**, -1.7611R, DD 7.4582R.

By market:
- AUDJPY: 9 trades, PF 1.45007, +2.25035R, DD3;
- AUDUSD: 8 trades, PF 1.73674, +2.94696R, DD2;
- EURUSD: 13 trades, PF 3.62374, +13.11870R, DD2;
- GBPJPY: 5 trades, PF 0.52368, -1.10379R;
- GBPUSD: 10 trades, PF 2.61369, +8.06845R, DD3;
- NAS100: 5 trades, PF 0.28517, -2.85933R;
- USDCAD: 14 trades, PF 1.58993, +4.12949R, DD2;
- USDJPY: 17 trades, PF 1.23589, +2.60357R, DD 8.7170R;
- XAUUSD: 9 trades, PF 0.44999, -3.03129R.

Interpretation:
- corrected geometry + cognition exposes a real positive economic signal in development;
- gross PF clears the 1.50 per-era certification threshold;
- gross DD is <=10R;
- expectancy is strongly positive;
- London is especially strong;
- Asia is marginal and exceeds the 10R observed-DD gate;
- New York remains negative;
- density collapsed to only 90 trades;
- **corrected-core winner preservation is not yet measured**;
- on 2026-10-10 the Owner explicitly rejected the 90-trade architecture as a final candidate;
- therefore V50-G is diagnostic evidence only and cannot be promoted, certified, or treated as the desired operating model.

### GEOMETRY_ONLY — corrected core

- 216 trades;
- PF 1.06742;
- +8.16657R;
- expectancy +0.03781R;
- DD 20.32895R.

At 0.05R/trade costs:
- PF 0.97939;
- expectancy -0.01219R;
- DD 25.07895R.

Conclusion:
- geometry alone is not enough;
- cognition/competition materially improves the surviving population;
- but the remaining problem is preserving much more edge.

## V52 — simple filtering falsified

V52 tested one categorical decision-time block at a time, then chronological MAX3 recompetition.

24 single-cell policies tested.

Results:
- 6/24 met winner preservation minima;
- **0/24** met preservation + positive gross edge.

Examples:
- block LIMITED runway: winner preservation high, PF ~0.691;
- block LATE execution: winner preservation high, PF ~0.682;
- block TOO_TIGHT stop state: PF ~0.729, but Winner-R preservation below required 90%;
- block STALE H1: reduced DD but destroyed too much edge;
- block LIQUIDITY_SWEEP_CISD: destructive trigger-family pruning.

Conclusion:

`SIMPLE_DECISION_TIME_ADMISSION_FILTERING = FALSIFIED_AS_EDGE_REPAIR`

Do not stack more filters.

## V50-R — causal M1 re-arm

Purpose:
- keep parent H1/M15 thesis;
- if first M1 geometry is WAIT_STOP_BREATHING, do not consume MAX3;
- if geometry is READY but cognition blocks it, do not consume MAX3;
- wait for a **strictly later** source-valid M1 trigger;
- re-evaluate only while M15 protected swing remains intact.

Implemented:
- terminal thesis invalidation;
- local per-setup cognitive-rearm state;
- chronological portfolio MAX3;
- geometry-reason diagnostics;
- first-attempt vs recovered capacity;
- active operating/session day reporting.

Current corrected-core workflow:
run `36788519468`

Status:
- stop-integrity gate GREEN;
- V50-R Ruff GREEN;
- V50-R Mypy FAILED;
- market/aggregate skipped.

Exact current errors:
- `capitalizer_v50_m1_rearm_capacity.py:599`
  incompatible assignment: tuple[str,str] into variable typed as five-field parent key;
- `capitalizer_v50_m1_rearm_capacity.py:601`
  invalid five-field key used for dict keyed by tuple[str,str].

Likely fix:
- do not reuse `key`;
- use distinct names such as `parent_key` and `session_day_key`.

This is a quality/type failure, **not scientific falsification**.

## V51 — multi-era repair lab

Purpose:
- replay another historical era with exactly the same topology and geometry;
- use pre-2016 provider-native M1;
- compare:
  - V49 baseline;
  - Geometry-only;
  - Cognitive-Geometry;
- report PF/DD/expectancy/payoff/risk-adjusted diagnostics plus winner preservation.

Historical era:
2014-09-17 -> 2016-09-17.

Current run:
`36788519475`

Status:
- stop-integrity gate GREEN;
- V51 Ruff GREEN;
- V51 Mypy FAILED;
- market/aggregate skipped.

Exact errors:
- line 129: Returning Any from function declared `dict[str, Any]`;
- line 580: V50GTrade assigned to variable inferred as V49EconomicTrade.

Fix typing only. Do not alter experiment semantics.

## V53 — winner-preserving re-arm economics

Frozen question:
> Can the same H1/M15 thesis wait for a better M1 execution and preserve winner mass while improving PF/DD?

Parent-thesis preservation identity:

`symbol + session + operating_date + h1_state_from + m15_setup_confirmed_at`

A baseline winner counts as preserved only if:
1. the same parent thesis survives recompetition; and
2. transformed execution also realizes positive R.

Winner-R preservation uses transformed realized R, not baseline identity-only R.

Frozen economics:
- later M1 trigger confirmation close;
- causal V50 execution stop;
- M15 thesis retained;
- no widening;
- first H1 ladder T1 >=1R;
- full exit T1 in this isolated replay;
- cost stress 0 / .01 / .025 / .05R.

Current run:
`36788519495`

Status:
- stop-integrity gate GREEN;
- own Ruff fails only I001 import ordering;
- markets skipped.

Fix import ordering only; do not alter methodology.

## V54-A — same-timestamp causal stop-ladder rescue

Question:
If latest M1 pivot is inside local noise, was there already an older, still-valid, causal M1 pivot at the **same entry timestamp** that can serve as execution stop?

Candidate rescue pivot must:
- be risk-side;
- already be causally confirmed;
- remain intact through entry;
- remain strictly inside M15 thesis boundary;
- satisfy frozen 4x–8x local breathing hypothesis;
- preserve a causal H1 destination >=1R.

Stage is pre-economic capacity first.

Current run:
`36788519508`

Status:
- stop-integrity gate GREEN;
- V54-A Ruff GREEN;
- Mypy FAILED.

Exact errors:
- line 363: tuple[str,str] assignment conflicts with five-field parent-key type;
- line 365: five-field key used against dict keyed tuple[str,str].

Same class of fix as V50-R: rename key variables by semantic type.

## V54-B — structural partial + H1 runner lifecycle

A/B population:
exact frozen V50-G Cognitive-Geometry population.

Control:
`FULL_T1_CONTROL`

Treatment:
`PARTIAL50_STRUCTURAL_T2_BE`

Treatment changes only post-T1 lifecycle.

If no causal runner existed at entry:
- full exit at T1.

If runner exists:
1. same admission;
2. same entry;
3. same initial stop;
4. same T1;
5. before T1 no lifecycle change;
6. stop + T1 same M1 -> STOP first;
7. at T1 realize 50%;
8. runner activates only after completed T1 bar;
9. remaining 50% stop tightens to entry/BE;
10. runner target = exact pre-entry H1 runner;
11. same-bar BE + runner -> BE first;
12. same-bar T1 + runner -> no same-bar runner credit;
13. unresolved runner closes at session end.

No:
- future-derived T2;
- outcome-selected target;
- stop widening;
- recovery sizing;
- martingale.

Current run:
`36788519463`

Status:
- stop-integrity gate GREEN;
- Ruff I001 import-order failure in `capitalizer_v54_structural_partial_runner.py`;
- markets skipped.

Fix import order only.

---

# 9. IMPORTANT OLD RESULTS THAT ARE NOW DIAGNOSTIC ONLY

Before the core execution-stop correction, V50-G showed strong loss suppression but extremely poor winner preservation.

Old-core realized preservation diagnostics:
- Geometry-only winner count ~5.04%;
- Geometry-only Winner-R ~21.30%;
- Cognitive-Geometry winner count ~2.92%;
- Cognitive-Geometry Winner-R ~13.69%.

Those figures prove the historical problem — cognition was deleting too much edge — but they are **not authoritative for the corrected core**.

Mandatory next task:
- recompute winner preservation after V50-R/V51/V53 are quality-green on the corrected stop engine.

---

# 10. CURRENT GITHUB QUALITY STATE

Current HEAD:
`db0fec90c95bb434e1828aa862de622f3653348d`

## Certification Standard workflow
Run:
`36788524308`

Status:
**SUCCESS**

Meaning:
- executable certification contract/tests are healthy.

It does **not** mean the Trader is certified.

## QORE CI
Run:
`36788524350`

Status:
**FAILURE**

Exact current global Ruff failures:
1. `capitalizer_v53_winner_preserving_rearm_economics.py` — I001 import block;
2. `capitalizer_v54_structural_partial_runner.py` — I001 import block.

Therefore the global CI red state is currently explained by known style failures, not a failed economic test.

---

# 11. CERTIFICATION STANDARD V2 — WHAT MUST BE PASSED

Executable contract:
`capitalizer_scalper_certification_standard_v2.py`

The Trader is **NOT certified**.

Mandatory numeric gates:

## Per designated OOS era
- PF >= **1.50**
- expectancy > **0R/trade**
- annualized Sharpe >= **1.50**
- annualized Sortino >= **2.00**
- observed max DD <= **10R**
- payoff >= **1.20**, unless an explicitly reviewed statistical-compensation exception exists

## Combined OOS
- PF >= **1.70**

## Monte Carlo
- probability positive >= **90%**
- p95 DD <= **15R**

## Post-cost
- PF > **1.00**
- expectancy > **0**

## Winner preservation
When intelligence removes/defers/transforms trades:
- Winner Count Preservation >= **80%**
- Winner-R Preservation >= **90%**

Additional mandatory evidence:
- temporal stability verified;
- anti-leakage audit passed;
- no prohibited outcome-aware logic;
- catastrophic loss clustering absent;
- MAE/MFE audit complete;
- loser anatomy audit complete;
- density sufficient after quality;
- final independent/prospective evidence integrity;
- final independent/prospective evaluation performed exactly under freeze;
- final evidence passed;
- QORE Risk review passed;
- CIBO review passed;
- independent validation passed;
- no fatal falsification.

The old “>=1,332 trades/year” number is **not a hard Owner gate anymore**.
High-frequency density remains a design goal and the certification standard still requires sufficient density after quality; do not maintain bad trades merely to satisfy a count.

---

# 12. WHAT IS STILL MISSING BEFORE CERTIFICATION

This is the critical unfinished work.

## P0 — make the corrected-core research chain executable

Repair without changing methodology:
1. V50-R Mypy key collision;
2. V51 two Mypy errors;
3. V53 import ordering;
4. V54-A Mypy key collision;
5. V54-B import ordering;
6. rerun QORE CI until GREEN.

Do not change thresholds while doing these fixes.

## P1 — close corrected-core V50-R

Need actual 9/9 capacity:
- first READY;
- recovered READY;
- cognitive recovered READY;
- thesis invalidations;
- attempts by index;
- by market/session;
- portfolio MAX3;
- operating-day density.

Question:
Does re-arm recover meaningful edge capacity without widening stops or allowing dead thesis?

## P1 — close V51 multi-era

Run 2014–2016 9/9.

Need:
- V49 baseline;
- corrected Geometry-only;
- corrected Cognitive-Geometry;
- PF/DD/expectancy/payoff;
- by session/market;
- winner count preservation;
- Winner-R preservation;
- loss recall;
- cost stress.

This tells us whether corrected V50 geometry generalizes beyond 2025–2026.

## P1 — close V53 winner-preserving economics

This is likely the most important active experiment.

Need to determine whether later M1 re-arm can:
- preserve >=80% winners;
- preserve >=90% Winner-R;
- materially improve PF;
- materially reduce DD;
- maintain enough density;
- remain causal.

Reject it even if PF improves if preservation fails.

## P1 — close V54-A

First capacity only.

If stop-ladder rescue recovers material opportunities:
- freeze the exact rescue law;
- only then open a separately predeclared economic replay.

Do not use economic outcome to choose which historical pivot is “best”.

## P1 — close V54-B

Isolate lifecycle effect.

Need exact A/B:
- same candidate population;
- same entries;
- same initial stops;
- same T1;
- only post-T1 management differs.

If beneficial:
- freeze lifecycle unchanged;
- only after V53/V54-A closes may it be applied to a winner-preserving transformed population without retuning.

## P2 — recompute corrected-core winner preservation

Current authoritative V50-G matrix does not contain corrected-core preservation.

Must produce:
- Winner Count Preservation;
- Winner-R Preservation;
- Loss Recall;
- Full-Stop Recall;
- baseline winners displaced by MAX3 recompetition;
- winners transformed into non-winners;
- new parent theses selected.

This is mandatory to know whether the new PF 1.5346 was bought by destroying edge.

## P2 — explicit realized payoff report

The corrected V50-G matrix reports median planned reward but not the certification payoff metric in final form.

Need explicitly:
- average realized winner;
- average realized loser magnitude;
- payoff ratio;
- by era/session/market.

Do not substitute planned reward for realized payoff.

## P2 — Sharpe/Sortino with explicit zero-trade semantics

Certification requires:
- return interval;
- frequency;
- annualization factor;
- risk-free/MAR;
- zero-trade period treatment;
- cost basis;
- exact population.

Current research diagnostics intentionally label zero-trade-days as not included.
Final OOS report must freeze and justify the treatment before reading results.

## P2 — temporal stability

Must show the candidate is not one-period luck:
- multiple historical eras;
- session stability;
- market stability;
- year/month stability;
- no hidden dependence on one market or one regime.

Do not “solve” weak markets retrospectively by deleting them after seeing outcome unless a new causal rule is predeclared and independently validated.

## P2 — MAE/MFE and loser anatomy

Mandatory:
- MAE;
- MFE;
- stop-hit anatomy;
- session-exit anatomy;
- failed-thesis vs failed-execution distinction;
- context age;
- execution freshness;
- target availability;
- stop/noise state;
- market/session/regime;
- winner destruction analysis.

## P2 — loss clustering

Measure:
- cluster count;
- streak/run length;
- cumulative cluster R;
- duration;
- concentration by market/session/regime/setup;
- factor/correlation context.

Current corrected Cognitive-Geometry has max losing streak 9 and Asia DD >10R, so clustering deserves explicit study.

## P2 — provider/broker cost model

Current V50-G uses explicit generic R stress:
- 0;
- .01R;
- .025R;
- .05R/trade.

This is useful research stress, not a claim of broker-native exact costs.

Before certification:
- integrate/validate actual provider/broker spread/commission/slippage assumptions where required;
- report post-cost PF and expectancy.

## P2 — Monte Carlo

Only after one candidate is frozen:
- reshuffle;
- dependence-aware sequence stress;
- losing-cluster stress;
- cost stress.

Required:
- positive probability >=90%;
- p95 DD <=15R.

Freeze:
- seeds;
- block semantics;
- sample count;
- chronology;
- cost assumptions.

## P2 — anti-leakage audit

Must verify:
- no current outcome visible at decision;
- no blocked outcome enters runtime memory;
- no future target;
- no future stop pivot;
- no hidden next-bar data;
- no retrospective market/session pruning;
- no survivor rule selected from OOS outcome.

## P3 — freeze one immutable candidate

Before final evidence:
- code fingerprint;
- configuration fingerprint;
- data-source fingerprint;
- stop/target/lifecycle law;
- cognitive law;
- session/market universe;
- MAX3 behavior;
- cost model;
- MC model;
- reporting schema.

No retuning after freeze.

## P3 — final independent/prospective OOS

Historical windows may all be used for repair.

Therefore final proof must be:
- independent governed provider/source not used for tuning; or
- prospective future period frozen before outcomes.

Evaluate exactly once for the immutable candidate.

If falsified:
- reject candidate;
- consumed evidence stays consumed;
- next candidate requires a new independent/prospective validation object.

## P3 — reviews

Still mandatory before ACCEPTED:
- QORE Risk review;
- CIBO review;
- independent validation.

---

# 13. DATA SOURCES AND RETAINED ARTIFACTS

## Current development provider-native M1 source

Run:
`35548099334`

Source SHA:
`18c338aedd5013ce65a6cb6408ffbc2e904a6217`

Used by 9-market V49/V50 development workflows.

Do not synthesize M1 when provider-native retained M1 exists.

## Pre-2016 multi-era provider-native source

Run:
`36367221571`

Source SHA:
`660881acc008593eb04b7be2c4e2e60f06950a4d`

Research era:
2014-09-17 -> 2016-09-17.

Under Owner override this era is valid for repair research and is considered consumed once used.

---

# 14. KEY FILE MAP FOR THE NEXT ARCHITECT

## Frozen identity / operating model
- `capitalizer_contract.py`
- `capitalizer_session_clock.py`
- `capitalizer_high_frequency_identity_v49.py`
- `capitalizer_high_frequency_decision_graph_v49.py`
- `capitalizer_high_frequency_capacity_census_v49.py`
- `capitalizer_high_frequency_trader_v49.py`
- `capitalizer_h1_context_state_v49.py`

## Cognitive core
- `capitalizer_master_cognitive_frame.py`
- `capitalizer_master_brain.py`
- `capitalizer_global_world_model.py`
- `capitalizer_context_brains.py`
- `capitalizer_market_brain_registry.py`
- `capitalizer_perception_integrity.py`
- `capitalizer_attention.py`
- `capitalizer_regime_intelligence.py`
- `capitalizer_session_journey_intelligence.py`
- `capitalizer_memory.py`
- `capitalizer_experience_memory.py`
- `capitalizer_confidence.py`
- `capitalizer_metacognition_v2.py`
- `capitalizer_adversarial_reasoning_v2.py`
- `capitalizer_cross_market_causality.py`
- `capitalizer_exposure_graph.py`
- `capitalizer_portfolio_position_supervisor.py`
- `capitalizer_opportunity_competition.py`
- `capitalizer_cognitive_pressure.py`
- `capitalizer_decision_sovereignty.py`
- `capitalizer_reasoning.py`
- `capitalizer_cognitive_engine.py`

## V50 HF cognitive integration
- `capitalizer_v50_cognitive_hf_bridge.py`
- `capitalizer_v50_cognitive_opportunity.py`
- `capitalizer_v50_target_stop_intelligence.py`
- `capitalizer_v50_cognitive_geometry_specialist.py`
- `capitalizer_v50_master_cognitive_adapter.py`
- `capitalizer_v50_cognitive_feature_atlas.py`
- `capitalizer_v50_prequential_cognitive_memory.py`
- `capitalizer_v50_hierarchical_memory.py`

## Active repair experiments
- `capitalizer_v50_m1_rearm_capacity.py`
- `capitalizer_v51_multi_era_repair.py`
- `capitalizer_v52_winner_preserving_filter_falsification.py`
- `capitalizer_v53_winner_preserving_rearm_economics.py`
- `capitalizer_v54_causal_m1_stop_ladder_rescue.py`
- `capitalizer_v54_structural_partial_runner.py`

## Certification
- `capitalizer_scalper_certification_standard_v2.py`
- `capitalizer_scalper_certification_metrics_v2.py`
- `capitalizer_scalper_monte_carlo_v2.py`
- `docs/research/QORE-CAPITALIZER-SCALPER-CERTIFICATION-STANDARD-V2.md`

---

# 15. KEY GITHUB ACTIONS WORKFLOWS

Active corrected-core workflows:

- `.github/workflows/qore-capitalizer-v50-g-cognitive-geometry.yml`
- `.github/workflows/qore-capitalizer-v50-r-rearm-capacity.yml`
- `.github/workflows/qore-capitalizer-v51-pre2016-multi-era-repair.yml`
- `.github/workflows/qore-capitalizer-v52-winner-preserving-filter-falsification.yml`
- `.github/workflows/qore-capitalizer-v53-winner-preserving-rearm-economics.yml`
- `.github/workflows/qore-capitalizer-v54-causal-m1-stop-ladder-rescue.yml`
- `.github/workflows/qore-capitalizer-v54-structural-partial-runner.yml`
- `.github/workflows/qore-capitalizer-scalper-certification-standard-v2.yml`
- `.github/workflows/ci.yml`

All V50-derived experiments have been bound to the V50 stop-integrity dependency so a future stop-engine change forces revalidation.

---

# 16. IMPORTANT ENGINEERING COMMITS FROM THIS WORK CYCLE

Selected continuity commits:

- `f89faddd01192e4abcfb8d6f402503e84817c899` — align V48 London detector-readiness test with actual reusable CISD primitive semantics.
- `0d2b7cbbbb857b8faaf808aa9b85bf8a318d967a` — enforce V50-R M15 thesis validity.
- `f488da2b4749fe0f3ee687d5082beb81919126ee` — tests for V50-R thesis invalidation.
- `f9b5ee98d521b10111fbd18a86cdb47fd370d0d8` — V50-R portfolio MAX3 capacity.
- `1de8ecfc0db2ef8a857375e66b1a9da919ca5900` — MAX3 capacity tests.
- `a58cf5536b7c0f74b9b16ed2519c7581457033d4` — clarify density day semantics.
- `05e8996575d3c226df588db5489f115c1c40d37c` — geometry-reason diagnostics.
- `cc0ded7671c544a642951fc28499d72f2c8a82aa` — serialize earlier V50-R runs.
- `586434b98a8401b39bf28d76b8cb34216b115835` — fix V50-R cognitive re-arm attribution to local setup state.
- V51/V52/V53/V54 modules/workflows added during the subsequent repair sequence.
- `47a1dc67e42aa7693c07fd2c01130c3c0e9868b6` — intact V50 execution pivots.
- `bcd50645418d981b484c2e065a59841e0b33b58d` — pivot-integrity tests.
- `68121971eed5670a5af5dfa6330ee9c8ce2fb2b0` — keep V50 execution stop inside M15 thesis.
- `57bc33c78cf1635f9c1d0939adf0b68e229b2ade` — thesis-boundary tests.
- `86ee65961cc3239d3df7bc6455902d1feeac34b1` — bind experiment workflows to stop-engine dependency.
- `db0fec90c95bb434e1828aa862de622f3653348d` — explicit stop-integrity gate in all six downstream experiment workflows.

---

# 17. RESEARCH LAWS THAT MUST NOT BE BROKEN

The next architect must preserve these laws:

1. No Daily/H4 decision layers.
2. H1 persistent, reusable context.
3. M15 is setup/thesis structure.
4. M1 is execution.
5. MAX3/session = ceiling, not quota.
6. No superintersection of every M1 technique.
7. No outcome-aware candidate selection.
8. No future-derived stop.
9. No future-derived target.
10. No post-entry stop widening.
11. No martingale.
12. No recovery sizing.
13. No “fix PF” by deleting most winners.
14. Symbol/session identity must not become direct negative causal evidence in memory.
15. Blocked outcomes must not enter runtime/prequential memory.
16. Historical windows may be used for research, but consumed data cannot be final fresh proof.
17. Final certification requires independent/prospective frozen evidence.
18. All engineering/evidence work is GitHub-only.
19. PR stays DRAFT / UNMERGED without Owner authorization.
20. No LIVE/VPS/production/real-capital changes.

---

# 18. SCIENTIFIC PRIORITY FROM THIS HANDOFF

The core question is no longer:

> “Which trades can we delete to make PF look good?”

V52 already falsified that path.

The correct question is:

> “How do we preserve the same valid H1/M15 thesis and its winner mass while transforming execution geometry and lifecycle so losses compress, payoff improves and drawdown falls?”

Priority research order:

1. fix current quality blockers;
2. close V50-R with emphasis on recovering many more executable parent theses;
3. close V51;
4. close V53 and measure whether re-arm restores winner/density mass;
5. close V54-A and quantify same-timestamp stop-ladder recovery;
6. close V54-B strictly as lifecycle improvement, not as a substitute for density recovery;
7. recompute corrected-core winner preservation;
8. reject any architecture that obtains PF/DD by collapsing the Scalper into a tiny survivor set;
9. compare transformed populations without retuning;
10. freeze the best genuinely high-frequency causal candidate;
11. run full certification battery;
12. only after pass: Risk/CIBO/independent review;
13. no deployment until explicit Owner instruction.

---

# 19. CURRENT BOTTOM LINE

What is already demonstrated:

- High-frequency source capacity exists under persistent H1 topology.
- The Owner explicitly rejected the 90-trade V50-G survivor architecture as an acceptable final Scalper candidate.
- V49 baseline economics are unacceptable.
- Simple cognition/memory selection does not solve the problem.
- Simple categorical filtering does not solve the problem without destroying edge.
- Causal M1 execution geometry materially improves economics.
- After the corrected stop-engine rules, V50-G Cognitive-Geometry reached:
  - PF 1.53459;
  - expectancy +0.29026R;
  - DD 9R;
  - positive cost-stress economics;
  - especially strong London behavior.
- New York remains negative.
- Asia remains below desired quality and slightly above the 10R DD gate.
- The candidate population is too small for promotion.
- Corrected-core winner preservation is unknown and mandatory.
- V50-R/V51/V53/V54 are blocked by quality errors, not by market falsification.
- The certification contract itself is GREEN.
- The Trader itself is **NOT certified**.

The next architect should **repair the blocked research harnesses first** and continue the winner-preserving transformation program. Do not restart strategy research and do not return to destructive filtering.

---

# 20. CANONICAL REFERENCES

PR:
- #623

Current engineering HEAD:
- `db0fec90c95bb434e1828aa862de622f3653348d`

Corrected-core authoritative V50-G:
- run `36788519476`
- matrix artifact `11140305850`

Blocked corrected-core runs:
- V50-R `36788519468`
- V51 `36788519475`
- V53 `36788519495`
- V54-A `36788519508`
- V54-B `36788519463`

Certification-standard workflow:
- `36788524308` — SUCCESS

QORE CI:
- `36788524350` — FAILURE due known Ruff I001 imports in V53/V54-B

Provider-native development M1:
- run `35548099334`
- SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`

Pre-2016 provider-native M1:
- run `36367221571`
- SHA `660881acc008593eb04b7be2c4e2e60f06950a4d`

---

**END OF MASTER HANDOFF**

This handoff is a continuity document, not a certification or deployment authorization.
