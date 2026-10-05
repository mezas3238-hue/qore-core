"""Reasoned sovereign entry point for single-account CIBO capital decisions.

One causal chain:
CF01-CF19 consultation
-> existing CIBO Adaptive Reasoning Runtime / Executive Brain
-> sovereign capital runtime
-> QORE Risk request boundary

No hand-authored threshold replaces CIBO reasoning. The same consultation receipt
is reused by reasoning and capital so each operation has one auditable cognitive
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboAdaptiveReasoningRuntime,
    CiboAdaptiveReasoningRuntimeResult,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_economic_engine_wiring import CiboLifecycleWireRequest
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
)
from qore.infrastructure.cibo_reasoning_runtime import CiboReasoningRequest
from qore.infrastructure.cibo_sovereign_capital_runtime import (
    CiboSovereignCapitalDecision,
    run_cibo_sovereign_capital_runtime,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_sovereign_reasoning_request import (
    build_sovereign_reasoning_request,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Success


@dataclass(frozen=True, slots=True)
class CiboReasonedSovereignCapitalDecision:
    consultation: CiboEconomicConsultationReceipt
    reasoning_request: CiboReasoningRequest
    reasoning: CiboAdaptiveReasoningRuntimeResult
    capital: CiboSovereignCapitalDecision

    def __post_init__(self) -> None:
        if not isinstance(self.consultation, CiboEconomicConsultationReceipt):
            raise CiboCapitalManagementError(
                "reasoned sovereign decision consultation is invalid"
            )
        if not isinstance(self.reasoning_request, CiboReasoningRequest):
            raise CiboCapitalManagementError(
                "reasoned sovereign decision request is invalid"
            )
        if not isinstance(self.reasoning, CiboAdaptiveReasoningRuntimeResult):
            raise CiboCapitalManagementError(
                "reasoned sovereign decision reasoning result is invalid"
            )
        if not isinstance(self.capital, CiboSovereignCapitalDecision):
            raise CiboCapitalManagementError(
                "reasoned sovereign decision capital result is invalid"
            )
        if (
            self.reasoning.runtime_result.synthesis
            != self.capital.synthesis
        ):
            raise CiboCapitalManagementError(
                "reasoning synthesis/capital synthesis drift"
            )
        if self.consultation != self.capital.faculty_consultation:
            raise CiboCapitalManagementError(
                "reasoning/capital faculty consultation drift"
            )


def run_cibo_reasoned_sovereign_capital_runtime(
    *,
    decision_id: str,
    option_id: str,
    opportunity: TraderOpportunityEnvelope,
    reasoning_runtime: CiboAdaptiveReasoningRuntime,
    reasoning_completed_at: datetime,
    twin: CiboObservedEconomicTwin,
    world_paths: tuple[Genc11WorldPath, ...],
    option_schedules: tuple[Genc11KnownOptionSchedule, ...],
    mission_policy: CiboCapitalMissionPolicy,
    capital: CiboCapitalState,
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    request_id: str,
    requested_at: datetime,
    expires_at: datetime,
    lifecycle_requests: tuple[CiboLifecycleWireRequest, ...] = (),
) -> CiboReasonedSovereignCapitalDecision:
    """Execute the complete CIBO intelligence-to-capital chain."""

    if not isinstance(reasoning_runtime, CiboAdaptiveReasoningRuntime):
        raise CiboCapitalManagementError(
            "reasoned sovereign runtime requires adaptive reasoning runtime"
        )
    if (
        not isinstance(reasoning_completed_at, datetime)
        or reasoning_completed_at.tzinfo is None
        or reasoning_completed_at.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            "reasoned sovereign completion time must be timezone-aware"
        )
    if reasoning_completed_at < twin.captured_at:
        raise CiboCapitalManagementError(
            "reasoning cannot complete before observed causal state"
        )
    if requested_at < reasoning_completed_at:
        raise CiboCapitalManagementError(
            "Risk request cannot predate completed CIBO reasoning"
        )

    consultation = consult_cibo_economic_faculties(
        decision_at=twin.captured_at,
        opportunities=(opportunity,),
        regime_state=regime_state,
        evidence_ref=evidence_ref,
    )
    reasoning_request = build_sovereign_reasoning_request(
        consultation=consultation,
        opportunity=opportunity,
    )
    reasoned = reasoning_runtime.run(
        reasoning_request,
        synthesized_at=reasoning_completed_at,
    )
    if not isinstance(reasoned, Success):
        raise CiboCapitalManagementError(
            "CIBO adaptive reasoning failed closed before capital decision"
        )
    reasoning = reasoned.value

    capital_decision = run_cibo_sovereign_capital_runtime(
        decision_id=decision_id,
        option_id=option_id,
        opportunity=opportunity,
        synthesis=reasoning.runtime_result.synthesis,
        twin=twin,
        world_paths=world_paths,
        option_schedules=option_schedules,
        mission_policy=mission_policy,
        capital=capital,
        regime_state=regime_state,
        evidence_ref=evidence_ref,
        faculty_consultation=consultation,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
        request_id=request_id,
        requested_at=requested_at,
        expires_at=expires_at,
        lifecycle_requests=lifecycle_requests,
    )

    return CiboReasonedSovereignCapitalDecision(
        consultation=consultation,
        reasoning_request=reasoning_request,
        reasoning=reasoning,
        capital=capital_decision,
    )
