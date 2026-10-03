#!/usr/bin/env python3
"""Sequential Trader Lab runtime approval audit for CIBO CF01..CF20.

This audit enforces the Owner -> Trader Lab -> CIBO chain of command:
- every lane is a genuine retained Trader Lab candidate;
- CF01..CF20 execute in strict order;
- a gate receives PASS only after its real implementation returns a valid result;
- the exact PASS receipt is required before the next gate can run;
- CF20 consumes the distinct PASS receipt from each of CF01..CF19;
- any failure aborts the lane and therefore blocks every later gate.

Research-only. No broker mutation, order placement, Risk decision, sizing, LIVE,
Production, real-capital, deployment, promotion, certification, or merge authority.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from cibo_cognitive_trader_lab_audit import (
    Audit as CognitiveAudit,
    PHASES as COGNITIVE_PHASES,
)

from qore.governance.cibo.ceo_dialogue import CiboCeoDialogue, CiboCeoMode
from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.core_health import (
    CiboCapabilityHealth,
    CiboCoreHealth,
    CiboHealthState,
)
from qore.infrastructure.cibo.decision_journal import CiboDecisionJournal
from qore.infrastructure.cibo.economic_intelligence import CiboEconomicIntelligence
from qore.infrastructure.cibo.executive_planner import (
    CiboExecutivePlanner,
    CiboGoal,
    CiboObjective,
)
from qore.infrastructure.cibo.executive_recommendation import (
    CiboRecommendationDisposition,
    CiboRiskAwareComposer,
    CiboRiskContext,
)
from qore.infrastructure.cibo.failure_intelligence import (
    CiboFailureClass,
    CiboFailureIntelligence,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboCoordinationDisposition,
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordinator,
)
from qore.infrastructure.cibo.learning import CiboLearning, CiboLessonState
from qore.infrastructure.cibo.market_monitoring import (
    CiboMonitoringSignal,
    CiboWorldMonitor,
)
from qore.infrastructure.cibo.opportunity_search import (
    CiboOpportunityHypothesis,
    CiboOpportunitySearch,
    CiboOpportunityState,
)
from qore.infrastructure.cibo.outcome_journal import CiboOutcomeJournal
from qore.infrastructure.cibo.portfolio_intelligence import (
    CiboAllocationConclusion,
    CiboPortfolioIntelligence,
)
from qore.infrastructure.cibo.quantitative_intelligence import (
    CiboQuantRequest,
    CiboQuantTool,
    CiboQuantitativeIntelligence,
)
from qore.infrastructure.cibo.research_director import (
    CiboResearchDirector,
    CiboResearchPlan,
    CiboResearchStage,
)
from qore.infrastructure.cibo.self_evaluation import CiboAbArm, CiboSelfEvaluation
from qore.infrastructure.cibo.specialist_mesh import (
    CiboSpecialistFaculty,
    CiboSpecialistMesh,
    CiboSpecialistOpinion,
)
from qore.infrastructure.cibo.trader_academy import (
    CiboAcademy,
    CiboAcademyStage,
)
from qore.infrastructure.cibo.trader_team import (
    CiboTeamDisposition,
    CiboTeamNeed,
    form_trader_team,
)
from qore.infrastructure.cibo.trader_voice import (
    CiboCouncilDisposition,
    CiboTraderCouncil,
    CiboTraderVoice,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_development_review import (
    CiboDevelopmentReason,
    CiboDevelopmentRecommendation,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.trader_lab.cibo_functional_receipt import (
    CiboTraderLabExecutionStatus,
    CiboTraderLabFunctionGate,
    TraderLabCiboFunctionPassReceipt,
    build_cibo_function_execution,
    issue_trader_lab_cibo_function_pass,
)
from qore.kernel.result import Failure, Success


FUNCTION_GATES = tuple(
    gate
    for gate in CiboTraderLabFunctionGate
    if gate.value.startswith("cf")
)


def _must(result: object, label: str):
    if isinstance(result, Success):
        return result.value
    if isinstance(result, Failure):
        raise RuntimeError(f"{label} failed: {result.error}")
    raise RuntimeError(f"{label} returned unexpected type {type(result).__name__}")


def _jsonable(value: object) -> object:
    logical = getattr(value, "logical_values", None)
    if callable(logical):
        return _jsonable(logical())
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {
            str(k): _jsonable(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _digest(value: object) -> str:
    payload = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _identity(trader: str, source_head: str) -> ResearchDecisionEvaluatorIdentity:
    family = "virtual.trader." + "".join(ch.lower() for ch in trader if ch.isalnum())
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(family),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision(source_head),
    )


def _config_fingerprint(candidate_fingerprint: str) -> CiboTraderConfigFingerprint:
    return CiboTraderConfigFingerprint(
        sha256((candidate_fingerprint + ":cibo-function-audit").encode("utf-8")).hexdigest()
    )


def _instrument_code(symbol: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "." for ch in symbol)
    normalized = normalized.strip(".")
    return normalized or "unknown.instrument"


@dataclass
class LaneState:
    previous_receipt: TraderLabCiboFunctionPassReceipt | None = None
    receipts: dict[CiboTraderLabFunctionGate, TraderLabCiboFunctionPassReceipt] = field(
        default_factory=dict
    )
    reports: list[dict[str, object]] = field(default_factory=list)


class FullFunctionAudit:
    def __init__(self, trace: dict[str, object], source_head: str) -> None:
        self.trace = trace
        self.source_head = source_head
        bootstrap = CognitiveAudit(trace, source_head)
        bootstrap.run_phase(COGNITIVE_PHASES[0], bootstrap.p01)
        self.contexts = bootstrap.contexts
        self.traders = bootstrap.traders
        self.lanes = {trader: LaneState() for trader in self.traders}

    def _gate_time(self, ctx: object, gate: CiboTraderLabFunctionGate):
        lifecycle = ctx.lifecycle
        if lifecycle is None or not lifecycle.qualifications:
            raise RuntimeError("Trader Lab RESEARCH qualification missing")
        return lifecycle.qualifications[-1].qualified_at + timedelta(
            minutes=FUNCTION_GATES.index(gate) + 1
        )

    def _sufficient(
        self,
        receipt: TraderLabCiboFunctionPassReceipt,
        *,
        as_of,
    ) -> CiboFunctionalEvidence:
        return CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(receipt.evidence_ref,),
            as_of=as_of,
            trader_lab_pass_receipts=(receipt,),
        )

    def _run_gate(self, gate: CiboTraderLabFunctionGate, executor) -> None:
        if gate not in FUNCTION_GATES:
            raise RuntimeError(f"{gate.value} is not a CF gate")
        for trader in self.traders:
            ctx = self.contexts[trader]
            lane = self.lanes[trader]
            now = self._gate_time(ctx, gate)
            expected_index = FUNCTION_GATES.index(gate)
            if expected_index == 0:
                if lane.previous_receipt is not None:
                    raise RuntimeError("CF01 cannot start with a previous receipt")
            else:
                expected_prev = FUNCTION_GATES[expected_index - 1]
                if lane.previous_receipt is None:
                    raise RuntimeError(
                        f"{gate.value} blocked: {expected_prev.value} has no PASS receipt"
                    )
                if lane.previous_receipt.function is not expected_prev:
                    raise RuntimeError(
                        f"{gate.value} blocked by wrong previous gate "
                        f"{lane.previous_receipt.function.value}"
                    )

            output, semantic = executor(ctx, now, lane.previous_receipt)
            input_material = (
                ctx.candidate.fingerprint.value,
                gate.value,
                None
                if lane.previous_receipt is None
                else lane.previous_receipt.receipt_sha256,
            )
            execution = _must(
                build_cibo_function_execution(
                    candidate=ctx.candidate,
                    function=gate,
                    input_sha256=_digest(input_material),
                    output_sha256=_digest(output),
                    executed_at=now,
                    status=CiboTraderLabExecutionStatus.PASS,
                ),
                gate.value + " execution record",
            )
            receipt = _must(
                issue_trader_lab_cibo_function_pass(
                    ctx.lifecycle,
                    execution,
                    previous_receipt=lane.previous_receipt,
                ),
                gate.value + " Trader Lab PASS",
            )
            lane.previous_receipt = receipt
            lane.receipts[gate] = receipt
            lane.reports.append(
                {
                    "gate": gate.value,
                    "status": "PASS",
                    "candidate_fingerprint": ctx.candidate.fingerprint.value,
                    "execution_sha256": execution.execution_sha256,
                    "output_sha256": execution.output_sha256,
                    "receipt_sha256": receipt.receipt_sha256,
                    "previous_receipt_sha256": (
                        None
                        if receipt.previous_receipt is None
                        else receipt.previous_receipt.receipt_sha256
                    ),
                    "semantic_assertion": semantic,
                    "broker_mutation": False,
                    "live": False,
                    "production": False,
                    "real_capital": False,
                }
            )

    def cf01(self, ctx, now, previous):
        if previous is not None:
            raise RuntimeError("CF01 bootstrap must not consume a previous CIBO receipt")
        evidence = CiboFunctionalEvidence(
            status=CiboEvidenceStatus.MISSING,
            evidence_refs=(),
            as_of=now,
            reasons=("trader-lab-bootstrap",),
        )
        value = _must(
            CiboWorldMonitor().observe(
                (evidence,),
                observed_at=now,
                subject_refs=(),
            ),
            "CF01 world monitoring",
        )
        if value.signal is not CiboMonitoringSignal.EVIDENCE_GAP:
            raise RuntimeError("CF01 did not preserve the explicit bootstrap evidence gap")
        return value, "real monitor executed; explicit evidence gap preserved"

    def cf02(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        opinion = CiboSpecialistOpinion(
            faculty=CiboSpecialistFaculty.SYNTHETIC_CROSS_ASSET,
            opinion_code="trader-lab-functional-pass",
            evidence=evidence,
            authored_at=now,
            authority=CiboFunctionalAuthority.OPINION,
        )
        value = _must(
            CiboSpecialistMesh().collect((opinion,), concluded_at=now),
            "CF02 specialist mesh",
        )
        if value.faculty_count != 1:
            raise RuntimeError("CF02 did not consume the specialist opinion")
        if value.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            raise RuntimeError("CF02 lost Trader Lab sufficient evidence")
        return value, "specialist mesh consumed prior Trader Lab PASS"

    def cf03(self, ctx, now, previous):
        # The retained candidate is only RESEARCH_READY at this point.  We therefore
        # exercise the real no-member dissolution path instead of fabricating a
        # certified REPLAY/OOS capability profile.
        value = _must(
            form_trader_team(
                (),
                mission_code="trader-lab-function-audit",
                needs=(CiboTeamNeed.MARKET,),
                disposition=CiboTeamDisposition.DISSOLVED,
                formed_at=now,
                provenance=("trader-lab",),
            ),
            "CF03 trader director",
        )
        if value.disposition is not CiboTeamDisposition.DISSOLVED or value.members:
            raise RuntimeError("CF03 dissolution contract did not execute correctly")
        return value, "real Trader Director dissolution path; no fake certified profile"

    def cf04(self, ctx, now, previous):
        identity = _identity(ctx.trader, self.source_head)
        fingerprint = _config_fingerprint(ctx.candidate.fingerprint.value)
        request = _must(
            CiboAcademy().request_experiment(
                request_code="trader-lab-function-audit",
                trader_identity=identity,
                config_fingerprint=fingerprint,
                hypothesis_code="function-chain-operability",
                evidence_refs=(previous.evidence_ref,),
                requested_at=now,
            ),
            "CF04 academy request",
        )
        stage = _must(
            CiboAcademy().advance(
                CiboAcademyStage.OBSERVE,
                decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
                reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
            ),
            "CF04 academy advance",
        )
        if stage is not CiboAcademyStage.DIAGNOSE:
            raise RuntimeError("CF04 curriculum advance did not reach DIAGNOSE")
        return (request, stage.value), "experiment request plus real curriculum advance"

    def cf05(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        hypothesis = CiboOpportunityHypothesis(
            opportunity_code="trader-lab-opportunity",
            market_refs=(previous.evidence_ref,),
            evidence=evidence,
            state=CiboOpportunityState.VALIDATED,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
            declared_at=now,
        )
        value = _must(
            CiboOpportunitySearch().evaluate(hypothesis),
            "CF05 opportunity search",
        )
        if value.state is not CiboOpportunityState.VALIDATED:
            raise RuntimeError("CF05 positive validated path was not preserved")
        return value, "VALIDATED path backed by prior Trader Lab PASS"

    def cf06(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        value = _must(
            CiboPortfolioIntelligence().recommend(
                evidence,
                participation_refs=(previous.evidence_ref,),
                allocation_code="portfolio.trader-lab.audit",
                recommended_at=now,
            ),
            "CF06 portfolio intelligence",
        )
        if value.conclusion is not CiboAllocationConclusion.DIVERSIFIED:
            raise RuntimeError("CF06 did not reach the sufficient-evidence allocation path")
        return value, "positive portfolio conclusion from Trader Lab sufficient evidence"

    def cf07(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        value = _must(
            CiboEconomicIntelligence().assess(
                metrics={
                    "gross_pnl": Decimal("1.00"),
                    "net_pnl": Decimal("0.75"),
                },
                evidence=evidence,
                attribution_refs=(previous.evidence_ref,),
                assessed_at=now,
            ),
            "CF07 economic intelligence",
        )
        if value.gross_pnl != Decimal("1.00") or value.net_pnl != Decimal("0.75"):
            raise RuntimeError("CF07 dropped authorized economic metrics")
        return value, "real economic metrics admitted only after Trader Lab PASS"

    def cf08(self, ctx, now, previous):
        identity = _identity(ctx.trader, self.source_head)
        fingerprint = _config_fingerprint(ctx.candidate.fingerprint.value)
        value = _must(
            CiboOutcomeJournal().record(
                trader_identity=identity,
                config_fingerprint=fingerprint,
                instrument_code=_instrument_code(str(ctx.row["qore_symbol"])),
                regime_code="retained-research",
                decision_refs=(previous.evidence_ref,),
                mode_code="research",
                action_code="observe",
                risk_decision_ref=None,
                demo_fill_refs=(),
                reconciliation_refs=(),
                gross_pnl=None,
                net_pnl=None,
                mfe=None,
                mae=None,
                exposure=None,
                stop_target_lifecycle_code="not-applicable",
                recorded_at=now,
            ),
            "CF08 outcome journal",
        )
        if value.decision_refs != (previous.evidence_ref,):
            raise RuntimeError("CF08 did not retain the prior Trader Lab evidence ref")
        return value, "outcome journal recorded research observation without invented fills"

    def cf09(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        value = _must(
            CiboFailureIntelligence().diagnose(
                CiboFailureClass.RISK_CONTAINMENT,
                evidence=evidence,
                hypothesis_code="trader-lab-risk-containment",
                diagnosed_at=now,
            ),
            "CF09 failure intelligence",
        )
        if value.classification is not CiboFailureClass.RISK_CONTAINMENT:
            raise RuntimeError("CF09 positive diagnosis path failed")
        return value, "non-insufficient failure classification backed by Trader Lab PASS"

    def cf10(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        request = CiboQuantRequest(
            request_code="quant.trader-lab.volatility",
            tool=CiboQuantTool.OPTION_VOLATILITY,
            input_refs=(previous.evidence_ref,),
            parameters=(("window", "252"),),
            requested_at=now,
        )
        value = _must(
            CiboQuantitativeIntelligence().dispatch(
                request,
                result_code="quant.result.volatility",
                exact_value=Decimal("0.0421"),
                evidence=evidence,
                computed_at=now,
            ),
            "CF10 quantitative intelligence",
        )
        if value.exact_value != Decimal("0.0421"):
            raise RuntimeError("CF10 authoritative quantitative result was not emitted")
        return value, "authoritative quantitative result requires and consumed Trader Lab PASS"

    def cf11(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        plan = CiboResearchPlan(
            plan_code="research.trader-lab.function-audit",
            question_code="research.question.function-operability",
            hypothesis_code="research.hypothesis.operable",
            data_requirements=(previous.evidence_ref,),
            stage=CiboResearchStage.ECONOMIC,
            evidence=evidence,
            updated_at=now,
        )
        value = _must(
            CiboResearchDirector().advance(
                plan,
                to_stage=CiboResearchStage.TRADER_LAB,
                evidence=evidence,
                updated_at=now,
            ),
            "CF11 research director",
        )
        if value.stage is not CiboResearchStage.TRADER_LAB:
            raise RuntimeError("CF11 did not reach the Trader Lab terminal stage")
        return value, "terminal TRADER_LAB research stage unlocked by authority receipt"

    def cf12(self, ctx, now, previous):
        functional_evidence = self._sufficient(previous, as_of=now)
        risk_evidence = CiboFunctionalEvidence(
            status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
            evidence_refs=(CiboEvidenceRef("risk:external-context"),),
            as_of=now,
            dependency_kind=CiboGovernedEvidenceKind.RISK,
            reasons=("external.risk.authority",),
        )
        risk_context = CiboRiskContext(
            risk_evidence=risk_evidence,
            risk_assessment_code="risk.assessment.external-context",
            assessed_at=now,
        )
        value = _must(
            CiboRiskAwareComposer().compose(
                recommendation_code="recommendation.trader-lab.audit",
                functional_evidence=functional_evidence,
                risk_context=risk_context,
                composed_at=now,
            ),
            "CF12 risk-aware recommendation",
        )
        if value.disposition is not CiboRecommendationDisposition.RECOMMEND:
            raise RuntimeError("CF12 did not reach positive recommendation path")
        return value, "RECOMMEND path; Risk remains externally authoritative"

    def cf13(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        capability = CiboCapabilityHealth(
            capability_code="core.trader-lab-function-chain",
            availability=CiboHealthState.HEALTHY,
            stale_inputs=(),
            missing_inputs=(),
            reconciliation_gaps=(),
            evidence_pipeline_code="core.trader-lab-function-chain.pipeline",
        )
        value = _must(
            CiboCoreHealth().assess(
                (capability,),
                evidence=evidence,
                blockers=(),
                assessed_at=now,
            ),
            "CF13 core health",
        )
        if value.overall is not CiboHealthState.HEALTHY:
            raise RuntimeError("CF13 could not declare HEALTHY with Trader Lab evidence")
        return value, "HEALTHY path unlocked only by Trader Lab sufficient evidence"

    def cf14(self, ctx, now, previous):
        objective = CiboObjective(
            objective_code="direction.trader-lab-function-audit",
            description_code="direction.trader-lab-function-audit.description",
            declared_at=now,
        )
        goal = CiboGoal(
            goal_code="goal.validate-next-function",
            parent_goal_code=None,
            dependency_codes=(objective.objective_code,),
            work_request_codes=(),
            research_request_codes=(),
            priority=1,
            rationale_code="direction.sequential-validation",
        )
        value = _must(
            CiboExecutivePlanner().plan(
                objective,
                goals=(goal,),
                replan_evidence=(previous.evidence_ref,),
                planned_at=now,
            ),
            "CF14 executive planner",
        )
        if len(value.goals) != 1:
            raise RuntimeError("CF14 did not preserve the acyclic validation goal")
        return value, "acyclic request-only plan consumed prior PASS"

    def cf15(self, ctx, now, previous):
        value = _must(
            CiboCeoDialogue().speak(
                CiboCeoMode.EXPLAIN,
                summary_code="trader-lab.function-pass",
                reason_codes=("sequential-validation",),
                evidence_refs=(previous.evidence_ref,),
                question_refs=(),
                spoken_at=now,
            ),
            "CF15 CEO dialogue",
        )
        if value.mode is not CiboCeoMode.EXPLAIN:
            raise RuntimeError("CF15 CEO dialogue mode drift")
        return value, "structured CEO dialogue consumed prior PASS without command authority"

    def cf16(self, ctx, now, previous):
        identity = _identity(ctx.trader, self.source_head)
        voice = CiboTraderVoice(
            trader_identity=identity,
            observation_codes=("obs-trader-lab-pass",),
            reasoning_code="reasoning-sequential-validation",
            opinion_code="opinion-function-operable",
            evidence_refs=(previous.evidence_ref,),
            voiced_at=now,
            authority=CiboFunctionalAuthority.OPINION,
        )
        value = _must(
            CiboTraderCouncil().consider(
                voice,
                disposition=CiboCouncilDisposition.AGREE,
                reason_codes=("council-review",),
                evidence_refs=(previous.evidence_ref,),
                responded_at=now,
            ),
            "CF16 trader voice",
        )
        if value.disposition is not CiboCouncilDisposition.AGREE:
            raise RuntimeError("CF16 council did not preserve the voice disposition")
        return value, "real Trader Voice plus Council path consumed prior PASS"

    def cf17(self, ctx, now, previous):
        identity = _identity(ctx.trader, self.source_head)
        value = _must(
            CiboDecisionJournal().record(
                episode_code="episode.trader-lab-function-audit",
                world_refs=(previous.evidence_ref,),
                core_refs=(),
                hypotheses=("hypothesis.function-operable",),
                alternatives=("alternative.reject",),
                uncertainty_code="uncertainty.bounded",
                consulted_specialists=("cross-asset",),
                consulted_traders=(identity,),
                evidence_refs=(previous.evidence_ref,),
                recommendation_code="recommendation.continue-validation",
                decision_code=None,
                expected_result_code="expected.next-gate-pass",
                risk_assumption_codes=("assumption.no-risk-authority",),
                actual_result_code=None,
                counterfactual_code=None,
                lesson_codes=(),
                recorded_at=now,
            ),
            "CF17 decision journal",
        )
        if value.decision_code is not None:
            raise RuntimeError("CF17 audit must not manufacture an executive decision")
        return value, "decision episode recorded without outcome-aware material"

    def cf18(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        identity = _identity(ctx.trader, self.source_head)
        value = _must(
            CiboSelfEvaluation().evaluate(
                arm_a=CiboAbArm.TRADERS_RISK_ONLY,
                arm_b=CiboAbArm.CIBO_MANAGED_TRADERS_RISK,
                trader_versions_a=(identity,),
                trader_versions_b=(identity,),
                window_start=now - timedelta(hours=2),
                window_end=now - timedelta(hours=1),
                evidence=evidence,
                conclusion_code="conclusion.function-audit",
                assessed_at=now,
            ),
            "CF18 self evaluation",
        )
        if value.trader_versions_a != value.trader_versions_b:
            raise RuntimeError("CF18 violated fair A/B exact-version parity")
        return value, "fair A/B evaluation with exact same trader version"

    def cf19(self, ctx, now, previous):
        evidence = self._sufficient(previous, as_of=now)
        value = _must(
            CiboLearning().accept(
                evidence,
                lesson_code="lesson.trader-lab-function-pass",
                outcome_ref=previous.evidence_ref,
                provenance_codes=("provenance.trader-lab",),
                confidence=Decimal("0.85"),
                evidence_refs=(previous.evidence_ref,),
                applicability_code="applicability.research",
                decided_at=now,
            ),
            "CF19 learning",
        )
        if value.state is not CiboLessonState.ACCEPTED:
            raise RuntimeError("CF19 could not ACCEPT with Trader Lab sufficient evidence")
        return value, "ACCEPTED learning path unlocked only by Trader Lab PASS"

    def cf20(self, ctx, now, previous):
        lane = self.lanes[ctx.trader]
        prior_gates = FUNCTION_GATES[:19]
        missing = [gate.value for gate in prior_gates if gate not in lane.receipts]
        if missing:
            raise RuntimeError("CF20 blocked; missing prior receipts: " + ",".join(missing))
        faculties = tuple(CiboFacultyDomain)
        if len(faculties) != 19:
            raise RuntimeError("CF20 expected exactly 19 functional faculties")
        contributions = []
        for faculty, gate in zip(faculties, prior_gates, strict=True):
            receipt = lane.receipts[gate]
            evidence = self._sufficient(receipt, as_of=now)
            contributions.append(
                CiboFunctionalContribution(
                    faculty=faculty,
                    contribution_code="trader-lab-pass",
                    subject_key="full-function-chain",
                    authority=CiboFunctionalAuthority.OBSERVATION,
                    evidence=evidence,
                    authored_at=now,
                    provenance=("trader-lab", gate.value),
                )
            )
        value = _must(
            CiboFunctionalCoordinator().coordinate(
                tuple(contributions),
                coordinated_at=now,
                request_code=None,
            ),
            "CF20 functional coordinator",
        )
        if value.disposition is not CiboCoordinationDisposition.RECOMMEND:
            raise RuntimeError("CF20 did not RECOMMEND after all 19 PASS receipts")
        if len(value.contributions) != 19:
            raise RuntimeError("CF20 did not consume all 19 functional contributions")
        if value.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            raise RuntimeError("CF20 synthesized evidence lost Trader Lab sufficiency")
        receipt_count = len(value.evidence.trader_lab_pass_receipts)
        if receipt_count != 19:
            raise RuntimeError(f"CF20 expected 19 distinct receipts, got {receipt_count}")
        return value, "coordinator consumed all 19 distinct Trader Lab PASS receipts"

    def execute(self) -> dict[str, object]:
        methods = (
            self.cf01,
            self.cf02,
            self.cf03,
            self.cf04,
            self.cf05,
            self.cf06,
            self.cf07,
            self.cf08,
            self.cf09,
            self.cf10,
            self.cf11,
            self.cf12,
            self.cf13,
            self.cf14,
            self.cf15,
            self.cf16,
            self.cf17,
            self.cf18,
            self.cf19,
            self.cf20,
        )
        if len(methods) != len(FUNCTION_GATES):
            raise RuntimeError("CF executor count does not match authority gate count")
        for gate, method in zip(FUNCTION_GATES, methods, strict=True):
            self._run_gate(gate, method)

        lanes: dict[str, object] = {}
        for trader in self.traders:
            lane = self.lanes[trader]
            passed = tuple(item["gate"] for item in lane.reports if item["status"] == "PASS")
            if len(passed) != 20:
                raise RuntimeError(f"{trader} has only {len(passed)} CF PASS gates")
            final = lane.previous_receipt
            if final is None or final.function is not CiboTraderLabFunctionGate.CF20_FUNCTIONAL_COORDINATOR:
                raise RuntimeError(f"{trader} missing final CF20 PASS receipt")
            lanes[trader] = {
                "status": "PASS",
                "gate_count": len(lane.reports),
                "gates": lane.reports,
                "final_receipt_sha256": final.receipt_sha256,
            }

        return {
            "schema": "qore.cibo.full-function-trader-lab-audit.v1",
            "source_trace_sha256": self.trace.get("trace_sha256"),
            "source_head_sha": self.source_head,
            "candidate_count": len(self.traders),
            "function_gate_count": len(FUNCTION_GATES),
            "all_functions_pass": True,
            "lanes": lanes,
            "next_stage_unlocked": "CIBO_COMPOUND_TRADER_LAB",
            "authority_chain": [
                "OWNER",
                "TRADER_LAB",
                "CIBO",
            ],
            "governance": {
                "research_only": True,
                "reused_holdout": True,
                "cibo_global_owner_approval_claimed": False,
                "certification_claimed": False,
                "broker_mutation": False,
                "orders": False,
                "risk_decision": False,
                "sizing": False,
                "live": False,
                "production": False,
                "real_capital": False,
                "merge_authority": False,
                "outcome_aware_predecision_tuning": False,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    report = FullFunctionAudit(trace, args.source_head).execute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_functions_pass": report["all_functions_pass"],
                "candidate_count": report["candidate_count"],
                "function_gate_count": report["function_gate_count"],
                "next_stage_unlocked": report["next_stage_unlocked"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
