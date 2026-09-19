# VT08 CRT COGNITIVE ARCHITECTURE FREEZE 001

**Status:** FROZEN ARCHITECTURE / RESEARCH ONLY / NOT CERTIFIED  
**Repository:** `mezas3238-hue/qore-core`  
**Branch:** `agent/vt08-crt-cognitive-architecture-freeze-001`  
**Base:** `main@c98d486a760056d9a71173c7041cf6f0c58bd9e9`  
**Date:** 2026-09-19

## 0. Purpose

Freeze the architecture agreed by the Owner for the future VT08 CRT specialist before implementation, calibration, economic validation, certification, runtime integration, or VPS deployment.

This document is an architecture contract. It does **not** certify CRT, does **not** authorize DEMO/LIVE/real capital, and does **not** modify the currently deployed VT08.

The historical VT08 CRT lineage in PR #516 remains independent evidence and must not be rewritten by this freeze.

## 1. Intended VT08 topology

VT08 is intended to become a dual-strategy trader with two independent strategy/cognitive lineages:

- VT08-AMD — AMD methodology and AMD cognitive lineage.
- VT08-CRT — Candle Range Theory methodology and CRT cognitive lineage.

AMD and CRT must not share one undifferentiated strategy brain. They may consume governed shared market knowledge, but each must retain its own identity, experience, reasoning contract, evidence trail, certification and economic attribution.

This freeze covers **VT08-CRT only**.

## 2. Initial CRT market scope

The intended first CRT specialist market set is:

- AUDUSD
- USDJPY
- BTCUSD

The same CRT methodology may be implemented across these markets, but market-specific behavior and experience must remain separated.

Required specialist memories:

- CRT Experience Memory — AUDUSD
- CRT Experience Memory — USDJPY
- CRT Experience Memory — BTCUSD

No market-specific rule may be silently transferred from one market to another.

## 3. Architecture sources to reuse

The new CRT cognitive architecture must be constructed from governed QORE components and lessons already present in the repository.

### 3.1 VT31 cognitive architecture — primary brain model

Reference lineage: PR #610.

Reuse the architectural pattern:

1. Strategy / Identity Memory
2. CIBO Market Memory
3. Trader Experience / Lab Memory
4. Current Situation Model
5. Reasoning Engine
6. EXECUTE / WAIT / ABSTAIN decision
7. Position Intelligence

The CRT implementation must preserve the principle that persistent memories are immutable during runtime and that market/experience memory cannot silently rewrite methodology identity.

### 3.2 Turtle Soup specialist memory / regime / journey architecture

Reference lineages include PRs #608, #611, #614, #618 and certified runtime adapters.

Reuse concepts, not Turtle Soup entry rules:

- exact regime;
- causal core regime;
- anatomy regime;
- regime journey;
- specialist memory;
- route / destination intelligence;
- structural posture;
- causal target resolution;
- immutable memory binding and fingerprinting.

### 3.3 CIBO Market Atlas / Journey / Target Destination

Reuse governed market knowledge for:

- market journey;
- structural touch history;
- pre-departure sequence;
- target destination;
- departure timing;
- cross-market/cross-index context when causally relevant;
- afterlife diagnostics;
- regime/context characterization.

CIBO observations are context and routing intelligence. Association-only evidence must not become an automatic veto or execution permission.

### 3.4 VT08 Deep Behavior / Market Journey research

Reference lineage: PR #604.

Reuse the observation architecture for:

- pre-entry accumulation/balance;
- reaction structure;
- reaction timing;
- expansion latency;
- structural boundaries;
- target path;
- post-stop afterlife;
- weekday/regime context;
- divergence/context relationships.

These features must be treated as research evidence until independently promoted by a frozen candidate and unseen validation.

### 3.5 Historical VT08 CRT source-bound lineage

Reference lineage: PR #516.

PR #516 is historical CRT research evidence, not the final cognitive architecture.

Its source-bound concepts must be audited and may seed Strategy Identity Memory only after source adjudication. Its historical design includes:

