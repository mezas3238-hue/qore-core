# QORE Shared — Owner Cognitive OS Directive 004

**Status:** frozen architectural direction  
**Program:** `QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_004`  
**Primary PR:** #635  
**Master program:** #638  
**Work-package sequence:** #639 → #650 remains unchanged.

## Identity

QORE Shared is the **Cognitive + Scientific + Epistemic Operating System of
QORE Core**.

It is not a trader, not a hidden strategy, not a risk engine, not a capital
allocator and not an execution engine.

Shared exists to maintain the best currently justifiable representation of:

- market reality;
- QORE Core reality;
- cognitive reality;
- uncertainty and unknowns;
- scientific knowledge;
- its own model limitations and cognitive failures.

The central question is not “what will price do?” or “how do I increase PF?”.
It is:

> What is the best currently justifiable representation of QORE and market
> reality; what is observed, inferred, unknown or contradictory; what could
> falsify the current theory; what information is missing; and what should be
> investigated next?

## Cognitive Firewall

Shared is read-only by default.

Allowed cognitive verbs:

`observe · infer · explain · compare · simulate · remember · hypothesize ·
falsify · research · communicate`

Forbidden Shared authorities:

`order_send · position_close · modify_stop · modify_tp · position_size ·
capital_allocate · risk_authorize · trade_block · trade_force`

Sovereignty:

```text
REAL WORLD
    ↓
SHARED BRAIN
    ↓
COGNITIVE ADAPTER
    ↓
SOVEREIGN TRADER
    ↓
CIBO
    ↓
QORE RISK
    ↓
EXECUTION
    ↓
BROKER
```

The trader owns methodology. CIBO owns allocation/sizing. QORE Risk owns
capital-risk authorization. Execution alone mutates broker state.

## Three simultaneous realities

### Market Reality

Price, ticks, OHLC, volume, spread, depth/order flow when available,
volatility, liquidity proxies, sessions, cross-market relations, rates,
indices, FX, commodities, crypto, macro events, market structure, trajectory
and regime.

### Core Reality

Feeds, freshness, latency, broker connectivity, runtime/process health, clock
drift, data gaps, symbol mapping, broker conditions, execution quality,
slippage, rejections, Risk state, capital state, telemetry integrity and model
versions.

### Cognitive Reality

Shared hypotheses/uncertainty, trader observations, CIBO conditions, Risk
constraints, experimental/validated/certified knowledge, model disagreement
and explicit unknowns.

Shared must distinguish market anomalies from system, data or broker anomalies.

## Digital twins

Shared maintains both:

- **Probabilistic Market Digital Twin**
- **QORE Core Digital Twin**

Inferred state may never masquerade as observation. Every inferred field must
carry value, confidence, supporting evidence, contradictory evidence, age,
source and quality.

## Hierarchical temporal cognition

Required levels include tick/sub-second/seconds, M1, M3, M5, M15, H1, H4,
D1, session/day/week and macro regime.

Each level owns state, transition model, uncertainty, causal relations,
prediction error and memory.

The hierarchy must reason bottom-up, top-down, cross-scale, delayed and
cross-market.

**Local opposition is never sufficient evidence of higher-timeframe reversal.**

## Federation of Worlds and Unknown World

World families include momentum, liquidity/auction, mean reversion,
event/dislocation, inventory, reflexive/crowding and
`UNKNOWN_UNEXPLAINED`.

Unknown World is first-class. Shared must not force novel reality into a known
world merely to avoid abstention.

## Latent state, agency and reflexivity

Latent states and agency mechanisms are probabilistic hypotheses, never
unobserved actor identities stated as facts.

Shared studies mechanisms such as aggressive/passive flow, forced liquidation,
short covering, rebalancing, crowding, self-reinforcement and reflexive
exhaustion.

## Causality and predictive coding

Causal grades:

`ASSOCIATION → TEMPORAL_DEPENDENCY → CAUSAL_CANDIDATE →
FALSIFICATION_SURVIVED → REPLICATED → TRANSPORTABLE → CERTIFIED`

Every causal edge preserves provenance, markets, regimes, dates, sample
coverage, experiments, failed experiments, known confounders and
transportability limits.

Every major hypothesis must predict what should be observed next. Prediction
error is cognitive evidence.

## Negative Evidence, Active Perception and Value of Information

Shared must explicitly represent “expected but absent” evidence.

Active Perception asks which observation best discriminates competing
hypotheses.

Value of Information prioritizes observations by expected reduction in
decision-relevant uncertainty.

## Beliefs and uncertainty

Shared maintains distributions over competing hypotheses, never one mandatory
story.

Uncertainty is decomposed into aleatoric, epistemic, model disagreement, data,
regime, causal and simulation uncertainty.

Market randomness must not be mislabeled as model ignorance, and model
ignorance must not be hidden behind “market randomness”.

## Memory and knowledge

Shared requires:

- episodic market memory;
- semantic memory;
- cognitive failure memory;
- knowledge half-life;
- knowledge transportability;
- invariant discovery;
- provenance and rollback.

