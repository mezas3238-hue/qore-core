# QORE CORE — MASTER HANDOFF VT08 COGNITIVE EXPANSION 5M V1

**Handoff date:** 2026-10-10  
**Repository:** `mezas3238-hue/qore-core`  
**Canonical PR:** #634 — `[DRAFT] VT08 Cognitive Expansion 5M V1 — EURJPY USDCHF NZDUSD CADJPY + USDCAD`  
**Canonical branch:** `agent/vt08-cognitive-expansion-5m-v1-001`  
**Base branch:** `agent/vt08-cognitive-v1-001`  
**Handoff parent SHA:** `6020b487ad9e4e4eed0bb70a8955ac003a8a02c2`  
**State at handoff:** OPEN / DRAFT / UNMERGED / MERGEABLE  
**Authority:** RESEARCH ONLY — NO DEMO/LIVE/PRODUCTION/REAL-CAPITAL AUTHORITY

---

## 0. Executive instruction to the next architect

Continue this exact trader identity until certification is genuinely earned from evidence.

Do **not** rename, silently replace, merge with another trader, or declare certification from partial metrics. GitHub PR #634 is the source of truth. Verify the current HEAD before every new write because this branch may be modified concurrently.

The Owner has explicitly rejected the prior density level. Approximately 149–182 M3 trades per market over ~3 years is not sufficient for the intended trader. The next architect must preserve source fidelity while increasing legitimate opportunity density and must not manufacture density by accepting invalid setups, merging LTF profiles after outcomes, selecting markets/anchors/sides post hoc, or using capital weighting to disguise raw methodology economics.

The most important new technical finding at this handoff is:

> **The current PR #634 expansion replay path is not wired through the full VT08 Cognitive V1 orchestrator.**

The inspected files
`vt08_cognitive_expansion_5m_evaluator_v1.py`,
`vt08_cognitive_expansion_5m_backtest_v1.py`, and
`vt08_cognitive_latest_ps_core_stack_frontier_v1.py`
construct/evaluate methodology candidates and replay trades directly. They do not call
`evaluate_cognitive_hypothesis()` or `evaluate_in_trade_cognition()` from
`vt08_cognitive_orchestrator.py`.

Therefore all PF/DD/density numbers obtained so far are valid for their exact research contracts, but they **do not prove that the complete cognitive stack governed every entry and every position**. This is a P0 certification blocker.

---

# 1. Trader identity and mission

## 1.1 Current research identity

`VT08_COGNITIVE_EXPANSION_5M_V1`

Five-market research universe:

- EURJPY
- USDCHF
- NZDUSD
- CADJPY
- USDCAD — control market

Owner operational Forex anchors:

- 01:00 New York
- 05:00 New York
- 09:00 New York

The program is stacked on VT08 Cognitive V1 but is not authorized to expand the certified runtime market list.

## 1.2 Source lineage

Primary methodology authority remains the TTrades 4-Hour Power of Three source:

- `youtube:FAKWJ-1NlLE`
- primary-source SHA-256:
  `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`

Authority order:

1. Primary TTrades video/audio/framebook.
2. Official later TTrades clarifications with provenance.
3. Frozen independent reconstruction/witness evidence.
4. QORE implementation.

Performance must never be used to resolve a methodology ambiguity.

Important lineage:

- PR #518 — pre-R3.2 forensic/source-executable baseline; economics cannot be reused as current qualification.
- PR #520 — R3.2 source kernel / split authority foundation.
- PR #521 — narrow R3.8 B01 source-faithful replay.
- R3.9 source contract — final narrow source-to-code adjudication with explicit containments.
- PR #634 — current Cognitive Expansion 5M research line.

---

# 2. Source-resolved VT08 operating model

## 2.1 H4 delivery model

Bullish delivery:

`OPEN -> LOW manipulation -> HIGH expansion -> CLOSE` (OLHC)

Bearish delivery:

`OPEN -> HIGH manipulation -> LOW expansion -> CLOSE` (OHLC)

VT08 interprets the H4 cycle as PO3:

`Accumulation -> Manipulation -> Distribution/Expansion`.

## 2.2 Daily bias

Current source-resolved bias family is the four-case PDH/PDL continuation/reversal logic retained by the R3.9 contract.

The exact source-day boundary remains a QORE containment where applicable. The 17:00 NY -> 17:00 NY historical reconstruction must not be relabeled as universal TTrades authority.

## 2.3 C2 / C3 fractal

Source supports:

- C2 reversal/expansion when the opposing run is qualitatively shallow / early and range remains.
- C3 continuation when the C2 opposing run is large/deep or materially consumes range.

Important: no source-authorized numeric threshold exists for “shallow” versus “large/deep”. Do not invent ATR, wick %, candle count, pips, ticks, or body/wick ratio as if it were source authority.

## 2.4 CISD

Current source contract:

- identify the first opposing candle in the opposing delivery sequence;
- its **open** is the CISD level;
- confirmation requires a **close through** that level;
- wick-only breach is insufficient.

## 2.5 Protected Swing

A Protected Swing is the structural extreme created after interaction with the relevant important level / POI and confirmed by CISD.

The Protected Swing extreme is the source-resolved structural invalidation reference.

No source-exact broker stop offset is currently established.

## 2.6 Entry families

R3.2 carries six source-supported entry-family identities:

1. reversal-entry
2. continuation-entry
3. confident-entry
4. positional-entry
5. open-entry
6. POI-continuation-entry

Current machine authority in PR #634:

- **positional-entry:** machine-complete in the narrow B01 path.
- the other five families: **SOURCE_IDENTITY_ONLY**; exact historical fill contract not frozen.

