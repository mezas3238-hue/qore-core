# QORE CORE STACK V2 SUPERINTELLIGENCE — OWNER FREEZE 001

Status: **OWNER-FROZEN / RESEARCH / SHADOW ONLY**  
Owner: Sergio  
Repository: `mezas3238-hue/qore-core`  
PR: #635  
Machine-readable contract:
`src/qore/infrastructure/core_stack_v2/architecture_freeze.py`

## 1. Objective

Shared Core V2 is not a universal strategy and not a simple filter. It is the
shared causal market-intelligence layer of QORE.

Its purpose is to improve the quality of specialist traders materially while
preserving each trader's methodology.

```text
MARKET / CIBO
      ↓
SHARED CORE V2 SUPERINTELLIGENCE
      ↓
COGNITIVE ADAPTER
      ↓
TRADER COGNITION
      ↓
TRADER METHODOLOGY
      ↓
QORE RISK
      ↓
EXECUTION
```

Intelligence does not imply authority.

## 2. Frozen intelligence capabilities

Shared Core V2 must preserve all of these capabilities:

1. Perception Integrity.
2. Historical Causal Market Memory.
3. Deep Market World Model.
4. Regime and transition intelligence.
5. Attention and change detection.
6. Hypothesis Ensemble.
7. Uncertainty and Metacognition.
8. Global Cross-Market Intelligence.
9. Opportunity Suitability by Trader.
10. Failure and Counterfactual Memory.
11. Position Journey and Economic Attribution.

Removing one of these is an architectural change, not an implementation detail.

## 3. Global Market Universe — REQUIRED

`GLOBAL_MARKET_UNIVERSE_REQUIRED = TRUE`.

Shared Core must not own a fixed symbol allowlist.

It consumes the QORE market universe dynamically:

- `ExecutiveMarketsReadModel` supplies concrete provider-neutral markets;
- `InstrumentUniverseRegistrySnapshot` supplies canonical instrument-family
  coverage and semantic context.

Every market present in the QORE projection is retained as Shared Core
knowledge. This includes markets that are:

- available;
- restricted;
- unavailable;
- authorized;
- blocked;
- unknown.

A market can therefore contribute to global context without being tradable.

The architecture must be able to absorb future Forex, indices, futures, crypto,
metals, commodities, synthetics or other QORE-supported families without a
Shared Core symbol-list rewrite.

```text
KNOWLEDGE OF MARKET != PERMISSION TO TRADE MARKET
MARKET CONTEXT != TRADER SIGNAL
CROSS-MARKET CONFIRMATION != UNIVERSAL ENTRY CONDITION
```

## 4. CIBO relationship

CIBO and Shared Core are complementary.

CIBO may provide governed historical market knowledge, structure, memory,
research evidence and specialist intelligence.

Shared Core transforms governed causal evidence into a shared current situation:

- what is happening;
- what changed;
- which regimes are active or transitioning;
- which hypotheses are supported or contradicted;
- how certain the system is;
- how the active market relates to the rest of the QORE universe;
- which historical closed situations are causally analogous;
- which known failure anatomies are present;
- which opportunity characteristics may matter to each specialist.

Shared Core does not claim that CIBO opinion makes a market fact true.

## 5. Shared facts / separate interpretation

Frozen law:

```text
SHARED FACTS
SEPARATE SPECIALIST INTERPRETATION
```

The same `CoreSnapshot` may be delivered to multiple traders. Each adapter
translates only the context relevant to its trader.

Shared Core cannot rewrite:

- setup definition;
- entry;
- stop;
- target;
- rearm;
- trader-specific DOL semantics;
- trader-specific market memory;
- specialist risk policy;
- methodology.

## 6. Historical causal memory

Shared Core may learn from completed historical episodes.

For an event under evaluation at time T, only facts that existed at or before T
may enter the runtime situation.

Historical outcomes may be used to build already-frozen knowledge about prior
episodes, but the current event's future path, terminal PnL, MFE/MAE, future
journey label, calendar/fold identity as an edge feature, or later bars cannot
be inputs to the current decision.

