"""Reasoning route policy for the CIBO Maximum Capability research exam.

The exam is intentionally non-production and non-certifying. Every capital
decision is treated as critical materiality with high uncertainty because
recursive compounding from a USD60 account can alter future survivability and
capital optionality. The existing governed CIBO router remains the authority
that maps those typed signals to the provider/model route.
"""

from __future__ import annotations

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    ProviderCondition,
)
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningEvidenceQuality,
    CiboReasoningMateriality,
    CiboReasoningRoute,
    CiboReasoningSituation,
    CiboReasoningUncertainty,
    select_cibo_reasoning_route,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)


def select_cibo_maximum_capability_reasoning_route(
    *,
    consultation: CiboEconomicConsultationReceipt,
    regime_state: CiboCapitalRegimeState,
) -> CiboReasoningRoute:
    """Use the existing router with typed Maximum Capability exam facts."""

    if not isinstance(consultation, CiboEconomicConsultationReceipt):
        raise CiboCapitalManagementError(
            "maximum-capability routing requires canonical consultation"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "maximum-capability routing requires canonical regime state"
        )
    if (
        not consultation.causal_predecision
        or not consultation.all_faculties_consulted
        or consultation.outcome_used
        or consultation.broker_mutation
    ):
        raise CiboCapitalManagementError(
            "maximum-capability routing consultation is contaminated"
        )

    statuses = tuple(
        str(item.output_payload.get("evidence_status", ""))
        for item in consultation.faculty_receipts
    )
    evidence_quality = (
        CiboReasoningEvidenceQuality.LIMITED
        if any(status == "insufficient" for status in statuses)
        else CiboReasoningEvidenceQuality.STRONG
    )
    degraded = (
        regime_state.provider_condition is not ProviderCondition.HEALTHY
        or regime_state.evidence_stale
    )
    situation = CiboReasoningSituation(
        materiality=CiboReasoningMateriality.CRITICAL,
        uncertainty=CiboReasoningUncertainty.HIGH,
        evidence_quality=evidence_quality,
        degraded_state=degraded,
        deeper_analysis_requested=True,
    )
    return select_cibo_reasoning_route(situation)