- D1 context;
- H4 1/5/9 CRT hierarchy;
- H1 nested CRT;
- M15 nested CRT;
- liquidity sweep/re-entry;
- explicit structural invalidation;
- opposite-range destination;
- decision-time vs post-outcome evidence separation;
- abstention contracts;
- failure analysis and story forensics.

No economic result from PR #516 grants current certification or authority.

## 4. Frozen CRT cognitive topology

```text
                VT08 — CRT COGNITIVE
                         |
        +----------------+----------------+
        |                |                |
 CRT STRATEGY       CIBO MARKET      CRT EXPERIENCE
 IDENTITY MEMORY      MEMORY             MEMORY
        |                |                |
        +----------------+----------------+
                         |
                 SITUATION MODEL
                         |
                 CRT REASONING ENGINE
                         |
           +-------------+-------------+
           |             |             |
        EXECUTE          WAIT        ABSTAIN
           |             |             |
           |             |        hypothesis dies
           |             |
           +------ + -----+
                  |
           JOURNEY / DOL ENGINE
                  |
          POSITION INTELLIGENCE
                  |
                 CIBO
                  |
              QORE RISK
                  |
              EXECUTION
```

## 5. CRT Strategy / Identity Memory

This memory answers:

> What is CRT, what constitutes a valid CRT opportunity, and what methodology am I allowed to operate?

It must contain methodology identity only.

At minimum it must freeze definitions for:

- valid reference candle/range;
- CRH / CRL;
- equilibrium;
- valid sweep / liquidation;
- one-sided vs two-sided sweep;
- reclaim / close-back-inside semantics;
- acceptance outside the range;
- invalidation;
- higher-timeframe to lower-timeframe hierarchy;
- nested CRT semantics;
- temporal/session semantics if source-supported;
- authorized entry families;
- structural stop identity;
- structural destination identity;
- opportunity expiry;
- same-bar ambiguity policy;
- rearm identity.

Hard guards:

- CIBO Market Memory may not rewrite CRT methodology.
- Trader Experience Memory may not rewrite CRT methodology.
- terminal PnL may not rewrite CRT methodology.
- runtime learning may not mutate CRT identity.
- any methodology change creates a new candidate identity and requires fresh validation.

## 6. CIBO Market Memory

CIBO Market Memory answers:

> What does this market historically do?

It is distinct from CRT experience.

For each market it may retain governed aggregate knowledge about:

- range behavior;
- sweep behavior;
- journey progression;
- timing;
- liquidity consumption;
- destination availability;
- structural sequences;
- expansion/compression behavior;
- regime/context;
- post-boundary extension;
- historical target paths.

It must not provide date-level future answers, post-outcome oracle data, or lookahead.

## 7. CRT Trader Experience Memory

CRT Trader Experience Memory answers:

> What has this CRT methodology learned when interacting with this specific market?

There must be independent experience stores for AUDUSD, USDJPY and BTCUSD.

Examples of admissible learned diagnostics:

- setup anatomy;
- confirmation latency;
- sweep depth;
- reclaim quality;
- displacement quality;
- entry geometry;
- stop geometry;
- destination geometry;
- journey stage at entry;
- dead-on-arrival behavior;
- giveback after favorable excursion;
- post-stop afterlife;
- route instability;
- structural rearm quality.

Experience memory cannot self-train from live PnL and cannot silently promote a rule. Promotion requires a frozen research protocol and new validation.

## 8. Current CRT Situation Model

The Situation Model is ephemeral and causal. It represents only information observable at the current decision time.

Minimum target state:

- symbol;
- decision timestamp;
- active CRT reference candle;
- CRH;
- CRL;
- equilibrium;
- current price location;
- boundary attacked;
- sweep depth;
- sweep chronology;
- reclaim state;
- close-back-inside state;
- acceptance/rejection outside range;
- D1 context;
- H4 context;
- H1 context;
- M15 context;
- session/time context;
- range state;
- expansion/compression state;
- relevant liquidity consumed;
- relevant liquidity available;
- active structural destinations;
- distance to destination;
- confirmation latency;
- displacement state;
- structural invalidation state;
- uncertainty/missing-context flags;
- market-specific context.

