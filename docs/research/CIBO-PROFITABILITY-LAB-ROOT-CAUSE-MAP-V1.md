# CIBO PROFITABILITY LAB — ROOT CAUSE MAP V1

Status: RESEARCH_ONLY / READ_ONLY_AUDIT_FROZEN / NO_PRODUCTIVE_AUTHORITY  
PR: #712 `agent/cibo-profitability-lab-001`  
Checkpoint audited: `646e235668ef694f5857788e1fad077558d664b7`

## Purpose

This document freezes the first root-cause map before any behavioral repair. It separates:

- registration from runtime availability;
- runtime availability from eligibility;
- eligibility from consultation;
- consultation from execution;
- execution from economic effect.

No Trader logic, signal geometry, CMA authority, QORE Risk authority, provider model, threshold, sizing rule, or outcome-aware parameter was changed to produce these findings.

## RC-01 — CF01..CF19 coverage is administrative, not per-opportunity economic cognition

**Disposition: CONFIRMED. H1 survives falsification attempt.**

The capability exam constructs one generic `capability-consultation` contribution for every CF01..CF19 and then reports `all_functional_faculties_consulted=true` when the coordinator returns those same registered faculty identities.

Relevant seams:

- `src/qore/infrastructure/cibo_capability_exam_cognitive_coverage.py`
  - assigns all faculties through Mission Director;
  - creates generic `capability-consultation` contributions;
  - derives `all_functional_faculties_consulted` from identity coverage.
- `src/qore/infrastructure/cibo/functional_coordinator.py`
  - explicitly has no EXECUTION/ORDER/DECISION authority;
  - reduces supplied contributions to RECOMMEND / REQUEST / ABSTAIN.
- `src/qore/infrastructure/cibo_executive_brain.py`
  - is an advisory synthesis seam whose caller supplies the directive and recommendation;
  - it does not itself select CE2I tools or capital actions.

The actual historical economic loop in
`src/qore/infrastructure/cibo_phase22_v4_historical_policy_replay.py`
does not invoke `CiboFunctionalCoordinator`, `CiboExecutiveBrain`, Mission Director, or CF01..CF19 before allocation. It constructs capital candidates, assigns the frozen expectation, evaluates CE2I, runs MPC and calls the allocator.

**Broken frontier:** cognitive coverage receipt -> economic decision loop.

**Scientific consequence:** `all_functional_faculties_consulted=true` proves coverage of an administrative exam, not that CF01..CF19 governed each capital decision.

## RC-02 — Advanced CE2I evidence is dropped before the policy evaluation

**Disposition: CONFIRMED. H2 survives falsification attempt.**

`evaluate_full_ce2i_surface(...)` can consume:

- T02 `StructuralLeverageEvidence`
- T03 `MarginEfficiencyEvidence`
- T04 `RiskEfficiencyEvidence`
- T08 `PortfolioNettingEvidence`
- T10 `CapitalVelocityEvidence`
- T16 `HedgedExposureEvidence`
- T17 `ConvexExposureEvidence`

The exact runtime chain is:

`execute_phase22_chronological_replay`
-> `seal_phase22_historical_replay_epoch`
-> `evaluate_phase22_historical_policy`
-> `evaluate_full_ce2i_surface`.

However, `execute_phase22_chronological_replay(...)` does **not** pass `advanced_evidence` into the sealing call. The sealing function therefore replaces `None` with a new empty `AdvancedPortfolioEvidence()`.

The full-surface evaluator then builds empty evidence bundles, producing the observed fail-closed reasons:

- T02 -> `MISSING_STRUCTURAL_LEVERAGE_EVIDENCE`
- T03 -> `MISSING_MARGIN_EFFICIENCY_EVIDENCE`
- T04 -> `MISSING_RISK_EFFICIENCY_EVIDENCE`
- T08 -> `MISSING_PORTFOLIO_NETTING_EVIDENCE`
- T10 -> `MISSING_CAPITAL_VELOCITY_EVIDENCE`
- T16 -> `MISSING_HEDGE_EVIDENCE`
- T17 -> `MISSING_CONVEX_INSTRUMENT_EVIDENCE`

**Producer side:** repository contracts/workflows for these evidence families exist.  
**Consumer side:** the profitability replay accepts the aggregate evidence type.  
**Broken frontier:** chronological execution -> sealing call does not transport any advanced evidence object.

This is not a tool-selection failure. The tools are enabled and asked to evaluate; their inputs are absent by construction.

## RC-03 — GEN-C runtime integration is incomplete by construction

**Disposition: CONFIRMED. H3 survives falsification attempt.**

The current compound lane imports only CMA, QORE Risk, the chronological Core execution report and the chronological replay plan. Its function accountability explicitly emits:

- GEN-C1 Compound Capital -> APPLIED/FAIL_CLOSED
- GEN-C3 Core Compound Portfolio -> APPLIED/FAIL_CLOSED
- GEN-C5 Sequential Compounding -> APPLIED/FAIL_CLOSED
- GEN-C6 Internal Capital Market -> JUSTIFIED_NOT_APPLICABLE

