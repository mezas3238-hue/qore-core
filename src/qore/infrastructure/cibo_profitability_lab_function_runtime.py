"""Native CF01-CF19 runtime probe for the CIBO Profitability Lab.

This module executes the real functional engines that are causally applicable at
the predecision boundary. It never reads the later trade outcome, never sizes,
never calls broker mutation, and never grants Risk/execution authority.

Functions whose semantics are intrinsically post-outcome (CF08, CF18, CF19) are
reported as JUSTIFIED_NOT_APPLICABLE at the predecision boundary rather than
being faked. Engines that correctly reject insufficient authority-rooted evidence
are reported as FAIL_CLOSED; that is an observed runtime result, not an integration
failure.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.governance.cibo.ceo_dialogue import CiboCeoDialogue, CiboCeoMode
from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
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
from qore.infrastructure.cibo.executive_recommendation import CiboRiskAwareComposer
from qore.infrastructure.cibo.failure_intelligence import (
    CiboFailureClass,
    CiboFailureIntelligence,
)
from qore.infrastructure.cibo.market_monitoring import CiboWorldMonitor
from qore.infrastructure.cibo.opportunity_search import (
    CiboOpportunityHypothesis,
    CiboOpportunitySearch,
    CiboOpportunityState,
)
from qore.infrastructure.cibo.portfolio_intelligence import CiboPortfolioIntelligence
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
from qore.infrastructure.cibo.specialist_mesh import (
    CiboSpecialistFaculty,
    CiboSpecialistMesh,
    CiboSpecialistOpinion,
)
from qore.infrastructure.cibo.trader_academy import CiboAcademy, CiboAcademyStage
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
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
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
from qore.kernel.result import Success


@dataclass(frozen=True, slots=True)
class CiboNativeFacultyRuntimeObservation:
    function_code: str
    engine_name: str
    engine_called: bool
    status: str
    output_payload: dict[str, object]
    reason: str | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.function_code, str)
            or not self.function_code.startswith("CF")
            or len(self.function_code) != 4
        ):
            raise CiboCapitalManagementError("native faculty function code invalid")
        if not isinstance(self.engine_name, str) or not self.engine_name:
            raise CiboCapitalManagementError("native faculty engine name required")
        if type(self.engine_called) is not bool:
            raise CiboCapitalManagementError("native faculty engine_called must be bool")
        if self.status not in {
            "SUCCESS",
            "FAIL_CLOSED",
            "DEPENDENCY_BLOCKED",
            "JUSTIFIED_NOT_APPLICABLE",
        }:
            raise CiboCapitalManagementError("native faculty runtime status invalid")
        if not isinstance(self.output_payload, dict):
            raise CiboCapitalManagementError("native faculty output payload invalid")
        if self.reason is not None and (
            not isinstance(self.reason, str) or not self.reason
        ):
            raise CiboCapitalManagementError("native faculty reason invalid")
        if self.status == "JUSTIFIED_NOT_APPLICABLE" and self.engine_called:
            raise CiboCapitalManagementError(
                "not-applicable faculty cannot claim engine execution"
            )


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    logical = getattr(value, "logical_values", None)
    if callable(logical):
        return _canonical(logical())
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _success(
    function_code: str,
    engine_name: str,
    value: object,
    *,
    status: str = "SUCCESS",
    reason: str | None = None,
) -> CiboNativeFacultyRuntimeObservation:
    return CiboNativeFacultyRuntimeObservation(
        function_code=function_code,
        engine_name=engine_name,
        engine_called=True,
        status=status,
        output_payload={
            "result_type": type(value).__name__,
            "result": _canonical(value),
        },
        reason=reason,
    )


def _capture(
    function_code: str,
    engine_name: str,
    result: object,
    *,
    success_status: str = "SUCCESS",
    success_reason: str | None = None,
) -> CiboNativeFacultyRuntimeObservation:
    if isinstance(result, Success):
        return _success(
            function_code,
            engine_name,
            result.value,
            status=success_status,
            reason=success_reason,
        )
    error = getattr(result, "error", None)
    return CiboNativeFacultyRuntimeObservation(
        function_code=function_code,
        engine_name=engine_name,
        engine_called=True,
        status="FAIL_CLOSED",
        output_payload={
            "error_type": type(error).__name__ if error is not None else type(result).__name__,
            "error": "" if error is None else str(error),
        },
        reason="native engine rejected the admitted predecision evidence",
    )


def _not_applicable(
    function_code: str,
    engine_name: str,
    reason: str,
) -> CiboNativeFacultyRuntimeObservation:
    return CiboNativeFacultyRuntimeObservation(
        function_code=function_code,
        engine_name=engine_name,
        engine_called=False,
        status="JUSTIFIED_NOT_APPLICABLE",
        output_payload={"temporal_boundary": "PREDECISION"},
        reason=reason,
    )


def _identity(trader_id: str) -> ResearchDecisionEvaluatorIdentity:
    compact = "".join(ch.lower() for ch in trader_id if ch.isalnum())
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{compact}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("profitability-lab-runtime-v1"),
    )


def evaluate_cibo_native_faculties(
    *,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
) -> tuple[CiboNativeFacultyRuntimeObservation, ...]:
    """Execute every causally applicable native CF engine at the predecision seam."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "native faculty runtime decision_at must be timezone-aware"
        )
    if not opportunities or any(
        not isinstance(item, TraderOpportunityEnvelope) for item in opportunities
    ):
        raise CiboCapitalManagementError(
            "native faculty runtime requires TraderOpportunityEnvelope inputs"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "native faculty runtime requires canonical regime state"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "native faculty runtime opportunity count drift"
        )
    if not isinstance(evidence_ref, CiboEvidenceRef):
        raise CiboCapitalManagementError(
            "native faculty runtime evidence reference invalid"
        )

    evidence = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(evidence_ref,),
        as_of=decision_at,
        reasons=("authority-rooted-evidence-required",),
    )
    identities = tuple(
        _identity(trader_id)
        for trader_id in sorted({item.trader_id.value for item in opportunities})
    )

    rows: list[CiboNativeFacultyRuntimeObservation] = []

    rows.append(
        _capture(
            "CF01",
            "CiboWorldMonitor.observe",
            CiboWorldMonitor().observe(
                (evidence,),
                observed_at=decision_at,
                subject_refs=(evidence_ref,),
            ),
        )
    )

    specialist = CiboSpecialistOpinion(
        faculty=CiboSpecialistFaculty.MACRO_REGIME,
        opinion_code="predecision-evidence-incomplete",
        evidence=evidence,
        authored_at=decision_at,
        authority=CiboFunctionalAuthority.OPINION,
    )
    rows.append(
        _capture(
            "CF02",
            "CiboSpecialistMesh.collect",
            CiboSpecialistMesh().collect(
                (specialist,),
                concluded_at=decision_at,
            ),
        )
    )

    rows.append(
        _capture(
            "CF03",
            "form_trader_team",
            form_trader_team(
                (),
                mission_code="cibo-economic-predecision",
                needs=(CiboTeamNeed.EVIDENCE,),
                disposition=CiboTeamDisposition.DISSOLVED,
                formed_at=decision_at,
                provenance=("profitability-lab", "predecision"),
            ),
            success_status="DEPENDENCY_BLOCKED",
            success_reason=(
                "exact Trader capability profiles are not injected into this "
                "historical policy seam; native team logic dissolved safely"
            ),
        )
    )

    rows.append(
        _capture(
            "CF04",
            "CiboAcademy.advance",
            CiboAcademy().advance(
                CiboAcademyStage.OBSERVE,
                decision=CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED,
                reason=CiboDevelopmentReason.EVIDENCE_INSUFFICIENT,
            ),
        )
    )

    hypothesis = CiboOpportunityHypothesis(
        opportunity_code="retained-trader-opportunity",
        market_refs=(evidence_ref,),
        evidence=evidence,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
        declared_at=decision_at,
    )
    rows.append(
        _capture(
            "CF05",
            "CiboOpportunitySearch.evaluate",
            CiboOpportunitySearch().evaluate(hypothesis),
        )
    )

    rows.append(
        _capture(
            "CF06",
            "CiboPortfolioIntelligence.recommend",
            CiboPortfolioIntelligence().recommend(
                evidence,
                participation_refs=(evidence_ref,),
                allocation_code="predecision-allocation-review",
                recommended_at=decision_at,
            ),
        )
    )

    rows.append(
        _capture(
            "CF07",
            "CiboEconomicIntelligence.assess",
            CiboEconomicIntelligence().assess(
                metrics={},
                evidence=evidence,
                attribution_refs=(evidence_ref,),
                assessed_at=decision_at,
            ),
        )
    )

    rows.append(
        _not_applicable(
            "CF08",
            "CiboOutcomeJournal.record",
            "outcome journal is causally post-settlement and cannot run predecision",
        )
    )

    rows.append(
        _capture(
            "CF09",
            "CiboFailureIntelligence.diagnose",
            CiboFailureIntelligence().diagnose(
                CiboFailureClass.INSUFFICIENT_EVIDENCE,
                evidence=evidence,
                hypothesis_code="failure-evidence-pending",
                diagnosed_at=decision_at,
            ),
        )
    )

    quant_request = CiboQuantRequest(
        request_code="predecision-portfolio-state",
        tool=CiboQuantTool.PORTFOLIO_MATH,
        input_refs=(evidence_ref,),
        parameters=(("opportunity-count", str(len(opportunities))),),
        requested_at=decision_at,
    )
    rows.append(
        _capture(
            "CF10",
            "CiboQuantitativeIntelligence.dispatch",
            CiboQuantitativeIntelligence().dispatch(
                quant_request,
                result_code="opportunity-count",
                exact_value=Decimal(len(opportunities)),
                evidence=evidence,
                computed_at=decision_at,
            ),
        )
    )

    research_plan = CiboResearchPlan(
        plan_code="economic-predecision-research",
        question_code="authority-rooted-evidence",
        hypothesis_code="economic-evidence-supports-action",
        data_requirements=(evidence_ref,),
        stage=CiboResearchStage.OBSERVATION,
        evidence=evidence,
        updated_at=decision_at,
    )
    rows.append(
        _capture(
            "CF11",
            "CiboResearchDirector.advance",
            CiboResearchDirector().advance(
                research_plan,
                to_stage=CiboResearchStage.HYPOTHESIS,
                evidence=evidence,
                updated_at=decision_at,
            ),
        )
    )

    rows.append(
        _capture(
            "CF12",
            "CiboRiskAwareComposer.compose",
            CiboRiskAwareComposer().compose(
                recommendation_code="predecision-risk-review",
                functional_evidence=evidence,
                risk_context=None,
                composed_at=decision_at,
            ),
        )
    )

    health = CiboCapabilityHealth(
        capability_code="profitability-lab-predecision",
        availability=CiboHealthState.DEGRADED,
        stale_inputs=(),
        missing_inputs=(evidence_ref,),
        reconciliation_gaps=(),
        evidence_pipeline_code="economic-predecision",
    )
    rows.append(
        _capture(
            "CF13",
            "CiboCoreHealth.assess",
            CiboCoreHealth().assess(
                (health,),
                evidence=evidence,
                blockers=(),
                assessed_at=decision_at,
            ),
        )
    )

    objective = CiboObjective(
        objective_code="evaluate-economic-predecision",
        description_code="obtain-authority-rooted-evidence",
        declared_at=decision_at,
    )
    goal = CiboGoal(
        goal_code="obtain-economic-evidence",
        parent_goal_code=None,
        dependency_codes=(objective.objective_code,),
        work_request_codes=(),
        research_request_codes=("economic-evidence-request",),
        priority=1,
        rationale_code="evidence-incomplete",
    )
    rows.append(
        _capture(
            "CF14",
            "CiboExecutivePlanner.plan",
            CiboExecutivePlanner().plan(
                objective,
                goals=(goal,),
                replan_evidence=(evidence_ref,),
                planned_at=decision_at,
            ),
        )
    )

    rows.append(
        _capture(
            "CF15",
            "CiboCeoDialogue.speak",
            CiboCeoDialogue().speak(
                CiboCeoMode.STATE_UNKNOWN,
                summary_code="economic-evidence-incomplete",
                reason_codes=("authority-rooted-evidence-required",),
                evidence_refs=(evidence_ref,),
                question_refs=(),
                spoken_at=decision_at,
            ),
        )
    )

    voice_outputs: list[object] = []
    voice_failure: object | None = None
    for identity in identities:
        voice = CiboTraderVoice(
            trader_identity=identity,
            observation_codes=("predecision-opportunity-present",),
            reasoning_code="economic-evidence-incomplete",
            opinion_code="request-economic-evidence",
            evidence_refs=(evidence_ref,),
            voiced_at=decision_at,
            authority=CiboFunctionalAuthority.OPINION,
        )
        response = CiboTraderCouncil().consider(
            voice,
            disposition=CiboCouncilDisposition.REQUEST_EVIDENCE,
            reason_codes=("authority-rooted-evidence-required",),
            evidence_refs=(evidence_ref,),
            responded_at=decision_at,
        )
        if isinstance(response, Success):
            voice_outputs.append(response.value)
        else:
            voice_failure = response
            break
    if voice_failure is None:
        rows.append(
            _success(
                "CF16",
                "CiboTraderCouncil.consider",
                {
                    "response_count": len(voice_outputs),
                    "responses": tuple(voice_outputs),
                },
            )
        )
    else:
        rows.append(
            _capture(
                "CF16",
                "CiboTraderCouncil.consider",
                voice_failure,
            )
        )

    rows.append(
        _capture(
            "CF17",
            "CiboDecisionJournal.record",
            CiboDecisionJournal().record(
                episode_code="economic-predecision",
                world_refs=(evidence_ref,),
                core_refs=(evidence_ref,),
                hypotheses=("economic-evidence-supports-action",),
                alternatives=("abstain-until-evidence",),
                uncertainty_code="economic-evidence-incomplete",
                consulted_specialists=("macro-regime",),
                consulted_traders=identities,
                evidence_refs=(evidence_ref,),
                recommendation_code="request-economic-evidence",
                decision_code=None,
                expected_result_code="evidence-dependent",
                risk_assumption_codes=("qore-risk-external",),
                actual_result_code=None,
                counterfactual_code=None,
                lesson_codes=(),
                recorded_at=decision_at,
            ),
        )
    )

    rows.append(
        _not_applicable(
            "CF18",
            "CiboSelfEvaluation.evaluate",
            "fair A/B self-evaluation requires a completed comparison window",
        )
    )
    rows.append(
        _not_applicable(
            "CF19",
            "CiboLearning.accept/reject",
            "learning requires a settled outcome and cannot consume the current future",
        )
    )

    observed_codes = tuple(item.function_code for item in rows)
    expected_codes = tuple(f"CF{index:02d}" for index in range(1, 20))
    if observed_codes != expected_codes:
        raise CiboCapitalManagementError(
            "native CF01-CF19 runtime observation surface drift"
        )
    return tuple(rows)