Do not convert a source identity into historical fills until a provenance-bound entry + stop + target bundle is frozen before economics.

## 2.7 Positional entry

For the narrow machine-complete path:

- fractal / Protected Swing must already be complete before the decision;
- positional entry reference = new H4 open;
- a Protected Swing confirmed after that open cannot retroactively authorize a fill at the open.

## 2.8 Stops

R3.2 recognizes five stop-family identities:

- Protected Swing stop
- 50% CISD / EQ stop
- opposing-candle stop
- FVG stop
- body-low/body-high family

There is no universal Cartesian combination with all entry families.

The narrow B01 replay uses the Protected Swing structural extreme.

## 2.9 Targets

Source target family is contextual and includes structural liquidity objectives. R3.9 retains fixed 2R only as a conservative **QORE research replay containment**.

Do not claim 2R is the universal TTrades target rule.

## 2.10 Filled-position lifecycle

The existing replay contains still-open modeled positions at the next H4 boundary. R3.9 explicitly records the exact filled-position H4 lifecycle as fundamentally unresolved source authority.

Any new lifecycle policy must be pre-frozen and not selected from best historical PnL.

## 2.11 LTF profiles

Source-authorized independent observation profiles:

- M15_STANDARD
- M5_FRACTAL
- M3_FRACTAL

They are independent alternatives.

**Prohibited:** unioning M15/M5/M3 after seeing outcomes or using one timeframe retrospectively to confirm another unless a separately source/Owner-authorized composition is frozen.

## 2.12 Owner daily cardinality

Current R3.2 Human Owner execution policy:

`MAXIMUM_FILLED_TRADES_PER_MARKET_PER_NEW_YORK_DATE = 1`

This is an Owner policy, not a proven universal TTrades source rule.

Multiple diagnostic candidates may coexist. Final selected/pending/filled/terminal trades remain at most one per market/day unless the Owner explicitly changes this policy in a new frozen contract.

---

# 3. Cognitive architecture — complete component map

The parent cognitive architecture is `VT08_FOREX_COGNITIVE_V1`.

Architecture freeze:
`docs/research/VT08_FOREX_COGNITIVE_V1_ARCHITECTURE_FREEZE.md`

The architecture is research/shadow and has no capital/order authority.

## 3.1 Strategy Identity Memory

**File:** `src/qore/infrastructure/traders/vt08_cognitive_strategy_identity_memory.py`

**Purpose:** answer “What is VT08 and what must always remain true?”

Contains immutable methodology identity and fingerprints:

- source kernel identity;
- Forex authority;
- anchors;
- market/direction authority;
- H4/LTF semantics;
- bias;
- POI;
- CISD;
- Protected Swing;
- entry/stop/target/lifecycle identity;
- cardinality invariants;
- unresolved-policy markers.

Guards:

- Market Memory cannot rewrite methodology.
- Trader Experience cannot rewrite methodology.
- QORE Risk remains final capital authority.

It may not contain retrospective best-PF selection rules.

## 3.2 CIBO Market Memory

**File:** `src/qore/infrastructure/traders/vt08_cognitive_cibo_market_memory.py`

**Purpose:** answer “How does this market/anchor normally behave structurally?”

Market × Anchor specialist memory.

Existing bound evidence:
- run `34759027136`
- HEAD `64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222`
- holdout identity `VT08_R3_15_FINAL_INDEPENDENT_2020_2022`

Stores aggregate causal/association priors such as:

- H4 range distribution;
- body fraction;
- close location;
- upper/lower wick fractions;
- bullish-close rate;
- market × 01/05/09 NY context.

Authority:

- no market-ranking authority;
- no direction authority;
- no EXECUTE/ABSTAIN authority;
- no capital authority.

## 3.3 Trader Experience Memory

**File:** `src/qore/infrastructure/traders/vt08_cognitive_trader_experience_memory.py`

**Purpose:** answer “What has VT08 learned from its own interaction with this market?”

Stores governed historical research experience:

- market × anchor sample;
- win/loss;
- mean R;
- PF;
- side counts;
- terminal-path counts;
- supported lessons;
- falsified hypotheses;
- unresolved hypotheses;
- causal failure modes;
- position-management lessons.

Critical boundary:

PF/PnL fields may inform research hypotheses but **may not directly gate EXECUTE/WAIT/ABSTAIN**.

Experience statistics do not grant execution authority.

## 3.4 Combined Cognitive Memory

**File:** `src/qore/infrastructure/traders/vt08_cognitive_memory.py`

Builds the governed memory bundle:

- architecture fingerprint;
- Strategy Identity fingerprint;
- CIBO Market Memory fingerprint;
- Trader Experience fingerprint;
- market × anchor context fingerprint.

This is the read-only evidence/memory context consumed by higher reasoning.

## 3.5 Causal Situation Model

**File:** `src/qore/infrastructure/traders/vt08_cognitive_situation_model.py`

**Purpose:** represent the complete decision-time state as-of a causal timestamp.

Fields include:

- market;
- anchor;
- side;
- LTF profile;
- methodology validity;
- source identity completeness;
- H4 lifecycle validity;
- bias state;
- scenario state;
- POI state;
- Protected Swing state;
- CISD state;
- displacement state;
- entry state;
- entry freshness;
- liquidity state;
- range state;
- volatility state;
- journey stage;
- structural destination state;
- exhaustion state;
- risk geometry;
- position state;
- supporting evidence;
- material contradictions;
- material uncertainties;
- nonmaterial observations;
- path efficiency / overlap / displacement / destination distance when causally observable.

