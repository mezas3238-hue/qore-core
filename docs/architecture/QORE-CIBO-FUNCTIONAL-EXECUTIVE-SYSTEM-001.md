# QORE CIBO Functional Executive System — CF-01..CF-20

Package: `HARNESS-ENGINEER-QORE-CIBO-FUNCTIONAL-EXECUTIVE-SYSTEM-001-BATCH-007`

Functional program: qore-core #483 `QORE-CIBO-FUNCTIONAL-EXECUTIVE-SYSTEM-001`.

Canonical separation honored throughout:

- `CIBO COGNITIVE SUPERARCHITECTURE = HOW CIBO THINKS` (out of scope, #482)
- `CIBO FUNCTIONS = WHAT CIBO DOES` (this package)
- `CIBO TRADER = ONE FUNCTIONAL DOMAIN`
- `FUNCTIONAL OUTPUT != EXECUTION AUTHORITY`
- `CIBO OPINION/RECOMMENDATION != RISK OR EXECUTION AUTHORITY`
- `TYPED EVIDENCE != AUTHENTIC GOVERNED EVIDENCE`
- `PUBLICLY CONSTRUCTIBLE RECORD != AUTHORITY-ROOTED ATTESTATION`
- `TYPE VALIDITY != PROVENANCE AUTHENTICITY`
- `CIBO FUNCTIONS != RISK / MARKET / ECONOMIC / LAB CERTIFICATION AUTHORITY`
- `NO AUTHORITY ROOT -> EVIDENCE_DEPENDENT / FAIL CLOSED`

No domain in this package constructs an order, a Risk decision, a provider
instruction, or a code/config mutation. The shared authority ladder
`CiboFunctionalAuthority` has no `EXECUTION`/`ORDER`/`DECISION` member.

## Functional coverage ledger

| CF | Owned contract / module | Reused authoritative dependency | Inputs | Outputs | Authority level | Evidence / freshness | Status | Tests | External dependency |
|----|--------------------------|---------------------------------|--------|---------|------------------|----------------------|--------|-------|---------------------|
| CF-01 | `cibo/market_monitoring.py` — `CiboWorldMonitor`, `CiboWorldObservation` | `cibo/contracts.py` (`CiboFunctionalEvidence`, `synthesize_evidence`), `cibo_trader_capability_profile.CiboEvidenceRef` | explicit `CiboFunctionalEvidence` assessments, `observed_at`, `subject_refs` | one `CiboMonitoringSignal` observation | `OBSERVATION` | synthesized status must be SUFFICIENT; INSUFFICIENT fails closed | implemented | `test_market_monitoring.py` | certified market-data producer (typed seam) |
| CF-02 | `cibo/specialist_mesh.py` — `CiboSpecialistMesh`, `CiboSpecialistMeshSummary`, `CiboSpecialistOpinion` | `cibo/contracts.py`, `CiboEvidenceRef` | specialist opinions per faculty | one OPINION mesh summary | `OPINION` | per-opinion evidence; synthesized only | implemented | `test_specialist_mesh.py` | specialist faculty inputs (typed seam) |
| CF-03 | `cibo_trader_manager.py` — `CiboTraderManager`, `CiboManagementDecision` (predecessor #480 correction restored) | `cibo_trader_capability_profile.CiboTraderCapabilityProfile`, `CiboDemoEligibilityEvidence`, `CiboConcentrationRecord`, `research_evaluator_identity.ResearchDecisionEvaluatorIdentity` | exact VT/version/config binding, DEMO eligibility, concentration/correlation | immutable management decision (select/reduce/suspend/block) | `OBSERVATION`/`RECOMMENDATION` only; no order | exact fingerprint + freshness; fail closed | implemented (restored) | `test_cibo_trader_manager.py` | Trader Lab DEMO eligibility (consumed) |
| CF-04 | `cibo_trader_development_review.py` — `CiboDevelopmentReview` (predecessor corrected); `cibo/trader_academy.py` — `CiboAcademy`, `CiboExperimentRequest` | `cibo_trader_capability_profile`, `research_evaluator_identity` | development review, academy stage transitions, experiment requests | review + forward-only stage transitions + experiment requests | `OPINION`/`REQUEST`; no silent mutation/self-promotion | explicit evidence + forward-only stage ladder | implemented (restored + new) | `test_cibo_trader_development_review.py`, `test_trader_academy.py` | Trader Lab execution (consumed) |
| CF-05 | `cibo/opportunity_search.py` — `CiboOpportunitySearch`, `CiboOpportunityHypothesis` | `cibo/contracts.py`, `CiboEvidenceRef` | opportunity hypotheses | evaluated hypothesis (`IDEA != EDGE`) | `OPINION` (hypothesis) / `RECOMMENDATION` (validated+sufficient) / `ABSTENTION` | SUFFICIENT required for VALIDATED/RECOMMENDED | implemented | `test_opportunity_search.py` | certified markets/Traders/regimes (typed seam) |
| CF-06 | `cibo/portfolio_intelligence.py` — `CiboPortfolioIntelligence`, `CiboAllocationRecommendation` | `cibo/contracts.py`, `CiboEvidenceRef` | portfolio participation/allocation evidence | allocation recommendation | `RECOMMENDATION`/`ABSTENTION`; Risk remains authority | evidence-bound; fails closed on insufficient | implemented | `test_portfolio_intelligence.py` | certified exposure/correlation evidence |
| CF-07 | `cibo/economic_intelligence.py` — `CiboEconomicIntelligence`, `CiboEconomicAssessment` | `cibo/contracts.py`, `CiboEvidenceRef` | explicit metrics only when evidenced | economic assessment with `INSUFFICIENT_EVIDENCE` | `OBSERVATION`/`RECOMMENDATION`; no invented PnL | metrics require evidence; `INSUFFICIENT_EVIDENCE` otherwise | implemented | `test_economic_journals.py` | #472 economics producer (typed seam) |
| CF-08 | `cibo/outcome_journal.py` — `CiboOutcomeJournal`, `CiboOutcomeRecord` | `CiboEvidenceRef`, `CiboTraderConfigFingerprint`, `research_evaluator_identity` | exact trader/version/config, refs, economics | immutable outcome-record semantics (no persistence) | `OBSERVATION` (record) | economics require DEMO fill refs; no fabricated fills/MFE/MAE | implemented | `test_economic_journals.py` | DEMO fills/reconciliation + Cognitive persistence (external) |
| CF-09 | `cibo/failure_intelligence.py` — `CiboFailureIntelligence`, `CiboFailureDiagnosis` | `cibo/contracts.py`, `CiboEvidenceRef` | loss/stop evidence | research hypothesis classification (no auto mutation) | `OPINION`/`ABSTENTION`; `INSUFFICIENT_EVIDENCE` supported | evidence-bound; no post-hoc certainty | implemented | `test_economic_journals.py` | stop/failure evidence producer |
| CF-10 | `cibo/quantitative_intelligence.py` — `CiboQuantitativeIntelligence`, `CiboQuantRequest`, `CiboQuantResult` | `cibo/contracts.py`, `CiboEvidenceRef` | typed deterministic math/stat request | deterministic computation result | `OBSERVATION` | exact parameter/ref validation; no hidden RNG/provider/retry | implemented | `test_quantitative_intelligence.py` | deterministic math/stat tools (typed seam) |
| CF-11 | `cibo/research_director.py` — `CiboResearchDirector`, `CiboResearchPlan` | `cibo/contracts.py`, `CiboEvidenceRef` | research question/hypothesis/plan/stages | forward-only stage lineage (`OBSERVATION -> … -> DEMO`) | `REQUEST`/`OBSERVATION`; no DEMO_ELIGIBLE, no self-promotion | explicit stage/data requirements; forward-only | implemented | `test_research_director.py` | Replay/OOS/robustness/Monte-Carlo producers (typed seam) |
| CF-12 | `cibo/executive_recommendation.py` — `CiboRiskAwareComposer`, `CiboExecutiveRecommendation`, `CiboRiskContext` | `cibo/contracts.py`, `CiboEvidenceRef` | functional evidence + explicit Risk evidence/context | `RECOMMEND`/`ABSTAIN`/`ESCALATE` recommendation | `RECOMMENDATION`/`ABSTENTION`/`ESCALATION`; no Risk decision | RECOMMEND requires SUFFICIENT evidence + Risk context | implemented | `test_executive_recommendation.py` | certified Risk decision authority (external) |
| CF-13 | `cibo/core_health.py` — `CiboCoreHealth`, `CiboHealthSnapshot` | `cibo/contracts.py`, `CiboEvidenceRef`, `cibo_operational_supervision_evidence` | capability availability/degradation, stale/missing inputs | health snapshot/assessment | `OBSERVATION`/`ESCALATION`; no silent repair/code mutation | evidence-pipeline freshness + reconciliation gaps | implemented | `test_core_health.py` | operational supervision evidence producer |
| CF-14 | `cibo/executive_planner.py` — `CiboExecutivePlanner`, `CiboObjective`, `CiboGoal`, `CiboPlan` | `cibo/contracts.py`, `CiboEvidenceRef` | CEO objective → goals/subgoals/deps | deterministic plan with dependency-cycle rejection | `REQUEST`/`RECOMMENDATION`; no code/config mutation | explicit dependencies + replan evidence | implemented | `test_executive_planner.py` | Cognitive planning substrate (future) |
| CF-15 | `governance/cibo/ceo_dialogue.py` — CEO dialogue result | `cibo/contracts.py`, `CiboEvidenceRef`, `governance/cibo_executive_dialogue.CiboExecutiveAnswer` semantics | CEO query/context | explain/ask/doubt/compare/opine/state unknowns | `OPINION`/`ABSTENTION`; free-form dialogue never grants command authority | explicit refs where facts are asserted | implemented | `test_ceo_dialogue.py` | existing CIBO executive dialogue module |
| CF-16 | `cibo/trader_voice.py` — `CiboTraderVoice`, `CiboTraderCouncil`, `CiboCouncilResponse` | `cibo/contracts.py`, `CiboEvidenceRef`, `research_evaluator_identity` | governed trader observations/reasoning/opinions | agree/disagree/challenge/request/route | `OPINION`; `TRADER VOICE != FORMAL SIGNAL` | governed trader inputs only | implemented | `test_trader_voice.py` | #475 Trader Voice contracts |
| CF-17 | `cibo/decision_journal.py` — `CiboDecisionJournal`, `CiboDecisionEpisode` | `cibo/contracts.py`, `CiboEvidenceRef`, `research_evaluator_identity` | world/Core refs, hypotheses, consulted traders, decision refs | immutable decision-episode semantics (no persistence) | `OBSERVATION` (record) | exact refs + later actual result when evidenced | implemented | `test_economic_journals.py` | Cognitive persistence (external) |
| CF-18 | `cibo/self_evaluation.py` — `CiboSelfEvaluation`, `CiboAbEvaluation` | `cibo/contracts.py`, `research_evaluator_identity` | fair A/B arms (`TRADERS_RISK_ONLY` vs `CIBO_MANAGED_TRADERS_RISK`) | contribution assessment (no cherry-picking) | `OPINION` | identical versions + comparable windows; mismatches rejected | implemented | `test_self_evaluation_learning.py` | comparable A/B evidence windows |
| CF-19 | `cibo/learning.py` — `CiboLearning`, `CiboLesson` | `cibo/contracts.py`, `CiboEvidenceRef` | validated outcomes → accepted/rejected lessons | typed lesson with provenance/confidence/applicability | `OPINION`; cannot silently rewrite code/config | outcome ref + evidence required | implemented | `test_self_evaluation_learning.py` | Cognitive memory (future) |
| CF-20 | `cibo/functional_coordinator.py` — `CiboFunctionalCoordinator`, `CiboFunctionalCoordination`, `CiboFunctionalContribution`, `CiboFunctionalDisagreement` | `cibo/contracts.py`, all faculty domains CF-01..CF-19 | attributed faculty contributions | one typed coordination (`RECOMMEND`/`REQUEST`/`ABSTAIN`) with preserved disagreements | `RECOMMENDATION`/`REQUEST`/`ABSTENTION`; no execution authority | synthesized evidence; disagreements preserved verbatim | implemented | `test_functional_coordinator.py` | none (pure coordination seam) |

No row is omitted. `EVIDENCE_DEPENDENT_SEAM` applies only where an external
certified producer (Trader Lab, DEMO fills, #472 economics, market-data
producers, future Cognitive persistence) genuinely does not yet exist; in every
such case the typed seam and fail-closed tests are present in this package.

## Correction 001 — governed evidence boundary (IA residuals)

Correction 001 closes three Integration-Authority residuals without changing the
Batch-007 functional program:

- **IA-F1 (opaque-reference laundering).** A bare `CiboEvidenceRef` is an opaque
  sanitized label and is no longer proof of evidence authenticity. Functional
  sufficiency now binds to `CiboGovernedEvidenceMaterial`. (Correction 002
  supersedes its shape: see the Correction 002 section below; the material is now
  attestation-bound rather than a caller-supplied UUID/timestamp tuple.)
  `CiboFunctionalEvidence(status=SUFFICIENT)` requires at least one revalidated
  governed material; empty or opaque-only refs fail closed. `CiboRiskContext`
  requires governed `RISK`-kind material, never a bare ref plus a code label. The
  `EVIDENCE_DEPENDENT` status is the explicit producer seam: it can never yield
  SUFFICIENT and always fails closed to ABSTAIN/ESCALATE/INSUFFICIENT.
- **IA-F2 (direct-constructor semantic bypass).** Immutable result contracts now
  enforce the same ceiling as their builders. `CiboFunctionalCoordination` with
  `disposition=RECOMMEND` requires SUFFICIENT evidence and no preserved
  disagreement; `ABSTAIN` must reflect non-sufficient evidence or a disagreement.
  `CiboExecutiveRecommendation` ESCALATE requires SUFFICIENT evidence with no Risk
  context, and ABSTAIN must not carry SUFFICIENT evidence.
- **IA-F3 (disagreement / deep-validation).** Duplicate disagreement faculties are
  rejected (not silently set-collapsed); differing disagreements with the same
  subject are rejected (not last-write-wins); `synthesize_evidence` recursively
  reconstructs every nested assessment and its governed material, so reflective
  corruption or malformed nested material fails closed.

## Correction 002 — governed evidence authenticity (IA residuals)

> **Superseded by Correction 003.** Correction 002 bound governed evidence to a
> publicly constructible producer record, which does not establish provenance
> (see Correction 003 below). The exact-runtime-type and temporal-ordering
> hardening of Correction 002 remains in force; only the attestation *trust root*
> is replaced.

Correction 002 closes the residual family IA-FUNC-R1/R2/R3 without restarting the
Batch-007 six-lane discovery. The governing law is
`TYPED EVIDENCE != AUTHENTIC GOVERNED EVIDENCE`: a UUID, enum label, digest, or
well-typed record is not proof that Risk, Market Intelligence, Economic
Intelligence, or the Trader Lab actually emitted it.

- **IA-FUNC-R1 (self-declared governed evidence).** `CiboGovernedEvidenceMaterial`
  is no longer constructible from caller-supplied `kind`/`evidence_id`/
  `certified_at` fields. It now carries an `attestation` field bound to an
  authoritative producer record already present in QORE, and derives its
  `evidence_id` and `certified_at` from that record:
  - `RISK` -> a resolved `FunctionalDecision` in the `risk.` namespace;
  - `MARKET` -> `QualifiedOhlcBarObservation` / `QualifiedQuoteTickObservation` /
    `InstrumentMarketSpecification`;
  - `ECONOMIC` -> `ResearchGrossEconomicResult` / `ResearchNetEconomicResult` /
    `ResearchReturnObservation`.
  The declared `kind` must match the attestation type, so a caller can never mint
  governed evidence by filling well-typed fields. CIBO Functions never become
  their own Risk/Lab/market/economic certification authority.
- **IA-FUNC-R1 (Trader Lab seam).** LAB evidence has no UUID/timestamp authority
  record in QORE yet, so `CiboGovernedEvidenceKind.LAB` is deliberately not
  manufacturable and must be surfaced as an explicit fail-closed
  `EVIDENCE_DEPENDENT` seam until the Trader Lab exposes one.
- **IA-FUNC-R2 (exact runtime trust boundaries).** Every authority-bearing enum
  field across the CIBO tree (`kind`, `status`, `disposition`, `authority`,
  `state`, `signal`, `faculty`, `mode`, `stage`, `conclusion`, `tool`, `arm`,
  `health`, `classification`, and the Trader-academy stage/recommendation/reason
  enums) requires its exact runtime enum type (`type(x) is
  CiboFunctionalAuthority`, etc. — never a generic `isinstance`) so a distinct
  value-equal StrEnum or a raw string cannot launder into a stronger state.
  Every CIBO timestamp validator requires exact `datetime` (`type(value) is not
  datetime`) so a subclass cannot override the ordering operators used by
  temporal-provenance checks (including the response/update/result ordering
  boundaries in `trader_voice`, `research_director`, and
  `quantitative_intelligence`). `bool` remains distinct from `int`
  (`type(x) is int`), and retained nested material is recursively revalidated
  before consumption — including the authoritative producer attestation itself,
  whose own validation is re-entered so a reflectively corrupted producer record
  (e.g. `bid > ask`) fails closed.
- **IA-FUNC-R3 (temporal provenance ordering).** Governed evidence cannot be
  certified after the consuming instant: `CiboFunctionalEvidence` enforces
  `certified_at <= as_of`, `synthesize_evidence` enforces `certified_at <= as_of`
  at the synthesis/decision point, and `CiboRiskContext` enforces
  `certified_at <= assessed_at`. Future evidence therefore fails closed rather
  than silently becoming valid after the decision.

## Correction 003 — authority-root attestation (IA-FUNC-R1B)

Correction 002's authenticity root was still insufficient: it bound
`CiboGovernedEvidenceMaterial` to a *publicly constructible* producer value record
(a resolved `risk.` `FunctionalDecision`, a qualified market observation, or a
research economic result). At least `FunctionalDecision` is a public dataclass and
`DecisionType("risk.*")` is publicly constructible, so any caller could synthesize
a resolved `risk.*` decision and present it as authority-issued.

Correction 003 removes the forgeable attestation claim entirely, in line with the
authority-root law above:

- **Lane 1 — authority-root inventory.** LSP/reference analysis proves every
  candidate producer record is a public value record, not an authority-rooted
  receipt. `FunctionalDecision` / `DecisionType` are public frozen dataclasses; the
  market observations (`QualifiedOhlcBarObservation` / `QualifiedQuoteTickObservation`
  / `InstrumentMarketSpecification`) and research economic results
  (`ResearchGrossEconomicResult` / `ResearchNetEconomicResult` /
  `ResearchReturnObservation`) are public value dataclasses. The Risk module's
  `AssessAllocationRiskCommand.to_decision()` returns a plain public
  `FunctionalDecision` and `RiskDecisionProducedEvent` is a plain public event —
  neither is an authority receipt. `ResearchProducerLineageVerifier` is a
  computation-reproduction verifier taking caller-supplied Protocols ("producer
  provenance remains unproven"). `verify_client_decision_envelope` is a real
  cryptographic verifier but only for `core.trade` execution decisions, not for
  Risk/Market/Economic/Lab evidence certification.
- **Lane 2 — trust-root redesign.** `CiboGovernedEvidenceMaterial` and its
  producer-record `attestation` binding are removed. `CiboFunctionalEvidence`
  no longer carries `governed_evidence`. `SUFFICIENT` is retained only as the
  *external-authority-injected* outcome and is refused at construction: a CIBO
  Function is not a certification authority and cannot manufacture SUFFICIENT.
  The only evidence-bearing conclusion CIBO can construct is `EVIDENCE_DEPENDENT`,
  which now requires an explicit `dependency_kind` (exactly one of RISK / MARKET /
  ECONOMIC / LAB) plus explicit seam `reasons`.
- **Lane 3/4 — Risk / Market / Economic / Lab adversarial closure.** Direct
  construction of a resolved `risk.*` `FunctionalDecision`, a qualified market
  observation, or a research economic result cannot create governed sufficiency
  (there is no route to bind them; `SUFFICIENT` is refused). Subclass laundering is
  rejected (a `FunctionalDecision` subclass is still not a
  `CiboFunctionalEvidence`). `CiboRiskContext` now binds an explicit
  `EVIDENCE_DEPENDENT` RISK assessment (`dependency_kind=RISK`), never a bare
  decision. LAB remains an explicit dependency seam (no authority receipt exists).
- **Lane 5 — regression.** Exact-runtime-type hardening is preserved (`type(x) is
  Enum`/`datetime`; bool != int; recursive nested revalidation). Temporal
  provenance is preserved via explicit timezone-aware instants and the
  `risk_evidence.as_of <= assessed_at` boundary; a datetime subclass is rejected at
  every trust boundary. `synthesize_evidence` reduces deterministically and fails
  closed on heterogeneous dependency kinds; it can never synthesize SUFFICIENT.

Downstream consequence: because `SUFFICIENT` is no longer manufacturable inside
CIBO Functions, the positive conclusions that required it (`NO_MATERIAL_CHANGE`,
`RECOMMEND`, `HEALTHY`, `VALIDATED`/`RECOMMENDED`, `SUFFICIENT_EVIDENCE`, accepted
lessons, authoritative quant results, terminal trader-lab/demo advancement) all
fail closed to `EVIDENCE_DEPENDENT` / `ABSTAIN` / `DEGRADED` / `INSUFFICIENT_EVIDENCE`
until an owning authority injects an authority-rooted receipt. No execution,
promotion, Risk-bypass, Production, or real-capital authority is introduced.

## Authority-boundary matrix (adversarial)

1. wrong Trader/version/config/evidence binding fails closed — CF-03 (`test_cibo_trader_manager.py`)
2. stale/missing/contradictory evidence cannot become opportunity/portfolio/trader/economic certainty — CF-01/05/06/07
3. fabricated PnL/metric without evidence is rejected — CF-07/CF-08 (`test_economic_journals.py`)
4. unsupported specialist opinion cannot become formal signal/order — CF-02/CF-16
5. functional coordinator cannot convert dialogue/opinion into execution authority — CF-20 (`test_functional_coordinator.py`)
6. Risk-aware recommendation cannot become Risk decision — CF-12 (`test_executive_recommendation.py`)
7. research hypothesis cannot become DEMO_ELIGIBLE — CF-11 (`test_research_director.py`)
8. Academy cannot silently mutate certified Trader version — CF-04 (`test_trader_academy.py`)
9. A/B mismatched versions/windows rejected — CF-18 (`test_self_evaluation_learning.py`)
10. self-evaluation cannot cherry-pick/retroactively substitute Traders — CF-18
11. stop/failure classification supports INSUFFICIENT_EVIDENCE and no post-hoc certainty — CF-09
12. quant request contains no hidden provider/RNG/retry-to-pass behavior — CF-10
13. Core-health degradation does not trigger hidden corrective trading or code mutation — CF-13
14. CEO dialogue cannot grant provider/order authority — CF-15
15. journal records cannot invent absent fills/PnL/MFE/MAE — CF-08
16. functional output has exact provenance/evidence/freshness where required — all domains
17. repeated identical input yields deterministic equal result/logical material — all domains
18. malformed nested types return typed Failure rather than raw AttributeError/TypeError — all domains
19. no secrets leak through logical_values/repr/evidence refs — all domains (sanitized code/ref validators)
20. every CF-01..CF-20 has executable test coverage and is represented here — this ledger

## Integration acceptance

A single integration test (`test_functional_coordinator.py::
test_coherent_functional_path_has_no_execution_authority`) demonstrates the path

`authorized evidence -> monitoring/specialists -> hypothesis/opportunity ->
risk-aware functional reasoning -> typed recommendation -> coordinator material`

and proves the final authority is `RECOMMENDATION` at most (no execution, no
Risk decision, no provider order). No Cognitive Batch 006 code and no Trader Lab
implementation is duplicated; no Production/real-capital authority is introduced.

## DEMO Acceleration deltas (D1-D6)

This continuation adds the post-freeze `#483` deltas on top of the recovered
Correction-003 candidate. It reuses the canonical CF-01..CF-20 registry (no
CF-21+ identifiers) and preserves every authority boundary above.

### D1 — exact-runtime / no-subclass-laundering (CIBO review module)

`ReviewFunctionalDecisionCommand` and `CiboDecisionProducedEvent` in
`src/qore/modules/cibo/contracts.py` now enforce exact runtime types and
recursively revalidate the retained source decision:

- `type(source_decision) is FunctionalDecision`, `type(decision_id) is
  DecisionId`, `type(priority) is DecisionPriority`, `type(requested_outcome) is
  DecisionOutcome` (when set), and `type(reason) is DecisionReason` per element —
  a `FunctionalDecision`/`DecisionId`/`DecisionReason` subclass or a value-equal
  StrEnum can no longer launder into a review the handler projects.
- `_validate_functional_decision` re-validates the source decision's nested exact
  types (decision_id, timestamp, decision_type, status, priority, metadata,
  reasons, outcome) and its lifecycle invariants at the trust boundary.
- `CiboDecisionProducedEvent` applies the same exact-type boundary to its
  represented decision and source id.
- Adversarial tests: `tests/modules/cibo/test_review_decision_adversarial.py`
  (subclass laundering, value-equal StrEnum laundering, reflective corruption,
  event boundary) while preserving valid exact-type callers.

### D2 — Trader Capability Profile representability (CF-03/CF-04)

The locked `CiboTraderCapabilityProfile` is proven (via
`tests/infrastructure/test_cibo/test_trader_capability_representability.py`) to
represent every required evidence-bound dimension: exact version/config,
specialty, qualified markets/timeframes, favorable + degraded regimes,
calibration + recurring errors (certified OOS/STRESS Lab evidence + economic
metrics), transaction-cost sensitivity, drawdown/tail behavior (economic
metrics), known limitations, correlation/dependence, and Risk envelope +
certification state. `CiboCertificationState` has no `DEMO_ELIGIBLE` member; no
silent methodology/config mutation.

### D3 — Market–Trader Suitability + Development/Degradation loop (CF-03/CF-04)

`src/qore/infrastructure/cibo/trader_suitability.py` adds two governed contracts
owned by the Trader Director (CF-03) and Trader Development Review (CF-04):

- `CiboSuitabilityAssessment` / `assess_market_trader_suitability` answer
  `WHAT DOES THE CURRENT EVIDENCE-BOUND MARKET/REGIME MEAN FOR THIS EXACT TRADER
  VERSION?` with explicit provenance, freshness, uncertainty, unsupported
  dimensions, and contradiction handling. The disposition ladder is deterministic
  and fails closed: a blocked/degraded exact version is `DEGRADED`, contradictory
  market evidence is `CONTRADICTORY`, non-SUFFICIENT market evidence is
  `INSUFFICIENT_EVIDENCE`, stale profile freshness is `INSUFFICIENT_EVIDENCE`,
  and positive `SUITABLE`/`CONDITIONAL`/`UNSUITABLE` outcomes are reserved for
  externally injected SUFFICIENT evidence (CIBO is not a market certification
  authority and cannot manufacture it).
- `CiboDevelopmentPlan` / `plan_trader_development` produce an individualized
  development/degradation plan with a replay/historical/stress/regime/
  calibration/error-remediation curriculum and required requalification evidence,
  plus a governed `RETRAIN` / `REDUCE_PARTICIPATION` / `SUSPEND` /
  `RESPECIALIZE` / `RETURN_TO_LAB` action. `CiboDevelopmentAction` has no
  PROMOTE/DEMO_ELIGIBLE member; a recommendation never equals Lab promotion,
  Risk approval, or DEMO eligibility, and no methodology/config is mutated.

### D4 — Dynamic Trader Team Formation (CF-03/CF-16/CF-20)

`src/qore/infrastructure/cibo/trader_team.py` forms purpose-built temporary teams
of exact-version Traders around market/regime/instrument/problem/uncertainty/
evidence needs, without adding any CF-21+ identifier:

- `CiboTraderTeam` / `form_trader_team`: exact-version membership (unique
  identity + config fingerprint) with capability provenance derived from each
  profile's certified Lab evidence; deterministic membership ordering;
  `FORMED`/`RECONFIGURED`/`DISSOLVED` dispositions (dissolution empties the
  team); REQUEST authority.
- `CiboTraderTeamOpinion`: independent hypothesis/confidence/uncertainty/
  objections plus `CiboFunctionalEvidence`; OPINION authority.
- `CiboTraderTeamSynthesis` / `synthesize_trader_team`: disagreements are
  preserved verbatim (never silently averaged) and contradictory evidence is
  compared explicitly; disposition (`CONVERGED`/`DIVERGED`/
  `INSUFFICIENT_EVIDENCE`) is derived deterministically and enforced by
  constructor/deriver parity. `TRADER OPINION -> CIBO INTEGRATES -> RISK REMAINS
  SEPARATE`: synthesis authority is OPINION, never higher.

### D5 — Mission Director + Functional Readiness Map (CF-14/CF-20)

`src/qore/infrastructure/cibo/mission_director.py` and
`functional_readiness.py` turn a high-level objective into a governed mission
without duplicating Cognitive reasoning (#482):

- `CiboMission` / `CiboMissionDirector`: objective + constraints; relevant
  functions (exact `CiboFacultyDomain`) and exact-version Traders plus readiness;
  missing evidence and unresolved uncertainty; research/replay/Lab/evaluation
  assignments; measurable hypotheses with success/failure criteria;
  training/retraining/version-comparison; DEMO observation requirements;
  baseline/counterfactual comparison; continue/revise/suspend/abandon
  disposition; and durable lineage plus unresolved risks. REQUEST authority.
- `CiboFunctionalReadinessMap` / `derive_readiness`: distinguishes semantic
  capability from demonstrated economic usefulness and fails closed against
  self-overstatement. States `CERTIFIED` / `DEMO_VALIDATING` / `QUALIFIED` /
  `DEGRADED` / `EVIDENCE_STALE` / `INSUFFICIENT_ECONOMIC_EVIDENCE` / `BLOCKED`
  are derived from backing evidence and enforced by constructor/deriver parity
  (e.g. CERTIFIED without certification evidence is rejected).

### D6 — Counterfactual Review + Economic Accountability (CF-07/08/09/17/18/19/20)

`src/qore/infrastructure/cibo/accountability.py` adds:

- `CiboCounterfactualAssessment` / `assess_counterfactual`: the eight required
  counterfactual questions (abstain-vs-act, alternate trader/version, alternate
  timing/execution, cost/slippage/liquidity sensitivity, regime-luck-vs-skill,
  lower-risk alternatives, comparable historical/replay regimes, and explicit
  unknowable outcomes). SUPPORTED requires evidence plus a conclusion; a
  counterfactual is never fabricated and never uses hindsight
  (`evidence_horizon <= assessed_at`).
- `CiboInterventionLineage` + `CiboInterventionAttribution` /
  `attribute_intervention`: the auditable lineage
  `market/situation -> evidence -> Traders/functions -> opinions/hypotheses ->
  CIBO synthesis -> recommendation -> external/governed decision -> outcome ->
  attribution -> learning disposition`, with exact intervention/version binding,
  pre-intervention evidence, prescribed development/research, post-intervention
  evidence, and a governed attribution state. A profitable outcome is never
  sufficient proof of CIBO causation: `ATTRIBUTED` requires explicit causal
  isolation evidence, otherwise the state is `UNATTRIBUTED` /
  `INSUFFICIENT_EVIDENCE` / `CONFOUNDED`.
- The resulting evidence feeds #469 DEMO A/B evaluation through the existing
  CF-18 `CiboAbEvaluation` arms (`TRADERS_RISK_ONLY` vs
  `CIBO_MANAGED_TRADERS_RISK`) without granting any DEMO execution authority.
