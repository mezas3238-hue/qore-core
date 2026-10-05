# CIBO High Intelligence — GitHub Source-of-Truth / Trader Lab Execution Contract

Owner: Sergio Meza  
Repository: `mezas3238-hue/qore-core`  
Branch: `agent/cibo-high-intelligence-semantic-transport-001`

## Operating model

GitHub is the permanent source of truth.

All durable work belongs in GitHub:
- CIBO code;
- contracts;
- semantic transport;
- cognitive integration;
- tests;
- documentation;
- replay builders;
- manifests;
- hashes;
- compact evidence summaries.

Trader Lab is an execution bank only.

Trader Lab may:
- execute replays;
- run 7/7 portfolio experiments;
- run Monte Carlo and stress;
- generate traces;
- run A/B comparisons;
- diagnose failures;
- produce large temporary artifacts.

Trader Lab must not become the canonical development repository.

Large replay outputs remain outside GitHub. GitHub stores only reproducible code, manifests, hashes, metrics, and conclusions.

## Workflow

1. BUILD / REPAIR IN GITHUB.
2. SYNCHRONIZE THE EXACT GITHUB REVISION INTO TRADER LAB.
3. EXECUTE RESEARCH-ONLY REPLAY IN TRADER LAB.
4. DIAGNOSE FROM TRACE / MANIFEST / HASHED EVIDENCE.
5. RETURN THE DURABLE REPAIR TO GITHUB.
6. REPEAT UNTIL THE PHASE IS FUNCTIONALLY COMPLETE.
7. USE GITHUB ACTIONS ONLY FOR IMPORTANT PR GATES / INTEGRATION / PRE-CERTIFICATION, NOT FOR EVERY EXPERIMENT.

No merge without Owner order.

## High Intelligence principle

CIBO operates by intelligence, not by memory.

Memory is evidence and context. It is never direct trade, sizing, leverage, compound, portfolio, Risk, execution, or broker authority.

Required reasoning order:

```
PERCEIVE CURRENT CAUSAL STATE
→ BUILD CURRENT WORLD MODEL
→ RECALL RELEVANT MEMORY
→ COMPARE MEMORY AGAINST CURRENT STATE
→ GENERATE HYPOTHESES
→ EVALUATE COUNTERFACTUALS
→ ESTIMATE UNCERTAINTY
→ EVALUATE PORTFOLIO + CAPITAL CONSEQUENCES
→ CHOOSE ACTION / WAIT / ABSTAIN
→ ONLY THEN SIZE / LEVERAGE / COMPOUND / PORTFOLIO
→ QORE RISK REMAINS SOVEREIGN
```

Historical similarity must never directly authorize capital.

Novel states must be reasoned over or abstained from, never force-matched to memory.

## Current 7-trader research surface

The burned reusable 3x1Y research trace contains 3,368 decisions:

- VT08_FOREX: 162
- R34_XAUUSD: 492
- R38_EURUSD: 495
- R43_GBPUSD: 561
- R38_GBPJPY: 543
- R42_AUDJPY: 631
- VT31_NAS100: 484

Current decision-context exposure:
- R34_XAUUSD: 31 keys
- R38_EURUSD: 31
- R43_GBPUSD: 31
- R38_GBPJPY: 30
- R42_AUDJPY: 30
- VT08_FOREX: 8
- VT31_NAS100: 7

## Confirmed architecture defects

### 1. Trader context is not propagated deeply enough

The five Turtle traders already expose 30–31 causal fields per decision, but most CF01–CF19 inputs receive only narrow summaries.

VT08 native logic contains materially richer state than the 8 fields exposed to CIBO, including H4 reference, Candle-2, daily bias, protected swing, CISD, entry anchor and risk geometry.

VT31 native M1 reasoning contains materially richer state than the 7 fields exposed to CIBO, including structure, displacement, freshness, path efficiency, overlap, journey/destination, H1/H4 context and uncertainty.

### 2. Native cognitive outputs are semantically compressed

The current profitability-lab runtime executes native CF engines but `_success()` reduces most structured native results to:
- `result_type`
- `result_sha256`
- optional scalar / response_count

The downstream economic consumer therefore often sees proof that a faculty ran without seeing the semantic contents of what it concluded.

### 3. Executive brain is not on the current economic path

Archived decision traces show the executive brain as quarantined / not invoked in the current integrated profitability path.

This must be repaired in research-only mode without changing the intelligence algorithms themselves.

### 4. Evidence status is intentionally fail-closed

CF01–CF19 currently remain advisory and evidence-conservative. This authority boundary must remain intact.

The High Intelligence repair may expose semantic content for research reasoning but must not manufacture authority-rooted SUFFICIENT evidence or grant execution/Risk/broker authority.

## Repair rule

Do not retune CIBO intelligence yet.

First repair:
1. rich causal input transport;
2. semantic native output transport;
3. research-only Executive Brain integration;
4. VT08 native-memory exposure;
5. VT31 exact causal coverage;
6. 7/7 semantic-consumption observability.

Only after these are complete run the integrated 7/7 replay.

## Economic restart gate

Sizing, Adaptive Leverage, CIBO Compound and Compound Portfolio are blocked from "maximum capability" claims until High Intelligence semantic transport is complete across all seven traders.

Restart order after the gate:

1. SIZING
2. ADAPTIVE LEVERAGE
3. CIBO COMPOUND
4. COMPOUND PORTFOLIO

Each economic engine must consume an intelligence conclusion, not raw memory.

## Governance

- Research-only.
- Burned/reusable traces are not Fresh OOS.
- No certification claim from this work.
- No LIVE.
- No Production.
- No real capital.
- No broker mutation.
- No post-outcome leakage into predecision reasoning.
- No trader/symbol identity hardcoding as economic logic.
- No merge without Owner order.