Hard rules:

- timestamp-aware;
- no future bars;
- no terminal PnL;
- no post-outcome labels;
- UNKNOWN remains UNKNOWN; never guessed.

## 3.6 Hypothesis Lifecycle

**File:** `src/qore/infrastructure/traders/vt08_cognitive_hypothesis.py`

Lifecycle:

`FORMING -> CONFIRMED -> WAITING -> EXECUTABLE`

or

`FORMING/CONFIRMED/WAITING -> CONTRADICTED -> KILLED`

Rules:

- ABSTAIN kills the current source hypothesis.
- KILLED is terminal for that source fingerprint.
- same source event cannot resurrect.
- rearm requires a genuinely new source fingerprint / structural event.
- EXECUTE requires confirmation completeness.

This prevents fallback execution after cognition has rejected the actual hypothesis.

## 3.7 Sovereign Reasoning Engine

**File:** `src/qore/infrastructure/traders/vt08_cognitive_reasoning.py`

Decision vocabulary:

- EXECUTE
- WAIT
- ABSTAIN

Reasoning consumes the Situation Model plus governed memory context.

Core behavior:

- material contradiction -> ABSTAIN;
- material unresolved uncertainty -> WAIT;
- incomplete CISD -> WAIT;
- incomplete Protected Swing -> WAIT;
- non-actionable entry -> WAIT;
- stale/non-current entry -> WAIT;
- otherwise causal executable hypothesis -> EXECUTE.

Every decision retains:

- reason codes;
- supporting evidence;
- contradictions;
- uncertainty;
- adversarial assessment;
- metacognitive state;
- Situation fingerprint;
- Strategy Identity fingerprint;
- Cognitive Memory fingerprint;
- Market × Anchor context fingerprint.

## 3.8 Adversarial Reasoning

Implemented within the reasoning layer.

Purpose: ask the inverse question before execution:

> What observable causal evidence says this hypothesis should not execute?

It checks for:

- methodology invalidity;
- incomplete source identity;
- invalid H4 lifecycle;
- invalid risk geometry;
- contradicted entry;
- contradicted destination;
- material contradiction;
- unresolved material uncertainty.

It may not invent new strategy rules.

## 3.9 Metacognition

Knowledge states:

- KNOWN
- SUPPORTED
- AMBIGUOUS
- CONTRADICTED
- UNKNOWN

Purpose:

- distinguish evidence from ignorance;
- avoid unsupported pseudo-confidence;
- surface execution-material unknowns;
- block EXECUTE when causal knowledge is materially unresolved.

No arbitrary confidence percentages are authorized.

## 3.10 Journey / Destination Intelligence

**File:** `src/qore/infrastructure/traders/vt08_cognitive_journey_intelligence.py`

Journey states include:

- PRE_ENTRY
- ADVANCING
- STALLED
- EXHAUSTION_RISK
- DESTINATION_REACHED
- INVALIDATED
- UNKNOWN

Destination states include:

- SUPPORTED
- APPROACHING
- REACHED
- CONTRADICTED
- UNKNOWN

Purpose:

- reason beyond the entry;
- track whether expected delivery is advancing;
- detect causal stalling/exhaustion;
- track structural destination;
- detect lifecycle expiration or thesis invalidation.

No future terminal journey label is allowed.

## 3.11 Position Intelligence

**File:** `src/qore/infrastructure/traders/vt08_cognitive_position_intelligence.py`

Actions:

- HOLD
- PROTECT
- REDUCE
- EXIT

Default research policy:

- structural protection disabled until VT08-specific calibration;
- exhaustion reduction disabled until VT08-specific calibration;
- H4 lifecycle end may recommend EXIT;
- causal thesis invalidation may recommend EXIT;
- bound destination reached may recommend EXIT.

Hard invariant:

**stop may improve or hold; never widen.**

Position Intelligence:

- cannot submit orders;
- cannot change quantity;
- has no capital authority.

## 3.12 Cognitive Orchestrator

**File:** `src/qore/infrastructure/traders/vt08_cognitive_orchestrator.py`

Desired pre-entry flow:

`source hypothesis -> Situation Model -> reason() -> Hypothesis Lifecycle`

Desired in-trade flow:

`Situation Model -> Journey Intelligence -> Position Intelligence`

Key functions:

- `evaluate_cognitive_hypothesis()`
- `evaluate_in_trade_cognition()`

This is the component that must be bound into the expansion replay before the replay can be described as fully cognitive.

## 3.13 QORE Risk / CIBO authority boundary

Cognition can recommend/interpret but cannot mint:

- capital;
- leverage;
- lot size;
- broker permission;
- execution authority.

Desired final chain:

`VT08 methodology -> cognition -> governed CIBO posture -> QORE Risk -> execution -> Position Intelligence`

QORE Risk remains sovereign.

---

# 4. Critical integration gap: current expansion replay is not fully cognitive

This is a mandatory P0 item for the next architect.

Inspection at parent HEAD `6020b487...`:

### `vt08_cognitive_expansion_5m_evaluator_v1.py`

Directly performs:

- source H4 reconstruction;
- bias resolution;
- C2 reversal test;
- Protected Swing extraction;
- entry at H4 open;
- stop at PS;
- fixed 2R target.

No import/call to Cognitive Orchestrator was found in the inspected replay path.

### `vt08_cognitive_expansion_5m_backtest_v1.py`

Directly:

- calls the expansion evaluator;
- builds `model_trade()`;
- resolves stop/target/H4 containment.