No future bar, terminal outcome, future MFE/MAE, later target touch, or post-trade label may enter the live Situation Model.

## 9. CRT Reasoning Engine

The deterministic CRT Reasoning Engine combines:

- CRT Strategy Identity Memory;
- CIBO Market Memory;
- market-specific CRT Trader Experience Memory;
- current causal Situation Model.

Its only primary pre-entry decisions are:

- EXECUTE
- WAIT
- ABSTAIN

It must expose auditable:

- support evidence;
- contradictions;
- uncertainty;
- memory sections used;
- situation fingerprint;
- memory fingerprints;
- destination/management intent.

### 9.1 Reasoning sovereignty

Reasoning sovereignty is mandatory.

If the CRT Reasoning Engine returns ABSTAIN:

- the current hypothesis is dead;
- no secondary route may override the abstention;
- no fallback may reuse the same source event;
- no mechanical bypass may execute the rejected setup.

A later opportunity requires a genuinely new structural event, rebuilt Situation Model and new Reasoning decision.

WAIT keeps the current hypothesis observable but grants no execution authority until the reasoning state becomes EXECUTE under the frozen contract.

Every executable path, including rearm, must pass Reasoning sovereignty.

## 10. Journey / DOL Engine

CRT methodology defines the allowed destination family. CIBO/market intelligence may help resolve which authorized destination is active and still available.

The Journey / DOL layer may reason about:

- opposite CRT boundary;
- higher-timeframe structural destinations;
- active/untouched liquidity objectives;
- destination rank;
- distance;
- route;
- already-consumed destinations;
- expected journey stage.

It may not invent a target outside the frozen Strategy Identity contract.

Agreement between multiple cognitive signals does not automatically increase risk.

## 11. Position Intelligence

Position Intelligence is separate from entry cognition.

It may reason about:

- structural protection;
- conquered destination lock;
- protected stop progression;
- hold/trail decisions;
- giveback risk;
- journey completion;
- structural rearm.

Position management must be causally observable and separately validated.

No position intelligence rule may retroactively alter the certified initial trade thesis.

## 12. CIBO and QORE Risk sovereignty

The CRT cognitive has no independent capital authority.

Mandatory authority chain:

```text
CRT identifies and reasons
        |
CIBO evaluates operational posture / coordination
        |
QORE RISK decides capital authority
        |
Execution boundary
        |
Broker
```

The CRT cognitive may not:

- bypass QORE RISK;
- submit provider orders directly;
- choose unrestricted quantity;
- increase lot size because multiple signals agree;
- authorize LIVE/real capital;
- promote itself to production.

## 13. Deep cognition versus critical execution path

The repository already contains a hard real-time market-data architecture targeting a 2.0 second boundary SLA in PR #619.

Therefore the future CRT architecture must distinguish:

### Critical decision path

Local, deterministic and auditable components:

- current market data;
- Situation Model;
- frozen memories;
- CRT Reasoning Engine;
- Journey/DOL resolution;
- risk request construction.

The critical path must be compatible with the required execution SLA.

### Deep cognition path

Governed CIBO Cognitive / external reasoning may support:

- pre-session analysis;
- forensic investigation;
- contradiction review;
- hypothesis generation;
- memory research;
- adversarial/council review;
- architecture diagnostics.

Deep cognition is **not** allowed to become an uncontrolled latency dependency for a boundary-critical order.

Reference: merged CIBO Cognitive Runtime PR #491.

## 14. Per-market isolation

AUDUSD, USDJPY and BTCUSD must share architecture, not blindly share learned behavior.

Required principle:

```text
CRT Identity = common methodology contract

AUDUSD Experience != USDJPY Experience != BTCUSD Experience
```

Market-specific parameters or learned contexts require independent evidence.

BTCUSD must not inherit FX session/week structure without explicit evidence. AUDUSD/USDJPY must not inherit BTCUSD continuous-weekend behavior.

## 15. Certification model

Certification must occur in layers.

### Layer A — methodology/source certification

Verify that the implemented CRT identity is source-faithful and deterministic.

### Layer B — per-market CRT specialist certification

Independently evaluate:

