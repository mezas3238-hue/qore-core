# CIBO PROFITABILITY LAB — EVIDENCE PRODUCER / CONSUMER MATRIX V1

Status: RESEARCH_ONLY / ROOT_CAUSE_EVIDENCE  
PR: #712 `agent/cibo-profitability-lab-001`

## Executive finding

The advanced CE2I failure is **not one homogeneous missing-adapter bug**.

Three different situations exist:

1. **post-outcome science exists but cannot legally feed the same predecision epoch**;
2. **predecision contracts exist but no adapter transports a causal instance into the profitability replay**;
3. **provider/capability science exists but explicitly says policy readiness is not proven**.

A blanket adapter that converts repository evidence into `AdvancedPortfolioEvidence` would therefore create outcome leakage or bypass scientific readiness.

There is an additional systemic defect: the current advanced surface does not bind evidence timestamps to the decision timestamp. Every advanced evidence class has `observed_at`, but `evaluate_full_ce2i_surface(...)` receives no `decision_at` and `evaluate_advanced_ce2i_surface(...)` does not reject future evidence. Empty evidence currently prevents leakage accidentally; any future adapter must first add an explicit causal-time guard.

## Matrix

| Tool | Runtime consumer contract | Repository producer/science located | Same-epoch legality | Broken frontier / disposition |
| --- | --- | --- | --- | --- |
| T02 | `StructuralLeverageEvidence`: OOS stop incidence/tail evidence + released/protected capacity | `cibo_arch2_t02_structural_binding.py` binds provider/Risk/settlement/release + terminal outcome into `T02ForwardStructuralOutcome`; T02 OOS validators consume settled outcomes | **POST-OUTCOME for the bound episode** | No causal predecision adapter to `StructuralLeverageEvidence`. Do not transform same-run settlements into same-run T02 permission. |
| T03 | `MarginEfficiencyEvidence`: executable verified equivalent expressions with normalized exposure, stop risk, margin and all-in cost | `cibo_ce2i_t03_equivalent_expression.py` defines declarations and provider-bound `T03ExpressionEconomics` with `observed_at/known_at` | **Potentially PREDECISION** when declaration and economics are known before decision | Replay never receives expression alternatives and no adapter maps the declaration/economics audit into `MarginEfficiencyEvidence`. Candidate producer exists; runtime transport is absent. |
| T04 | `RiskEfficiencyEvidence`: OOS candidate expected output, true stop risk, p95 DD, tail loss, margin | `cibo_ce2i_t04_t10_economic_gate.py` is explicitly preregistered **outcome-bound** WF1..WF4 evaluation | **POST-OUTCOME validation** | Cannot feed the same historical epoch. A frozen prior/OOS policy artifact would have to predate the later evaluation epoch. No such runtime adapter is bound here. |
| T08 | `PortfolioNettingEvidence`: signed factor-risk mapping + stable OOS correlation + fresh OOS netting utility | `cibo_a1_t08_phase22_oos_binding.py` binds T08 shadow epochs to exact Phase22 decisions **and actual replay outcomes**, explicitly says it does not authorize netting | **POST-OUTCOME validation** | Current A1 OOS binding is proof/ablation evidence, not a same-epoch netting-credit producer. No predecision frozen correlation/risk-map/netting-utility adapter reaches the replay. |
| T10 | `CapitalVelocityEvidence`: OOS realized net output / capital-minutes with tail/DD gates | `cibo_ce2i_t04_t10_economic_gate.py` requires outcome-bound WF1..WF4 observations and authoritative deployment/release timestamps | **POST-OUTCOME validation** | Cannot feed its own episode. Needs a chronologically frozen policy learned earlier and applied later. No such artifact reaches the current replay. |
| T11 | runtime guard requires identified gross-edge + market-impact inputs | gross-edge Fresh-OOS validator, market-impact evaluator/terminal receipt, policy-input readiness modules exist | **Validation artifacts exist; runtime binding absent** | Profitability replay does not inject `T11PolicyInputReadiness`; guard defaults both model-ready flags false. Shadow guard therefore remains `T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED; T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED`. |
| T16 | `HedgedExposureEvidence`: certified/executable instrument with stable correlation, risk reduction, basis risk, cost, margin | `cibo_ce2i_t16_hedge_candidate.py` defines predecision observations (`known_at >= end_market_at`) but explicitly cannot prove fresh-OOS utility/policy readiness; separate fresh-OOS utility science exists | **Mixed: measurement may be PREDECISION; policy readiness requires prior OOS proof** | No adapter reaches runtime. More importantly, the generic advanced engine is weaker than the stricter T16 science contract: it does not itself require the fresh-OOS utility/policy-readiness receipt. Do not bridge until that readiness is enforced. |
| T17 | `ConvexExposureEvidence`: certified limited-downside instrument with fresh pricing, certified settlement/execution and positive upside net of premium/cost | provider/account GSL capability assessment and receipt exist, but explicitly state GSL is not an option/defined-risk spread and force `t17_policy_ready=False` | **NOT POLICY READY** | Current provider receipt must **not** be converted into convex permission. Missing evidence is scientifically correct until an actual certified limited-downside instrument + execution economics + fresh OOS utility exist. |

## Systemic causal-time defect

The advanced runtime evidence classes all carry `observed_at`, but:

- `evaluate_full_ce2i_surface(...)` has no explicit decision timestamp;
- `evaluate_advanced_ce2i_surface(...)` does not compare evidence `observed_at` to an opportunity/portfolio decision clock;
- `TraderOpportunityEnvelope` itself intentionally contains no timestamp.

Therefore a future adapter could accidentally supply evidence learned after the decision and still pass the advanced-engine type contracts.

### Required repair before any evidence adapter

Add a fail-closed **causal-time boundary** at the full-surface orchestration seam:

`advanced evidence observed_at <= market decision_at`

for every supplied opportunity and portfolio evidence object.

This is not replay tool-selection authority. It is a causality invariant. Replay may transport evidence; it may not decide which tool CIBO uses.

## What may be wired safely next

1. T03 can be investigated first for a true predecision adapter because its source contract already distinguishes `observed_at` and `known_at`.
2. T16 predecision measurement can be transported only as measurement/shadow evidence until the separate fresh-OOS policy-readiness contract is satisfied.
3. T11 readiness may be exposed to the runtime guard as a read-only readiness receipt, but it must not fabricate historical availability.
4. T02/T04/T08/T10 post-outcome science must remain post-outcome for the episode that generated it. Any runtime use requires chronological TRAIN/calibration -> freeze -> later FORWARD/OOS.
5. T17 remains fail-closed; current provider capability evidence is explicitly insufficient for convex-policy readiness.

## Prohibited shortcut

Do **not** populate `AdvancedPortfolioEvidence` by reading:

- the current replay's outcomes;
- T02/T08 outcome-bound bindings from the same population;
- T04/T10 WF outcome results from the same population;
- current T17 GSL capability and relabeling it as a convex instrument;
- any evidence whose `observed_at`/knowledge time postdates the historical decision.

That would convert a missing-evidence problem into outcome-aware leakage.