No pre-entry `evaluate_cognitive_hypothesis()` call and no in-trade `evaluate_in_trade_cognition()` call in this path.

### `vt08_cognitive_latest_ps_core_stack_frontier_v1.py`

Uses methodology scanner + latest-PS selector + Core Stack management. It does not prove that the full Cognitive V1 reasoning engine governed admission.

## Consequence

Do **not** call current PF/DD results “full-cognitive performance”.

Correct description:

- methodology replay;
- source/density research;
- management/frontier research;
- cognition architecture available but not yet bound as sovereign per-trade execution path.

## Required repair

Build a dedicated cognitive replay adapter which, for every candidate/source event:

1. builds the causal `Vt08ForexSituationModel`;
2. binds Strategy Identity, CIBO Market Memory and Trader Experience;
3. creates/advances a `Vt08Hypothesis`;
4. calls `evaluate_cognitive_hypothesis()`;
5. allows trade admission only on cognitive EXECUTE;
6. preserves WAIT as a live hypothesis, not a rejection;
7. kills ABSTAIN source identity;
8. permits rearm only from genuinely new structural source event;
9. after fill, updates causal Situation Model through the trade;
10. calls `evaluate_in_trade_cognition()`;
11. records Journey and Position Intelligence decisions;
12. retains exact counterfactual baseline: methodology-valid candidate versus cognitive decision;
13. proves no future/PnL leakage.

Until this is complete, Cognitive V1 itself is not economically validated by PR #634.

---

# 5. Research completed before this handoff

## 5.1 Original five-market truth audit

Consumed common ~1095-day evidence.

Run:
`35938734279`

Original narrow line:

| Market | Trades | 2Y equivalent | Raw equal-risk PF | Core Stack PF |
|---|---:|---:|---:|---:|
| EURJPY | 82 | 54.67 | 1.3251 | 1.8868 |
| USDCHF | 77 | 51.33 | 0.5638 | 0.6719 |
| NZDUSD | 114 | 76.00 | 1.2278 | 1.2051 |
| CADJPY | 86 | 57.33 | 1.0837 | 1.4367 |
| USDCAD | 98 | 65.33 | 0.6256 | 0.6115 |

Owner decision:
**REJECTED_FOR_DENSITY**.

The old minimum 50 trades / 2Y gate is retired for this expansion program.

A new numeric density acceptance gate still needs to be frozen separately.

## 5.2 Density root-cause

11,655 observed anchors were reconciled.

Main first failures:

- C2 close not inside reference: 3,987
- bias unresolved: 2,071
- both-side sweep: 1,347
- side/bias mismatch: 1,317
- no reference sweep: 1,085
- no Protected Swing: 769 in the earlier funnel
- incomplete H4: 406
- multiple PS: 145
- incomplete source day: 40

The density problem is mainly upstream methodology/admission, not daily uniqueness.

## 5.3 Three-year opportunity census

Run:
`36057198230`

Terminal profile variants:

- M15: 579
- M5: 759
- M3: 812

Exact distinct terminal C2 union by `market + signal_at + side`:

**1,057**

Distinct mechanical C2 union:

**1,157**

Additional disjoint C3 structural shapes:

**195**

Full anchor reconciliation:

- C2 executable-mechanical in >=1 LTF: 1,157
- C2 source-valid but no PS: 245
- C3 shape from non-executable C2: 195
- neither: 10,058

Total: 11,655.

Profile union is diagnostic only; it is not authorized execution.

## 5.4 Post-anchor Protected Swing audit

Run:
`36058578818`

Among the 245 C2-valid / no-pre-anchor-PS cases:

- 130 formed a Protected Swing later inside the same H4;
- 115 never formed one.

These are not missing positional fills because confirmation occurred after the H4 open.

They are evidence that another source entry family may recover legitimate density.

## 5.5 Delayed continuation conservative bundle

Run:
`36059612077`

The ultra-conservative contract requiring FVG + CISD + PS with confirmation close inside a unique FVG produced only 3/130 eligible delayed anchors across the earlier residual set.

Conclusion:
too sparse; not a density solution.

## 5.6 Latest-confirmed Protected Swing

Run:
`35942191510`

Source adjudication allowed latest causally confirmed PS rather than “multiple PS -> universal abstain” for the diagnostic/latest-PS research line.

M3 consumed-development results:

| Market | Trades ~3Y | ~Trades/2Y | Raw PF | Total R | DD R |
|---|---:|---:|---:|---:|---:|
| EURJPY | 161 | 107.33 | 1.4746 | +39.00 | 7.00 |
| USDCHF | 149 | 99.33 | 0.9479 | -4.61 | 15.39 |
| NZDUSD | 182 | 121.33 | 0.9469 | -5.49 | 20.19 |
| CADJPY | 161 | 107.33 | 1.0555 | +4.79 | 18.88 |
| USDCAD | 159 | 106.00 | 1.0599 | +5.37 | 20.36 |

Owner feedback:
still too little density for the intended trader.

Do not promote this line as density-resolved.

## 5.7 Latest-PS + existing Core Stack

Run:
`36077923826`

M3 raw -> managed:

| Market | Trades | Raw PF | Managed PF | Raw DD | Managed DD | Key result |
|---|---:|---:|---:|---:|---:|---|
| EURJPY | 161 | 1.4746 | 1.4881 | 7.00 | 7.26 | PF flat, total R worsened |
| USDCHF | 149 | 0.9479 | 1.0045 | 15.39 | 8.52 | strong DD reduction |
| NZDUSD | 182 | 0.9469 | 1.1613 | 20.19 | 9.19 | major rescue, still below target PF |
| CADJPY | 161 | 1.0555 | 1.4128 | 18.88 | 7.47 | major improvement |
| USDCAD | 159 | 1.0599 | 0.9529 | 20.36 | 13.48 | DD better, PF damaged |