Knowledge stores are separated into certified, adaptive and experimental
knowledge.

## Representation and ontology evolution

Human ontology is not the ceiling.

Shared may discover latent concepts and, after governed validation, propose:
split, merge, create or retire concepts.

Ontology changes may never self-promote to production.

## Graph, transitions, journey and irreversibility

Shared maintains a dynamic market graph with leader/follower, decoupling,
contagion, correlation breakdown and causal-propagation relations.

It studies critical-transition warnings, market journeys, recovery probability
and effective irreversibility.

Normal adversity, recoverable deterioration, metastable deterioration,
critical transition and structural failure are distinct states.

## Counterfactuals and simulation fidelity

Counterfactuals are conditional scenario families, not point predictions.

Simulation must be tested against path distributions, volatility clustering,
tails, transition frequency, regime persistence, cross-market dependencies and
spread dynamics.

## Scientific Society and Cognitive Arbitration

Internal specialists include liquidity, structure, volatility, cross-market,
regime, trajectory, causality, anomaly, agency, macro-time, infrastructure,
broker and epistemics.

Simple majority voting is forbidden.

Arbitration weights specialists by calibration, current-regime competence,
OOD, evidence quality, recent prediction error and relevance.

Every strong hypothesis gets adversarial treatment:
`DEFENDER · PROSECUTOR · SKEPTIC`.

## Self-model, meta-reasoning and computation economy

Shared maintains a self-model of the models it relies on, their strengths,
weaknesses, stale knowledge, unstable representations and calibration failures.

Meta-reasoning chooses how deeply to think.

Value of Computation estimates whether additional cognition is worth its cost.

Runtime tiers separate sensory safety, world-state refresh, belief update, deep
cognition, offline science and offline training/discovery.

## Core, infrastructure and broker intelligence

Shared models Core stability separately from market stability.

It detects feed degradation, clock drift, latency anomalies, broker mismatch,
symbol mapping errors, data holes, execution degradation, spread anomalies and
runtime instability.

Broker intelligence maintains separate probabilistic profiles for spread,
slippage, session behavior, latency, rejection patterns, symbols, liquidity
windows and pre-close deterioration.

These systems diagnose and communicate. They do not mutate runtime or broker
state.

## Cognitive adapters and blindspots

Adapters translate generic Shared concepts into a trader's vocabulary without
rewriting methodology.

Shared maintains a Blindspot Engine:
what the trader/component sees, what it does not see, what Shared sees outside
that field and what missing information may matter.

Trader rules are never copied directly between traders. Only generic phenomena
may be abstracted and revalidated.

## Scientific laboratory and self-improvement

Research priority is driven by prediction error, unexplained recurring states,
uncertainty, cognitive failures, downstream importance, knowledge decay and
cross-market anomalies.

Autonomous experiment design is sandboxed by anti-leakage and reproducibility
contracts.

Knowledge promotion ladder:

```text
OBSERVATION
→ HYPOTHESIS
→ EXPERIMENTAL
→ FALSIFICATION_SURVIVED
→ REPLICATED
→ HOLDOUT_VALIDATED
→ STRESS_VALIDATED
→ SHADOW_VALIDATED
→ CERTIFIED
```

Self-improvement is governed and rollbackable. Shared may propose improvements
but cannot self-modify certified runtime knowledge directly.

## Trust, abstention and degraded mode

Material beliefs require provenance back to raw evidence.

Explicit abstention states include:
`INSUFFICIENT_EVIDENCE · UNIDENTIFIABLE · CONTRADICTORY · OOD ·
DATA_UNRELIABLE · NO_SUPPORTED_HYPOTHESIS`.

Trust boundaries require read-only defaults, signed artifacts, immutable
provenance, versioned knowledge, role separation, sandbox research, audit logs
and tamper detection.

Partial sensor failures reduce confidence; they must not collapse Core.

If Shared is unavailable, sovereign traders remain conceptually operable.

## Measurement law

Primary Shared intelligence metrics include reconstruction accuracy,
calibration, transition calibration, causal falsification quality, OOD/novelty
detection, uncertainty calibration, cross-market consistency, knowledge
stability/transportability, representation quality, counterfactual fidelity,
analogue retrieval, cognitive-failure reduction, reproducibility, blindspot
discovery, infrastructure/broker accuracy, explanation fidelity, latency and
availability.

PF, DD, Total R, tail risk, capital efficiency, execution quality and trader
decision quality remain downstream effects and final economic certification
evidence. They do not define Shared's identity.

## Explanation contract

Every material Shared output must be able to answer:

1. What do you believe?
2. Why?
3. What contradicts it?
4. How certain are you?
5. What would falsify it?
6. What do you not know?
7. What evidence would be most useful next?

## Program governance

This directive is transversal to the existing ordered chain #639→#650.
It does not create a competing roadmap.

PR #635 remains DRAFT / UNMERGED. No LIVE, production, real-capital or merge
authority follows from this document.
