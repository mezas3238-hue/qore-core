"""Causal CF01-CF19 consultation seam for the CIBO Profitability Lab.

The legacy capability exam proved that faculties existed, but it did not place
them on the economic decision path.  This module makes consultation a required
precondition of each historical economic policy decision without granting any
faculty sizing, Risk, order, execution, or broker authority.

The consultation is deliberately evidence-conservative.  It records that all
faculties were consulted against the predecision state and emits a REQUEST for
missing authority-rooted evidence.  It does not manufacture SUFFICIENT evidence
and never reads the later trade outcome.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboCoordinationDisposition,
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordinator,
)
from qore.infrastructure.cibo.mission_director import (
    CiboMissionDirector,
    CiboMissionDisposition,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
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
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboUncertainty,
    CiboUncertaintyKind,
)


@dataclass(frozen=True, slots=True)
class CiboEconomicConsultationReceipt:
    decision_at: datetime
    consultation_id: str
    consulted_faculties: tuple[str, ...]
    opportunity_fingerprints: tuple[str, ...]
    coordination_disposition: str
    coordination_request_code: str | None
    reasoning_route_tier: str
    reasoning_mode: str
    reasoning_route_reason: str
    mission_code: str
    mission_faculties: tuple[str, ...]
    executive_directive: str
    executive_request_code: str | None
    causal_predecision: bool = True
    all_faculties_consulted: bool = True
    reasoning_route_selected: bool = True
    mission_director_invoked: bool = True
    functional_coordinator_invoked: bool = True
    executive_brain_invoked: bool = True
    economic_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    outcome_used: bool = False
    broker_mutation: bool = False

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "economic consultation decision_at must be timezone-aware"
            )
        if (
            not isinstance(self.consultation_id, str)
            or not self.consultation_id.startswith("sha256:")
            or len(self.consultation_id) != 71
        ):
            raise CiboCapitalManagementError(
                "economic consultation id must be canonical SHA-256"
            )
        expected = tuple(
            item.value for item in sorted(CiboFacultyDomain, key=lambda item: item.value)
        )
        if self.consulted_faculties != expected:
            raise CiboCapitalManagementError(
                "economic consultation requires exact CF01-CF19 faculty surface"
            )
        if self.mission_faculties != expected:
            raise CiboCapitalManagementError(
                "economic consultation Mission Director must assign CF01-CF19"
            )
        if not self.reasoning_route_tier or not self.reasoning_mode:
            raise CiboCapitalManagementError(
                "economic consultation requires governed reasoning route"
            )
        if not self.reasoning_route_reason:
            raise CiboCapitalManagementError(
                "economic consultation reasoning route reason missing"
            )
        if not self.mission_code:
            raise CiboCapitalManagementError(
                "economic consultation mission code missing"
            )
        if self.executive_directive != CiboExecutiveDirectiveKind.REQUEST_EVIDENCE.value:
            raise CiboCapitalManagementError(
                "economic consultation Executive Brain must request evidence"
            )
        if self.executive_request_code != self.coordination_request_code:
            raise CiboCapitalManagementError(
                "economic consultation executive/coordinator request drift"
            )
        if len(self.opportunity_fingerprints) != len(
            set(self.opportunity_fingerprints)
        ):
            raise CiboCapitalManagementError(
                "economic consultation opportunity fingerprints must be unique"
            )
        for name in (
            "causal_predecision",
            "all_faculties_consulted",
            "reasoning_route_selected",
            "mission_director_invoked",
            "functional_coordinator_invoked",
            "executive_brain_invoked",
            "economic_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "outcome_used",
            "broker_mutation",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"economic consultation {name} must be bool"
                )
        if not self.causal_predecision or not self.all_faculties_consulted:
            raise CiboCapitalManagementError(
                "economic consultation must be complete and predecision"
            )
        if not all(
            (
                self.reasoning_route_selected,
                self.mission_director_invoked,
                self.functional_coordinator_invoked,
                self.executive_brain_invoked,
            )
        ):
            raise CiboCapitalManagementError(
                "economic consultation requires complete cognitive orchestration"
            )
        if any(
            (
                self.economic_authority,
                self.sizing_authority,
                self.risk_authority,
                self.execution_authority,
                self.outcome_used,
                self.broker_mutation,
            )
        ):
            raise CiboCapitalManagementError(
                "economic consultation cannot carry productive/outcome authority"
            )


def consult_cibo_economic_faculties(
    *,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> CiboEconomicConsultationReceipt:
    """Consult all CF01-CF19 on the actual predecision economic path."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "economic consultation decision_at must be timezone-aware"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "economic consultation requires at least one opportunity"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "economic consultation requires canonical regime state"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "economic consultation regime opportunity count drift"
        )
    fingerprints = tuple(item.signal_fingerprint for item in opportunities)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "economic consultation duplicate opportunity fingerprint"
        )
    if any(not isinstance(item, TraderOpportunityEnvelope) for item in opportunities):
        raise CiboCapitalManagementError(
            "economic consultation requires TraderOpportunityEnvelope inputs"
        )

    predecision_digest = _predecision_digest(
        decision_at=decision_at,
        opportunities=opportunities,
        regime_state=regime_state,
    )
    evidence_ref = CiboEvidenceRef(
        "lab:predecision:" + predecision_digest[7:]
    )
    faculties = tuple(sorted(CiboFacultyDomain, key=lambda item: item.value))
    route = select_cibo_reasoning_route(
        CiboReasoningSituation(
            materiality=CiboReasoningMateriality.MATERIAL,
            uncertainty=CiboReasoningUncertainty.HIGH,
            evidence_quality=CiboReasoningEvidenceQuality.LIMITED,
            episode_state=CiboReasoningEpisodeState.ACTIVE,
            deeper_analysis_requested=True,
        )
    )
    mission_result = CiboMissionDirector().direct(
        mission_code="cibo-economic-predecision",
        objective_code="evaluate-economic-predecision",
        constraint_codes=(
            "broker-mutation-forbidden",
            "no-outcome-use",
            "risk-authority-external",
            "sizing-authority-cma-only",
        ),
        assigned_functions=faculties,
        assigned_traders=(),
        readiness_codes=("runtime-predecision-ready",),
        missing_evidence_codes=("authority-rooted-evidence-required",),
        unresolved_uncertainty_codes=("economic-evidence-incomplete",),
        assignment_codes=("consult-all-cibo-functions",),
        hypothesis_codes=("predecision-evidence-supports-action",),
        success_criteria=("complete-cognitive-orchestration",),
        failure_criteria=("missing-cognitive-orchestration",),
        training_codes=(),
        demo_observation_codes=("historical-replay-observation",),
        baseline_codes=(),
        counterfactual_codes=(),
        disposition=CiboMissionDisposition.CONTINUE,
        lineage=("profitability-lab", "predecision"),
        unresolved_risk_codes=("external-risk-decision-pending",),
        planned_at=decision_at,
    )
    if not isinstance(mission_result, Success):
        raise CiboCapitalManagementError(
            "economic Mission Director orchestration failed closed"
        )
    mission = mission_result.value
    mission_faculties = tuple(item.value for item in mission.assigned_functions)
    if mission_faculties != tuple(item.value for item in faculties):
        raise CiboCapitalManagementError(
            "economic Mission Director faculty assignment drift"
        )

    contributions = tuple(
        CiboFunctionalContribution(
            faculty=faculty,
            contribution_code="predecision-consulted",
            subject_key="economic-decision",
            authority=CiboFunctionalAuthority.OBSERVATION,
            evidence=CiboFunctionalEvidence(
                status=CiboEvidenceStatus.INSUFFICIENT,
                evidence_refs=(evidence_ref,),
                as_of=decision_at,
                reasons=("authority-rooted-evidence-required",),
            ),
            authored_at=decision_at,
            provenance=("profitability-lab", "predecision"),
        )
        for faculty in faculties
    )
    result = CiboFunctionalCoordinator().coordinate(
        contributions,
        coordinated_at=decision_at,
        request_code="economic.evidence.request",
    )
    if not isinstance(result, Success):
        raise CiboCapitalManagementError(
            "economic faculty coordination failed closed"
        )
    coordination = result.value
    consulted = tuple(item.faculty.value for item in coordination.contributions)
    if consulted != tuple(item.value for item in faculties):
        raise CiboCapitalManagementError(
            "economic faculty coordination surface drift"
        )
    if coordination.disposition is not CiboCoordinationDisposition.REQUEST:
        raise CiboCapitalManagementError(
            "economic faculty consultation must preserve evidence request"
        )

    cognitive_ref = CiboCognitiveEvidenceRef(
        "lab:predecision:" + predecision_digest[7:]
    )
    synthesis_result = CiboExecutiveBrain().synthesize(
        synthesis_id=uuid5(
            NAMESPACE_URL,
            f"qore:cibo:economic-predecision:{predecision_digest}",
        ),
        directive=CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
        reasoning_mode=route.semantic_mode,
        subject_code="cibo.economic-predecision",
        synthesized_at=decision_at,
        evidence_refs=(cognitive_ref,),
        uncertainty=CiboUncertainty(
            kind=CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
        ),
        observations=(
            "all-functional-faculties-consulted",
            "authority-rooted-evidence-missing",
        ),
        request_code="economic.evidence.request",
        limitations=(
            "no-broker-mutation",
            "no-outcome-use",
            "no-productive-authority",
        ),
    )
    if not isinstance(synthesis_result, Success):
        raise CiboCapitalManagementError(
            "economic Executive Brain orchestration failed closed"
        )
    synthesis = synthesis_result.value
    if synthesis.directive is not CiboExecutiveDirectiveKind.REQUEST_EVIDENCE:
        raise CiboCapitalManagementError(
            "economic Executive Brain must remain evidence-request only"
        )

    return CiboEconomicConsultationReceipt(
        decision_at=decision_at,
        consultation_id=predecision_digest,
        consulted_faculties=consulted,
        opportunity_fingerprints=tuple(sorted(fingerprints)),
        coordination_disposition=coordination.disposition.value,
        coordination_request_code=coordination.request_code,
        reasoning_route_tier=route.tier.value,
        reasoning_mode=route.semantic_mode.value,
        reasoning_route_reason=route.routing_reason,
        mission_code=mission.mission_code,
        mission_faculties=mission_faculties,
        executive_directive=synthesis.directive.value,
        executive_request_code=synthesis.request_code,
    )


def _predecision_digest(
    *,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> str:
    payload = {
        "decision_at": decision_at.isoformat(),
        "opportunities": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "provider_symbol": item.provider_symbol,
                "side": item.side,
                "entry_type": item.entry_type,
                "intended_entry": str(item.intended_entry),
                "stop_loss": str(item.stop_loss),
                "take_profit": str(item.take_profit),
            }
            for item in sorted(
                opportunities,
                key=lambda item: item.signal_fingerprint,
            )
        ],
        "regime": {
            "liquidity": regime_state.liquidity.value,
            "volatility": regime_state.volatility.value,
            "correlation": regime_state.correlation.value,
            "provider_condition": regime_state.provider_condition.value,
            "risk_utilization": str(regime_state.risk_utilization),
            "margin_utilization": str(regime_state.margin_utilization),
            "drawdown_utilization": str(regime_state.drawdown_utilization),
            "opportunity_count": regime_state.opportunity_count,
        },
        "outcome_present": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