Conclusion:
Core Stack is not a universal certification solution.

## 5.8 Management attribution

Run:
`36078305720`

Bank-only M3 results included:

- EURJPY PF ~1.613, DD ~5.52R
- USDCHF PF ~0.959
- NZDUSD PF ~0.924
- CADJPY PF ~1.216
- USDCAD PF ~0.998

Useful attribution, not a final global policy.

## 5.9 CIBO stop-only / cautious shield

Stop-only frontier:
run `36078501575` — technically successful research.

Cautious-state shield:
run `36078689608`.

All five markets failed the promotion decision for the cautious shield.

Do not resurrect it by changing thresholds post hoc.

## 5.10 Structural outcome and pairwise forensics

Runs:

- structural outcome forensics: `36078954926`
- pairwise structural forensics: `36079369540`

Purpose:
identify causal structural states on consumed development evidence.

Important governance:
forensics are hypothesis generators, not runtime rules.

Do not cherry-pick a favorable market-specific pairwise state and apply it directly to production.

## 5.11 Sealed seven-year archive

Run:
`36079229139`

Five-market M15/M3 archive collected successfully.

Freeze:
`docs/research/VT08_COGNITIVE_EXPANSION_5M_7Y_SEALED_ARCHIVE_FREEZE.md`

Rules:

- raw collection only;
- no strategy replay at collection;
- evidence at/after `2023-09-24T23:45:00Z` is consumed;
- future fresh validation must use signals/exits strictly before that cutoff;
- do not open/tune on the sealed older interval before candidate freeze.

---

# 6. Work performed in the latest continuation cycle

The following work was added after the prior pairwise/7Y checkpoint.

## 6.1 All-valid-owner-anchors frontier

Commit:
`0289b3b1181943ec32563957481561eb55be1ff7`

Workflow:
`QORE VT08 M3 All Valid Anchors Frontier V1`

Run:
`36176183179` — SUCCESS.

Purpose:
measure whether the current daily-candidate containment was suppressing density by dropping days with multiple valid Owner anchors.

Result:

- density increased only modestly, roughly +20 to +35 candidates/trades per market across ~3 years;
- EURJPY improved to ~189 trades and remained economically reasonable;
- several other markets deteriorated materially;
- NZDUSD increased to ~217 trades but PF dropped to ~0.88 and DD rose to ~25R;
- overall, retaining all anchors does not solve density + quality simultaneously.

Governance correction:

R3.2 current Owner policy still caps final filled trades at one per market/day. Therefore this frontier remains diagnostic; do not silently promote multi-fill/day execution.

## 6.2 Source-bound M3 continuation density census

Commit:
`5b63490123a2057137ef69d81869cda549bfd8d4`

Lint repair:
`6d2ca6a33f78b62f4c72093e70ae5c68147757d1`

Run:
`36176526008` — SUCCESS.

Frozen contract:

- same valid H4 cycle;
- new same-side CISD;
- new Protected Swing;
- causal FVG;
- sufficient structural room;
- no PnL used in counting.

Result:
only about 4–6 conservative continuation opportunities per market over ~3 years.

Conclusion:
this ultra-conservative continuation definition is too narrow to solve density.

## 6.3 Intracycle C2 density census

Commit:
`51cdc081f907855552eacd1efa2d658b148b5a6d`

Lint repair:
`5349cbb66adf677e1e41830c2ac95fd829e28375`

Run:
`36176920864` — SUCCESS.

Key conceptual change:
do not wait for the final completed H4 C2 close merely to count source-observable intracycle important-level run + CISD + Protected Swing structures.

No economics used.

Source-confirmed intracycle structures over ~3Y:

- EURJPY: 2,340
- USDCHF: 2,294
- NZDUSD: 2,042
- CADJPY: 2,162
- USDCAD: 2,327

Approximate source-structure 2Y equivalent:

- EURJPY ~1,560
- USDCHF ~1,529
- NZDUSD ~1,361
- CADJPY ~1,441
- USDCAD ~1,551

However the ultra-narrow “confirmation close inside one active FVG” subset was only:

- EURJPY: 5
- USDCHF: 10
- NZDUSD: 9
- CADJPY: 3
- USDCAD: 14

Critical conclusion:

> **The market is not lacking VT08 structural events. The density bottleneck is the executable entry contract.**

## 6.4 Causal M3 entry-geometry census

Commit:
`6020b487ad9e4e4eed0bb70a8955ac003a8a02c2`

Workflow:
`QORE VT08 M3 Entry Geometry Census V1`

Run:
`36177811605` — SUCCESS.

Main CI at the same SHA:
run `36177811524` — SUCCESS.

This census uses no terminal PnL and grants no entry authority.

It measures distinct NY days to respect the Owner one-fill/day ceiling.

### Source CISD + Protected Swing density

| Market | Raw source events ~3Y | Unique NY days ~3Y | 2Y-equivalent unique days |
|---|---:|---:|---:|
| EURJPY | 2,340 | 463 | ~308.67 |
| USDCHF | 2,294 | 490 | ~326.67 |
| NZDUSD | 2,042 | 458 | ~305.34 |
| CADJPY | 2,162 | 452 | ~301.34 |
| USDCAD | 2,327 | 502 | ~334.67 |

This is the first evidence showing density in the intended general region while preserving max one fill/day as an upper-bound diagnostic.

### Later causal CISD-level retest

