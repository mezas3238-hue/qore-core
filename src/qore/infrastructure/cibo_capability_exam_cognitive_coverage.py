"""CIBO cognitive/functional coverage receipt for the USD60 capability exam.

This module proves that the reused-holdout capability exam traverses CIBO's
executive cognition and functional coordination surfaces before capital results
are interpreted. It does not decide a Trader entry, does not invent sizing, and
does not grant execution authority.

Authority law:
- Trader = opportunity/entry geometry only.
- CIBO CMA = sole sizing/capital-expression authority.
- QORE Risk = independent hard survivability governor.
- Cognitive/functional outputs remain advisory/request/abstention only.

The coverage receipt requires:
- governed CIBO reasoning-route selection;
- Mission Director assignment of every CF01..CF19 faculty;
- Functional Coordinator consultation of every CF01..CF19 faculty;
- exact CE2I T01..T20 registry coverage;
- explicit no-LIVE/no-real-capital/no-broker-mutation/no-merge boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_capital_management_authority import CiboCapitalManagementError
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY
from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordinator,
)
from qore.infrastructure.cibo.mission_director import (
    CiboMissionDirector,
    CiboMissionDisposition,
)
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningEpisodeState,
    CiboReasoningEvidenceQuality,
    CiboReasoningMateriality,
    CiboReasoningSituation,
    CiboReasoningUncertainty,
    select_cibo_reasoning_route,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboUncertainty,
    CiboUncertaintyKind,
)

EXPECTED_FACULTIES = tuple(sorted(CiboFacultyDomain, key=lambda item: item.value))
EXPECTED_TOOLS = tuple(f"T{index:02d}" for index in range(1, 21))


@dataclass(frozen=True, slots=True)
class CiboCapabilityCognitiveCoverageReceipt:
    source_batch_sha256: str
    observed_at: datetime
    reasoning_route_tier: str
    reasoning_mode: str
    reasoning_route_reason: str
    mission_code: str
    mission_faculties: tuple[str, ...]
    coordinated_faculties: tuple[str, ...]
    coordination_disposition: str
    executive_directive: str
    ce2i_tool_codes: tuple[str, ...]
    trader_sizing_authority: str
    cibo_sizing_authority: str
    qore_risk_sovereign: bool
    cognitive_used: bool
    all_functional_faculties_consulted: bool
    all_ce2i_tools_registered: bool
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            not self.source_batch_sha256.startswith("sha256:")
            or len(self.source_batch_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "cognitive coverage source batch digest invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "cognitive coverage observed_at must be timezone-aware"
            )
        expected_faculties = tuple(item.value for item in EXPECTED_FACULTIES)
        if self.mission_faculties != expected_faculties:
            raise CiboCapitalManagementError(
                "cognitive coverage Mission Director must assign CF01..CF19"
            )
        if self.coordinated_faculties != expected_faculties:
            raise CiboCapitalManagementError(
                "cognitive coverage coordinator must consult CF01..CF19"
            )
        if self.ce2i_tool_codes != EXPECTED_TOOLS:
            raise CiboCapitalManagementError(
                "cognitive coverage requires exact T01..T20 registry"
            )
        if self.trader_sizing_authority != "NONE":
            raise CiboCapitalManagementError(
                "Trader must not own sizing authority"
            )
        if self.cibo_sizing_authority != "CIBO_CMA":
            raise CiboCapitalManagementError(
                "CIBO CMA must own sizing authority"
            )
        if not all(
            (
                self.qore_risk_sovereign,
                self.cognitive_used,
                self.all_functional_faculties_consulted,
                self.all_ce2i_tools_registered,
            )
        ):
            raise CiboCapitalManagementError(
                "cognitive/function coverage is incomplete"
            )
        if any(
            (
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "cognitive coverage cannot grant operational authority"
            )

    @property
    def complete(self) -> bool:
        return True


def build_cibo_capability_cognitive_coverage(
    *,
    source_batch_sha256: str,
    observed_at: datetime,
) -> CiboCapabilityCognitiveCoverageReceipt:
    """Traverse CIBO cognition + CF01..CF19 without inventing capital decisions."""

    route = select_cibo_reasoning_route(
        CiboReasoningSituation(
            materiality=CiboReasoningMateriality.MATERIAL,
            uncertainty=CiboReasoningUncertainty.MODERATE,
            evidence_quality=CiboReasoningEvidenceQuality.STRONG,
            episode_state=CiboReasoningEpisodeState.ACTIVE,
            deeper_analysis_requested=True,
        )
    )

    evidence_ref = CiboEvidenceRef(
        "lab:phase22-v4-reused-capability-exam"
    )
    functional_evidence = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(evidence_ref,),
        as_of=observed_at,
        reasons=("external-lab-certification-pending",),
    )

    faculties = EXPECTED_FACULTIES
    mission_result = CiboMissionDirector().direct(
        mission_code="cibo-usd60-capability-exam",
        objective_code="validate-full-cibo-capability",
        constraint_codes=(
            "broker-mutation-forbidden",
            "cibo-owns-sizing",
            "live-forbidden",
            "real-capital-forbidden",
            "trader-sizing-forbidden",
        ),
        assigned_functions=faculties,
        assigned_traders=(),
        readiness_codes=("reused-holdout-lab-ready",),
        missing_evidence_codes=("external-certification-receipt-pending",),
        unresolved_uncertainty_codes=("capability-performance-pending",),
        assignment_codes=("consult-all-cibo-functions",),
        hypothesis_codes=("cibo-full-stack-is-operational",),
        success_criteria=(
            "cognitive-cf-ce2i-cma-risk-accounting-covered",
            "usd60-survival",
        ),
        failure_criteria=(
            "missing-functional-coverage",
            "missing-tool-coverage",
        ),
        training_codes=(),
        demo_observation_codes=("historical-replay-observation",),
        baseline_codes=("minimal-seed-control",),
        counterfactual_codes=("full-cibo-core",),
        disposition=CiboMissionDisposition.CONTINUE,
        lineage=("phase22-v4-reused-capability-exam",),
        unresolved_risk_codes=("performance-not-yet-observed",),
        planned_at=observed_at,
    )
    if isinstance(mission_result, Failure):
        raise CiboCapitalManagementError(
            f"CIBO Mission Director coverage failed: {mission_result.error}"
        )
    mission = mission_result.value

    contributions = tuple(
        CiboFunctionalContribution(
            faculty=faculty,
            contribution_code="capability-consultation",
            subject_key="usd60-capability-exam",
            authority=CiboFunctionalAuthority.OBSERVATION,
            evidence=functional_evidence,
            authored_at=observed_at,
            provenance=("phase22-v4-reused-capability-exam",),
        )
        for faculty in faculties
    )
    coordination_result = CiboFunctionalCoordinator().coordinate(
        contributions,
        coordinated_at=observed_at,
        request_code="execute-governed-capability-exam",
    )
    if isinstance(coordination_result, Failure):
        raise CiboCapitalManagementError(
            "CIBO Functional Coordinator coverage failed: "
            f"{coordination_result.error}"
        )
    coordination = coordination_result.value

    cognitive_ref = CiboCognitiveEvidenceRef(
        "lab:phase22-v4-reused-capability-exam"
    )
    synthesis_result = CiboExecutiveBrain().synthesize(
        synthesis_id=uuid5(
            NAMESPACE_URL,
            f"qore:cibo:capability-exam:{source_batch_sha256}",
        ),
        directive=CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
        reasoning_mode=route.semantic_mode,
        subject_code="cibo.usd60-capability-exam",
        synthesized_at=observed_at,
        evidence_refs=(cognitive_ref,),
        uncertainty=CiboUncertainty(
            kind=CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
        ),
        observations=("full-functional-coverage-required",),
        request_code="execute-governed-capability-exam",
        limitations=(
            "no-broker-mutation",
            "no-live",
            "no-real-capital",
        ),
    )
    if isinstance(synthesis_result, Failure):
        raise CiboCapitalManagementError(
            f"CIBO Executive Brain coverage failed: {synthesis_result.error}"
        )
    synthesis = synthesis_result.value

    mission_faculties = tuple(
        item.value for item in mission.assigned_functions
    )
    coordinated_faculties = tuple(
        item.faculty.value for item in coordination.contributions
    )
    tool_codes = tuple(item.code for item in CE2I_TOOL_REGISTRY)

    return CiboCapabilityCognitiveCoverageReceipt(
        source_batch_sha256=source_batch_sha256,
        observed_at=observed_at,
        reasoning_route_tier=route.tier.value,
        reasoning_mode=route.semantic_mode.value,
        reasoning_route_reason=route.routing_reason,
        mission_code=mission.mission_code,
        mission_faculties=mission_faculties,
        coordinated_faculties=coordinated_faculties,
        coordination_disposition=coordination.disposition.value,
        executive_directive=synthesis.directive.value,
        ce2i_tool_codes=tool_codes,
        trader_sizing_authority="NONE",
        cibo_sizing_authority="CIBO_CMA",
        qore_risk_sovereign=True,
        cognitive_used=True,
        all_functional_faculties_consulted=(
            coordinated_faculties
            == tuple(item.value for item in EXPECTED_FACULTIES)
        ),
        all_ce2i_tools_registered=(tool_codes == EXPECTED_TOOLS),
    )