The profitability-lab coverage builder marks every other GEN-C capability `NOT_INTEGRATED` when it is absent from `compound.function_accountability`.

Therefore GEN-C2, GEN-C4 and GEN-C7..GEN-C14 are not merely "not selected by Cognitiva"; they never enter the economic decision surface of this treatment.

**Broken frontier:** Capital Science engines -> compound economic lane.

## RC-04 — The current expectation is Trader-constant, not opportunity-specific

**Disposition: CONFIRMED MECHANISM. H4 survives falsification attempt; economic value not yet evaluated.**

`build_frozen_train_expectation(...)` looks up one frozen row by `trader_id` from `CIBO_PHASE20_TRAIN_PRIOR_V1`.

For any two opportunities from the same Trader, the structural expectation differs only through current stop-risk USD multiplication; the underlying expected structural R and expected capital minutes are constant for that Trader. No market-state, signal-state, regime-state, path-state or opportunity-specific feature enters the prediction.

Frozen TRAIN window:

- 2021-09-23T05:00:00Z
- 2022-03-09T17:00:00Z

The diagnostic reused-holdout market clock is years earlier. The replay source explicitly labels this policy as a counterfactual historical replay and prevents pretending the later model existed at market time.

**Broken frontier:** opportunity-specific causal state -> expectation engine.

**Next scientific action:** design chronological TRAIN -> freeze -> later FORWARD/OOS expectation research. Do not fit on run 37080376842.

## RC-05 — T11 has science contracts but its runtime guard is not bound to identified models

**Disposition: CONFIRMED RUNTIME GAP; model-identification status remains evidence-dependent.**

`cibo_ce2i_t11_runtime_guard.py` defaults:

- `gross_edge_model_ready=False`
- `market_impact_model_ready=False`

and emits:

- `T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED`
- `T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED`.

Separate repository components exist for:

- fresh-OOS gross-edge validation;
- market-impact terminal receipts;
- T11 policy-input readiness.

But the profitability historical policy/execution path does not bind a `T11PolicyInputReadiness` result into the T11 runtime guard or into the allocator. The runtime guard is also explicitly shadow-only.

**Broken frontier:** T11 evidence/readiness science -> economic runtime guard/policy input.

## RC-06 — Compound redeploys realized profit on the frozen Core selection without preservation / marginal-utility / speed governors

**Disposition: CONFIRMED MECHANISM. H5 remains OPEN as an economic causal hypothesis.**

The current compound lane:

1. follows the executed Core selection surface;
2. accumulates causally prior realized positive settlements in an account-local profit pool;
3. attempts an additional minimum executable seed from that pool;
4. sends the incremental request through CMA and sovereign QORE Risk.

It does not call GEN-C7 Profit Preservation, GEN-C4 Marginal Capital Utility, GEN-C8 Adaptive Compound Speed, GEN-C9 Robust Growth/Ruin, GEN-C10 Digital Twin, GEN-C11 MPC, GEN-C12 Crisis Capital Intelligence, GEN-C13 Meta-Capital Memory or GEN-C14 governance inside the compound decision loop.

This directly explains why the current treatment can mechanically recycle profits into a negative Core selection surface. It does **not** yet prove which missing governor would improve OOS economics.

## Current hypothesis dispositions

| Hypothesis | Status after V1 audit | Reason |
| --- | --- | --- |
| H1 Cognitiva exists but does not govern per-opportunity economic pipeline | CONFIRMED GAP | economic replay bypasses CF/Executive Brain |
| H2 tools exist but evidence plane does not feed them | CONFIRMED for advanced CE2I | execution omits advanced_evidence |
| H3 Capital Science exists but is not integrated | CONFIRMED for GEN-C2/4/7-14 | lane accountability/runtime omits them |
| H4 expectation prior is too coarse | MECHANISM CONFIRMED | constant structural-R prior by Trader |
| H5 Compound amplifies without preservation/marginal utility/speed | MECHANISM CONFIRMED; economic causality OPEN | those governors are absent from lane |
| H6 CMA transforms R edge badly into USD | OPEN | requires stop-risk/margin/asymmetry decomposition |
| H7 provider economics turns marginal trades negative | OPEN | requires provider-cost decomposition |
| H8 CF -> CE2I -> GEN-C executive loop is fragmented | CONFIRMED GAP | no unified per-opportunity orchestration seam in replay |

## No-repair boundary frozen by this map

The first repairs must be instrumentation/adapters only:

1. durable per-opportunity Decision Trace;
2. transport existing causal advanced evidence without inventing values;
3. bind legal-stage GEN-C capabilities in shadow first;
4. expose T11 readiness inputs without granting authority;
5. leave Trader signals, geometry, CMA sovereignty and QORE Risk unchanged.

Every repair must show before/after behavior with identical population and no outcome-derived parameter selection.