| Market | Events | Unique NY days | 2Y-equivalent unique days |
|---|---:|---:|---:|
| EURJPY | 2,041 | 444 | ~296.00 |
| USDCHF | 1,981 | 466 | ~310.67 |
| NZDUSD | 1,773 | 437 | ~291.34 |
| CADJPY | 1,898 | 437 | ~291.34 |
| USDCAD | 1,997 | 477 | ~318.00 |

### Active pre-confirmation FVG present

2Y-equivalent unique-day density:

- EURJPY ~211.34
- USDCHF ~212.67
- NZDUSD ~190.00
- CADJPY ~185.34
- USDCAD ~211.34

### Later FVG retest

2Y-equivalent unique-day density:

- EURJPY ~163.33
- USDCHF ~172.00
- NZDUSD ~142.67
- CADJPY ~146.67
- USDCAD ~163.33

### Confirmation close inside active FVG

This remains extremely sparse:

- EURJPY: 5 unique days
- USDCHF: 9
- NZDUSD: 9
- CADJPY: 2
- USDCAD: 10

Conclusion:

> Requiring the confirmation close itself to remain inside a unique active FVG is not a plausible universal density contract for this expansion. CISD + Protected Swing structures are abundant; FVG-close-at-confirmation is the severe narrowing condition.

This conclusion is diagnostic only. It does **not** authorize CISD retest as an entry.

---

# 7. Current scientific interpretation

## 7.1 Density is not fundamentally missing

The earlier 149–182 trades per market / ~3Y created the impression that VT08 simply does not generate enough opportunities.

The intracycle and entry-geometry censuses falsify that interpretation.

There are roughly 452–502 NY dates per market over ~3 years with at least one source-observable CISD + Protected Swing event.

Equivalent upper-bound density is approximately 301–335 unique opportunity days per 2Y depending on market.

Therefore the core research question is now:

> Which source-supported non-positional entry family legitimately converts a useful subset of those causal structures into executable trades while preserving PF/DD?

## 7.2 FVG cannot be assumed universal

FVG remains a source-supported contextual POI concept, but the current evidence shows that the narrow requirement “confirmation close inside one causal FVG” collapses density.

Do not respond by deleting FVG arbitrarily.

Instead:

- recover exact primary-source/framebook provenance for reversal/continuation/confident/open/POI-continuation;
- determine which families require FVG, which permit another POI/retest, and at what causal decision time;
- freeze one provenance-bound bundle before PnL.

## 7.3 CISD-level retest is a high-density geometry, not yet an authorized entry

The new census finds roughly 291–318 unique retest days / 2Y.

This is a research lead only.

The next architect must not simply declare “enter on CISD retest” because it looks dense. First prove from primary/official source material which entry family, if any, authorizes that exact execution geometry.

## 7.4 Do not use outcomes to select the entry family

No:

- best-PF family;
- best-market family;
- best-anchor family;
- optimized retest distance;
- optimized latency;
- optimized FVG count;
- optimized wick/body threshold.

Methodology first, code second, economics third.

---

# 8. Certification status

**NOT CERTIFIED.**

PR #634 remains research-only.

## 8.1 Existing pre-registered economic gates

The original expansion freeze records:

- PF >= 1.80;
- observed DD <= 6R;
- mean R >= 0;
- MC p95 DD <= 15R;
- MC positive terminal >= 0.90;
- anchor stability required;
- temporal validation required;
- stress required;
- Monte Carlo required.

The original minimum 50 trades / 2Y gate is explicitly retired by Owner rejection.

## 8.2 Density gate blocker

A replacement numeric density acceptance gate has **not** yet been formally frozen.

Owner qualitative requirement is clear:

- ~160 trades / 3Y per market is insufficient.

Do not invent a final numeric gate in the handoff.

The next architect should freeze an Owner-approved numeric density gate **before** evaluating the final candidate economics.

The new geometry census demonstrates that ~300+ unique source-structure days / 2Y are available as an upper-bound reservoir, but that does not mean the final executable strategy must or will trade all of them.

## 8.3 Full-cognitive replay blocker — P0

Before certification, build a replay in which the complete Cognitive V1 stack actually governs the trade lifecycle.

Required proof:

- 100% of admitted trades have a Situation Model fingerprint;
- 100% have a Reasoning decision;
- 100% have Hypothesis Lifecycle provenance;
- ABSTAIN cannot execute through fallback;
- WAIT cannot be treated as automatic rejection if the hypothesis remains alive;
- rearm requires new source identity;
- after fill, Journey/Position Intelligence decisions are logged;
- no future information;
- no terminal PnL in runtime features;
- no runtime self-training.

Certification of “Cognitive VT08” is impossible without this binding.

## 8.4 Entry-family blocker — P0

Only positional-entry is machine-complete.

The high-density intracycle reservoir cannot become economic trades until one non-positional source bundle is machine-complete.

Required fields:

- exact source family;
- causal trigger;
- decision timestamp;
- executable price or entry zone;
- POI semantics;
- compatible stop family;
- stop price semantics;
- target family;
- target priority;
- H4 lifecycle behavior;
- daily selection behavior;
- ambiguity handling;
- provenance references.

## 8.5 C3 blocker

C3 is source-authorized but not machine-complete in the current expansion line.

Existing C3 positional eligibility was only 7/195 for the narrow conservative path.

Do not claim C3 solved.

A new C3 implementation needs source-first pre-registration.

## 8.6 Multiple-PS / both-side-sweep / source-day ambiguity

Still not universally source-resolved:

