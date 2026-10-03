# CIBO PROFITABILITY LAB — ECONOMIC DECOMPOSITION V1

Status: FORENSIC_ONLY / NO_OUTCOME_AWARE_TUNING  
Source workflow run: `37081669873`  
Artifact: `11258847345`  
Trace SHA-256: `sha256:5fa9cec126a800e745c252a90019eb5df0ebd6860ab7a14d81e6dc0ecb6a5a8c`

This document uses outcomes only to diagnose the already-frozen treatment. No
threshold, feature, weight, Trader inclusion rule, Compound speed, sizing rule
or selection rule may be fitted from these results.

## Population and actual decision path

- 580 opportunities across 564 historical decision epochs.
- 580/580 rows report CF01..CF19 economic runtime consultation as `ABSENT`.
- 155 opportunities reached CMA/QORE Risk and all 155 were `ALLOW`.
- 155 settled.
- 425 did not reach Risk because the frozen policy did not select them.
- Of the 155 selected:
  - 117 were selected by positive static expected net value per risk-minute.
  - 38 were admitted by the laboratory override despite a non-positive static Trader prior.
- The expectation model is constant in structural-R and capital-minutes by Trader:
  - R34_XAUUSD: +0.0112392893R, 30 min
  - R38_EURUSD: -0.0740659687R, 40 min
  - R38_GBPJPY: +0.2772449400R, 55 min
  - R42_AUDJPY: +0.1555813531R, 80 min
  - R43_GBPUSD: +0.0454017635R, 45 min
  - VT08_FOREX: -0.0982142857R, 105 min
  - VT31_NAS100: +0.2981877695R, 6 min

The USD expectation varies only because the minimum executable stop-risk USD
varies. Market/signal state does not change the structural expectation within a
Trader.

## H6 — Is CMA's R -> USD expression the primary cause?

**Disposition from this run: NOT SUPPORTED AS PRIMARY ROOT CAUSE.**

For the 155 Core settlements:

- unweighted structural-R profit factor: **0.80361**
- actual USD gross profit factor before provider cost: **0.78973**
- actual USD net profit factor after provider cost: **0.68736**
- gross structural USD P/L before provider cost: **-$19.52985**
- provider execution adjustment: **-$11.47419**
- final Core P/L: **-$31.00405**

Thus monetary risk weighting worsened the already-negative structural population
slightly (PF 0.80361 -> 0.78973), but it did not create the negative edge.

The global authorized stop-risk asymmetry also does not support a simple
"losers are sized larger" explanation:

- 66 net winners: average authorized stop risk ≈ **$1.30568**
- 89 net losers: average authorized stop risk ≈ **$0.98852**

There are local asymmetries (for example XAUUSD loss risk exceeded winner risk),
but globally winners carried more stop-risk than losers.

### Conclusion

CMA capital expression remains worth auditing per provider/minimum-volume regime,
but the current evidence falsifies the hypothesis that a global winner/loser
risk asymmetry is the dominant explanation of the Core loss.

## H7 — Are provider economics the primary cause?

**Disposition: MATERIAL SECONDARY AMPLIFIER, NOT PRIMARY ROOT CAUSE.**

Without provider execution adjustments the 155 executed Core trades still lose:

- gross structural profit: **$73.35152**
- gross structural loss: **$92.88138**
- gross structural PF: **0.78973**
- gross structural P/L: **-$19.52985**

Provider economics then subtract another **$11.47419**, lowering PF to
**0.68736** and P/L to **-$31.00405**.

Therefore provider economics explain approximately $11.47 of the $31.00 Core
loss, but even a zero-provider-cost counterfactual remains negative.

Provider cost is economically important and must stay in all forward tests, but
it cannot explain why CIBO is selecting a structurally negative population.

## Compound causal decomposition

Current Compound:

- Core executed count: 155
- Compound selected attempts: 155
- Compound settlements: 110
- Compound Risk rejects: 45 total downstream blockers
  - 15: compound risk/margin headroom insufficient
  - 19: sovereign QORE Risk rejected compound seed
  - 11: realized-profit pool below minimum seed + cost
- Compound incremental gross structural P/L before provider cost:
  **-$20.99178**
- Compound provider cost: **-$7.63920**
- Compound incremental net P/L: **-$28.63098**
- Compound gross PF before provider cost: **0.69111**
- Compound net PF: **0.60209**

The Compound subset is therefore **worse structurally than Core** before cost
(Core gross PF 0.78973 vs Compound gross PF 0.69111).

This is consistent with the mechanism already identified in RC-06:

1. current Compound follows the same frozen Core selection surface;
2. it deploys an additional minimum executable seed when causally prior realized
   profit and headroom happen to exist;
3. it has no integrated GEN-C7 Profit Preservation;
4. it has no GEN-C4 Marginal Capital Utility comparison;
5. it has no GEN-C8 Adaptive Compound Speed;
6. it has no GEN-C9 ruin/growth governor;
7. it has no GEN-C10/11 forward capital-trajectory controller;
8. it has no GEN-C12 crisis aggressiveness governor.

The path-dependent realized-profit availability gate is therefore acting as the
main admission condition for incremental capital, not a demonstrated marginal
economic utility test.

This diagnosis is forensic. It does **not** authorize choosing a speed,
threshold or subset from these outcomes.

## Per-Trader Core decomposition

| Trader | Executed | Net wins | Net losses | Gross structural P/L before provider | Provider cost | Net P/L |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R34_XAUUSD | 17 | 11 | 6 | +$4.72100 | -$3.40000 | +$1.32100 |
| R38_EURUSD | 33 | 17 | 16 | -$0.63100 | -$1.32000 | -$1.95100 |
| R38_GBPJPY | 25 | 10 | 15 | -$11.56701 | -$1.79040 | -$13.35741 |
| R42_AUDJPY | 25 | 10 | 15 | -$5.13633 | -$0.97424 | -$6.11056 |
| R43_GBPUSD | 32 | 14 | 18 | -$6.18500 | -$1.92000 | -$8.10500 |
| VT08_FOREX | 5 | 1 | 4 | +$1.74473 | -$0.26956 | +$1.47517 |
| VT31_NAS100 | 18 | 3 | 15 | -$2.47625 | -$1.80000 | -$4.27625 |

These rows are diagnostic only. All seven Traders remain in the population.

## Updated hypothesis dispositions

- H1 cognitive coverage vs actual economic governance: **CONFIRMED GAP**
- H2 advanced evidence plane feeds runtime: **CONFIRMED GAP**
- H3 GEN-C runtime integration: **CONFIRMED GAP**
- H4 opportunity-specific expectation: **CONFIRMED GAP**
- H5 Compound lacks marginal/preservation/speed governors: **CONFIRMED MECHANISM**
- H6 global CMA winner/loser USD asymmetry: **FALSIFIED AS PRIMARY CAUSE in this run**
- H7 provider economics: **CONFIRMED SECONDARY AMPLIFIER; falsified as sole/primary cause**
- H8 unified CF -> CE2I -> GEN-C executive loop: **CONFIRMED GAP**

## Immediate implication

The next repairs should target **decision intelligence and causal evidence
availability**, not Trader geometry and not generic risk scaling.

The first safety repair required before wiring any advanced evidence is a
decision-time guard: evidence learned after the historical decision must fail
closed.