```text
PAST CLOSED EPISODES = ALLOWED KNOWLEDGE
CURRENT EPISODE FUTURE = FORBIDDEN
```

## 7. Opportunity intelligence

Shared Core may estimate contextual suitability separately for each trader.

Example:

```text
NAS100 CURRENT SITUATION
        ↓
GLOBAL CORE KNOWLEDGE
        ↓
VT31 SUITABILITY CONTEXT
        ↓
VT31 ADAPTER
        ↓
VT31 COGNITION + VT31 METHODOLOGY
```

Shared Core never emits a universal BUY/SELL instruction.

## 8. Failure and counterfactual intelligence

Shared Core should learn causal pre-decision anatomies associated with:

- loss clusters;
- adverse excursion;
- false expansion;
- failed continuation;
- failed reversal;
- excessive uncertainty;
- contradiction;
- bad cross-market alignment;
- duplicated portfolio factor exposure.

Research may compare EXECUTE / WAIT / ABSTAIN / specialist-permitted management
counterfactuals. Counterfactual analysis is laboratory evidence, never order
authority.

## 9. Position intelligence

After a specialist opens a position, Shared Core may continue to describe:

- expansion;
- compression;
- contradiction;
- target/liquidity progress;
- opposite displacement;
- volatility transition;
- global market context.

Frozen invariant:

```text
STOP CAN IMPROVE OR HOLD
STOP CANNOT WIDEN
NO FUTURE
```

Specialist position-management logic remains specialist-owned.

## 10. Metacognition

Shared Core must preserve explicit epistemic states:

- I_KNOW;
- I_THINK;
- I_AM_UNCERTAIN;
- EVIDENCE_CONFLICTS;
- DATA_IS_INSUFFICIENT.

WAIT and ABSTAIN are valid cognitive states, not errors.

## 11. VT31 benchmark after Shared Core V2 completion

Reference certified trader:

`VT31_NAS100_STRUCTURAL_TARGET_V1`

5Y certified reference:

- trades: 806;
- PF: 3.736184576983536;
- total: +68.4017921123R;
- mean: +0.0848657470R/trade;
- observed DD: 3.7089849073R;
- max losing streak: 11;
- MC positive terminal: 99.98%;
- MC p95 DD: 6.3348648310R;
- MC p99 DD: 8.1518108457R.

Parity remains required as an engineering safety gate, but **parity is not the
economic objective**.

After Shared Core V2 is complete, VT31 becomes the first economic benchmark.

The research objective is material, robust improvement across:

- Profit Factor;
- total R;
- mean R/trade;
- observed drawdown;
- losing streak;
- Monte Carlo drawdown;
- positive-terminal probability;
- temporal stability;
- regime stability;
- WAIT quality;
- ABSTAIN quality;
- losses avoided;
- winners sacrificed;
- retained trade density;
- latency.

No uplift claim is valid if it depends on future leakage, fold identity,
calendar identity as an edge feature, retrospective cherry-picking, or Core
silently mutating VT31 methodology.

## 12. Governance freeze

```text
CORE_STACK_V2_RESEARCH_AUTHORIZED = TRUE
GLOBAL_MARKET_UNIVERSE_REQUIRED = TRUE
SHARED_CORE_MODEL = REQUIRED
ADAPTER_MODEL = REQUIRED
TRADER_METHODOLOGY_MUTATION = FALSE
QORE_RISK_SOVEREIGN = TRUE
VT08_FOREX_INTEGRATION = FALSE
VT08_FOREX = EXCLUDED
CAPITALIZER = DEFERRED_UNTIL_FINAL_FROZEN
SHADOW_FIRST = TRUE
LIVE_DEPLOYMENT_AUTHORIZED = FALSE
PRODUCTION_AUTHORIZED = FALSE
REAL_CAPITAL_AUTHORIZED = FALSE
MERGE_AUTHORIZED = FALSE
```

Any material alteration requires an explicit Owner-authorized versioned
architecture change.