- deterministic selection among multiple PS;
- both-side-sweep machine rule;
- exact source-day convention;
- re-entry/cardinality source authority;
- deterministic target priority;
- stop offset;
- exact filled-position lifecycle.

Any experimental formalization must be labeled QORE/Owner formalization and separately versioned.

## 8.7 Sealed validation blocker

The 7Y archive exists and remains the future unseen validation reservoir.

Do not open older sealed outcomes while tuning.

Required sequence:

1. close methodology/source bundle;
2. bind full cognition;
3. freeze candidate identity/fingerprint;
4. freeze density gate and economic gates;
5. only then run on the sealed pre-cutoff evidence;
6. no modification after seeing holdout without retiring the candidate and creating a new identity.

---

# 9. Mandatory next work — ordered plan

## P0-A — Make cognition sovereign in replay

Create a dedicated `VT08_COGNITIVE_EXPANSION_FULL_COGNITIVE_REPLAY_V1` or equivalent clearly versioned research path.

Do not modify the old raw baseline in place.

For every candidate:

- build Situation Model;
- bind memory;
- call Cognitive Orchestrator;
- retain decision ledger;
- preserve counterfactual “methodology-only candidate” identity;
- prove cardinality;
- prove no fallback after ABSTAIN;
- prove new-source rearm.

For every open position:

- causal journey updates;
- Position Intelligence;
- stop monotonicity proof;
- no uncalibrated reduce/protect rule promoted silently.

## P0-B — Source-close one high-density entry family

Priority question from current evidence:

Can source-authorized reversal / continuation / open / confident / POI-continuation semantics use the causal CISD+PS state or later CISD/POI retest without requiring confirmation-close-inside-FVG?

Required research sources:

- primary video/framebook;
- exact timestamps/examples;
- later official TTrades material where provenance is clear;
- PR #518 source trace only as forensic aid, never its economics;
- PR #520 R3.2 source kernel identities.

Output:

- source authority report;
- ambiguity table;
- one machine-complete `VT08SourceBundle`;
- no PnL.

## P0-C — Freeze final density acceptance

Owner must approve a replacement for retired 50/2Y.

The gate must be frozen before final candidate outcome review.

Report:

- trades per market;
- trades/year;
- 2Y equivalent;
- unique NY dates;
- aggregate portfolio density;
- no duplicate profile counting.

## P1 — Consumed-development economic replay

Only after P0-A/P0-B:

- all five markets;
- one global frozen contract;
- no market filtering;
- no anchor filtering;
- no side filtering unless source/Owner authority predates outcomes;
- equal-risk PF as methodology truth;
- managed-R separately;
- capital weighting separately and never mislabeled.

Compare:

1. raw methodology-only baseline;
2. source-complete candidate without cognitive gating;
3. full cognitive candidate;
4. management variants only if pre-frozen.

Measure:

- trades;
- PF;
- total R;
- DD;
- mean R;
- win rate;
- losing streak;
- annual blocks;
- anchor stability;
- side stability;
- market stability;
- false cognitive abstention;
- cognition-rescued bad entries;
- cognition-killed winners;
- WAIT resolution;
- rearm density;
- journey/position contribution.

## P1 — Temporal and causal falsification

Before sealed holdout:

- chronological block stability;
- walk-forward;
- no-lookahead tests;
- date-shuffle / forbidden oracle adversarial tests;
- memory provenance audit;
- hypothesis-source identity audit;
- leave-one-market-out robustness;
- anchor decomposition;
- side decomposition;
- spread/friction stress if execution modeling is introduced.

## P2 — Sealed 7Y validation

Use only the frozen candidate.

Fresh/older validation data must obey the existing cutoff:
signals/exits strictly before `2023-09-24T23:45:00Z`.

Run:

- exact candidate unchanged;
- temporal windows;
- stress;
- MC/block bootstrap;
- density;
- PF;
- DD;
- MC p95 DD;
- probability positive terminal;
- annual/market/anchor stability.

If it fails, candidate is falsified. Do not tune against the sealed result.

## P3 — Certification decision

Certification requires all gates simultaneously.

No “aggregate strong” result can hide:

- weak per-market density;
- high DD;
- PF below gate;
- unstable years;
- cognitive bypass;
- leakage;
- market-specific cherry-picking.

Only after certification may a separate integration/live authorization process begin.

---

# 10. Explicit prohibitions for the next architect

Do not:

- merge PR #634 merely because CI is green;
- call the trader certified;
- wire to live capital;
- modify VPS/runtime from this research handoff;
- use capital weighting to report raw PF;
- combine M15/M5/M3 after outcomes;
- choose best market/anchor/side after PnL;
- optimize source ambiguity from PnL;
- invent shallow/large numeric thresholds;
- widen stops retrospectively;
- resurrect cautious shield without a new causal hypothesis;
- treat pairwise forensics as production rules;
- open sealed 7Y outcome evidence before candidate freeze;
- claim cognitive performance while bypassing Cognitive Orchestrator;
- let ABSTAIN be overridden by a fallback route;
- self-train cognition from realized runtime PnL.

---

# 11. Important files for continuity

## Cognitive architecture