- VT08_CRT_AUDUSD
- VT08_CRT_USDJPY
- VT08_CRT_BTCUSD

Each must have its own evidence, metrics, stress, walk-forward/temporal robustness, Monte Carlo, losing-streak analysis, drawdown analysis, yearly stability and unseen holdout.

A failed market does not become certified because another market performs well.

### Layer C — combined CRT portfolio certification

Replay all certified CRT markets in one chronological capital sequence with true simultaneous exposure, conflicts, concentration and QORE Risk behavior.

### Layer D — future VT08 dual-cognitive certification

Only after AMD and CRT are independently certified may the combined VT08 organism be certified:

- AMD cognitive lineage;
- CRT cognitive lineage;
- coordinator/conflict behavior;
- CIBO;
- QORE RISK;
- chronological combined portfolio economics.

Individual certification does not automatically certify the combined organism.

## 16. Research and anti-leakage governance

Mandatory:

- source freeze before economic tuning;
- decision-time/post-outcome separation;
- no lookahead;
- consumed evidence remains consumed;
- no consumed period may be relabeled fresh;
- no target-count fitting;
- no retrospective policy selection from a holdout;
- no silent methodology mutation after holdout access;
- any material rule change creates a new candidate identity;
- genuinely unseen evidence is required for final promotion.

## 17. Historical references

This architecture freeze intentionally references, without modifying:

- PR #491 — governed CIBO cognitive reasoning runtime;
- PR #516 — historical VT08 CRT 1-5-9 V3 source-bound research;
- PR #604 — VT08 Index Deep Behavior + Market Journey Atlas;
- PR #608 — Turtle Soup XAUUSD CIBO Journey Router;
- PR #610 — VT31 NAS100 Intelligence Pilot;
- PR #611 — Turtle Soup GBPUSD specialist memory;
- PR #614 — Turtle Soup GBPJPY Cognitive V3 / R28;
- PR #618 — Turtle Soup AUDJPY specialist memory;
- PR #619 — QORE realtime MT5 market sync hard 2s SLA.

These references are architecture/research inputs only. Their economic outcomes are not silently transferred into CRT certification.

## 18. Frozen invariants

The following are frozen by Owner direction unless explicitly reopened:

1. VT08 will retain AMD and CRT as separate strategy/cognitive lineages.
2. This contract governs CRT only.
3. Initial intended CRT markets are AUDUSD, USDJPY and BTCUSD.
4. CRT uses the VT31-style cognitive brain architecture.
5. CRT uses CIBO/Turtle-style specialist market journey and destination intelligence.
6. CRT uses separate market-specific Trader Experience Memory.
7. CRT Situation Model is causal and ephemeral.
8. CRT Reasoning decisions are EXECUTE / WAIT / ABSTAIN.
9. ABSTAIN cannot be overridden by fallback/secondary execution.
10. New execution after ABSTAIN requires a genuinely new structural event and rebuilt reasoning.
11. Journey/DOL and Position Intelligence are separate governed layers.
12. Deep external cognition is not the boundary-critical execution dependency.
13. CIBO and QORE RISK retain authority separation.
14. PR #516 is preserved as historical CRT evidence and must not be overwritten.
15. No current trader, VPS runtime, live authorization or real-capital state is modified by this architecture freeze.

## 19. Current authority state

- ARCHITECTURE_FROZEN = TRUE
- IMPLEMENTATION_STARTED = FALSE
- SOURCE_ADJUDICATION_COMPLETE = FALSE
- CRT_CANDIDATE_FROZEN = FALSE
- CRT_CERTIFIED = FALSE
- VT08_DUAL_COGNITIVE_CERTIFIED = FALSE
- DEMO_AUTHORIZED_BY_THIS_FREEZE = FALSE
- LIVE_AUTHORIZED_BY_THIS_FREEZE = FALSE
- REAL_CAPITAL_AUTHORIZED_BY_THIS_FREEZE = FALSE
- PRODUCTION_AUTHORIZED_BY_THIS_FREEZE = FALSE
- VPS_MUTATED_BY_THIS_FREEZE = FALSE

The next implementation phase must begin from this contract rather than redesigning the architecture implicitly.