- `docs/research/VT08_FOREX_COGNITIVE_V1_ARCHITECTURE_FREEZE.md`
- `docs/research/VT08_FOREX_COGNITIVE_V1_JOURNEY_POSITION.md`
- `docs/research/VT08_FOREX_COGNITIVE_V1_MEMORY_BINDING.md`
- `src/qore/infrastructure/traders/vt08_cognitive_v1_contracts.py`
- `src/qore/infrastructure/traders/vt08_cognitive_strategy_identity_memory.py`
- `src/qore/infrastructure/traders/vt08_cognitive_cibo_market_memory.py`
- `src/qore/infrastructure/traders/vt08_cognitive_trader_experience_memory.py`
- `src/qore/infrastructure/traders/vt08_cognitive_memory.py`
- `src/qore/infrastructure/traders/vt08_cognitive_situation_model.py`
- `src/qore/infrastructure/traders/vt08_cognitive_hypothesis.py`
- `src/qore/infrastructure/traders/vt08_cognitive_reasoning.py`
- `src/qore/infrastructure/traders/vt08_cognitive_journey_intelligence.py`
- `src/qore/infrastructure/traders/vt08_cognitive_position_intelligence.py`
- `src/qore/infrastructure/traders/vt08_cognitive_orchestrator.py`

## Source/methodology

- `src/qore/infrastructure/traders/vt08_source_kernel_r3_2.py`
- `src/qore/infrastructure/traders/vt08_b01_source_contract_r3_9.py`
- `src/qore/infrastructure/traders/vt08_b01_r3_8.py`
- `docs/research/trader-lab/VT08-R3-2-SOURCE-FREEZE.md`
- `docs/research/trader-lab/VT08-R3-2-AMBIGUITY-REGISTER.md`
- `docs/research/trader-lab/VT08-R3-9-FINAL-SOURCE-CONTRACT.md`
- `docs/research/VT08-CRT-H4-AMD-V2-SOURCE-FREEZE.md`

## Expansion / density

- `docs/research/VT08_COGNITIVE_EXPANSION_5M_V1_FREEZE.md`
- `docs/research/VT08_COGNITIVE_EXPANSION_5M_OWNER_REJECTION_DENSITY_PF_TRUTH.md`
- `docs/research/VT08_COGNITIVE_EXPANSION_5M_THREE_YEAR_OPPORTUNITY_CENSUS_MASTER_REPORT.md`
- `docs/research/VT08_COGNITIVE_POST_ANCHOR_PS_ENTRY_FAMILY_AUTHORITY_REPORT.md`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_entry_family_authority_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_latest_ps_density_recovery_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_intracycle_c2_density_census_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_entry_geometry_census_v1.py`

## Economic / management labs

- `src/qore/infrastructure/trader_lab/vt08_cognitive_latest_ps_core_stack_frontier_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_management_attribution_frontier_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_cibo_stop_only_frontier_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_cautious_state_shield_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_structural_outcome_forensics_v1.py`
- `src/qore/infrastructure/trader_lab/vt08_cognitive_m3_pairwise_structural_forensics_v1.py`

## Sealed evidence

- `docs/research/VT08_COGNITIVE_EXPANSION_5M_7Y_SEALED_ARCHIVE_FREEZE.md`
- workflow run `36079229139`

---

# 12. Key workflow/run ledger

- `35934924907` — immutable ~1095d five-market base evidence.
- `35938734279` — five-market equal-risk/PF truth audit.
- `35941643396` — exact-window M3 evidence.
- `35942191510` — latest-confirmed PS density/economics.
- `36057198230` — three-year opportunity census.
- `36057627121` — residual reconciliation.
- `36058018066` — no-PS forensics.
- `36058578818` — post-anchor PS census.
- `36059612077` — delayed conservative continuation bundle eligibility.
- `36077923826` — latest-PS Core Stack frontier.
- `36078305720` — M3 management attribution.
- `36078501575` — M3 CIBO stop-only frontier.
- `36078689608` — cautious-state shield; rejected.
- `36078954926` — M3 structural outcome forensics.
- `36079229139` — five-market 7Y sealed archive acquisition.
- `36079369540` — M3 pairwise structural forensics.
- `36176183179` — M3 all-valid-anchor frontier.
- `36176526008` — source-bound M3 continuation density census.
- `36176920864` — M3 intracycle C2 density census.
- `36177811605` — M3 causal entry-geometry census.
- `36177811524` — main PR #634 CI at parent handoff SHA; SUCCESS.

---

# 13. Final handoff verdict

Current trader state:

`RESEARCH_ACTIVE / DENSITY_RESERVOIR_FOUND / ENTRY_AUTHORITY_INCOMPLETE / FULL_COGNITIVE_BINDING_INCOMPLETE / NOT_CERTIFIED`

What is solved:

- source lineage is clear;
- current narrow positional path is understood;
- density failure of the old line is proven;
- LTF opportunity census is reconciled;
- C3 and delayed-PS structural reservoirs are mapped;
- M3 latest-PS density/economics are known;
- Core Stack / management effects are measured;
- causal structural forensics exist;
- 7Y older archive is sealed;
- intracycle CISD+PS reservoir is now proven to be large;
- distinct-day density under one-fill/day can reach roughly 301–335 source-structure opportunity days / 2Y;
- CI is green at the parent handoff SHA.

What is **not** solved:

1. exact machine-complete high-density non-positional entry family;
2. full Cognitive V1 binding into every replay admission and in-trade decision;
3. new Owner-approved numeric density certification gate;
4. final PF/DD combination across all five markets;
5. C3 machine-complete implementation;
6. several source ambiguities;
7. sealed 7Y validation;
8. final WFO/MC/stress/temporal certification battery;
9. DEMO/LIVE/production authorization.

The next architect should start at **P0-A full cognitive binding** and **P0-B source-closing one high-density entry family**, not by launching another generic PF optimization.

SOURCE FIRST. COGNITION SOVEREIGN. DENSITY LEGITIMATE. HOLDOUT SEALED. CERTIFICATION ONLY AFTER ALL GATES.
