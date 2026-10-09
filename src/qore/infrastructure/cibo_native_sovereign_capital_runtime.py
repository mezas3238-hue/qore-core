"""Native-only sovereign CIBO intelligence-to-capital runtime.

Maximum Capability path:
native Trader perception
-> sovereign CF01-CF19
-> native maximum-intelligence synthesis
-> sovereign capital runtime
-> QORE Risk request boundary

No GPT/OpenAI/TERRA/SOL/external reasoning provider is imported or invoked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import CiboCapitalMissionPolicy
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_economic_engine_wiring import CiboLifecycleWireRequest
from qore.infrastructure.cibo_full_economic_digital_twin import CiboObservedEconomicTwin
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
)
from qore.infrastructure.cibo_native_mode_authority import (
    NativeSovereignModeInstruction, issue_native_sovereign_mode_instruction,
)
from qore.infrastructure.cibo_native_max_mpc_bridge import (
    build_native_max_mpc_inputs,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    CiboNativeMaximumIntelligenceResult,
    run_native_maximum_intelligence,
)
from qore.infrastructure.cibo_sovereign_capital_runtime import (
    CiboSovereignCapitalDecision,
    run_cibo_sovereign_capital_runtime,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef


@dataclass(frozen=True, slots=True)
class CiboNativeSovereignCapitalDecision:
    consultation: CiboEconomicConsultationReceipt
    intelligence: CiboNativeMaximumIntelligenceResult
    capital: CiboSovereignCapitalDecision
    native_mpc_derived_from_cognition: bool = False
    mpc_world_path_ids: tuple[str, ...] = ()
    target_signal_fingerprint: str = ""  # explicit for simultaneous Trader epochs

    def __post_init__(self) -> None:
        if not isinstance(self.consultation, CiboEconomicConsultationReceipt):
            raise CiboCapitalManagementError(
                "native sovereign decision consultation is invalid"
            )
        if not isinstance(
            self.intelligence,
            CiboNativeMaximumIntelligenceResult,
        ):
            raise CiboCapitalManagementError(
                "native sovereign decision intelligence result is invalid"
            )
        if not isinstance(self.capital, CiboSovereignCapitalDecision):
            raise CiboCapitalManagementError(
                "native sovereign decision capital result is invalid"
            )
        if self.intelligence.synthesis != self.capital.synthesis:
            raise CiboCapitalManagementError(
                "native intelligence/capital synthesis drift"
            )
        if self.consultation != self.capital.faculty_consultation:
            raise CiboCapitalManagementError(
                "native intelligence/capital consultation drift"
            )
        if (
            not self.intelligence.native_only
            or self.intelligence.external_ai_call_count != 0
            or self.intelligence.external_reasoning_provider_used
        ):
            raise CiboCapitalManagementError(
                "native sovereign path cannot depend on external AI"
            )
        if type(self.native_mpc_derived_from_cognition) is not bool:
            raise CiboCapitalManagementError(
                "native sovereign MPC derivation flag must be bool"
            )
        if (
            len(self.mpc_world_path_ids)
            != len(set(self.mpc_world_path_ids))
            or any(not item for item in self.mpc_world_path_ids)
        ):
            raise CiboCapitalManagementError(
                "native sovereign MPC world ids must be unique/non-empty"
            )
        if self.native_mpc_derived_from_cognition and len(
            self.mpc_world_path_ids
        ) != 4:
            raise CiboCapitalManagementError(
                "native-derived MPC must consume all four Native MAX scenarios"
            )

    @property
    def native_qdle_mode_instruction(self) -> NativeSovereignModeInstruction:
        """CIBO-owned management direction for EVERY cognition-processed signal.

        Independent of historical disposition/legacy admission. The four motors
        and sole physical QDLE still determine whether a lot can be financed.
        """
        capital = self.capital
        signal = self.target_signal_fingerprint
        if not signal:
            if len(self.consultation.opportunity_fingerprints) != 1:
                raise CiboCapitalManagementError(
                    "sovereign Native MAX QDLE needs target signal in shared epoch"
                )
            signal = self.consultation.opportunity_fingerprints[0]
        if signal not in self.consultation.opportunity_fingerprints:
            raise CiboCapitalManagementError(
                "sovereign Native MAX QDLE signal outside cognitive surface"
            )
        return issue_native_sovereign_mode_instruction(
            episode=self.intelligence.cognitive_episode,
            signal_fingerprint=signal,
            trader_id=capital.final_plan.trader_id.value,
            decided_at=self.consultation.decision_at,
            semantic_digest=self.intelligence.semantic_digest,
        )


def run_cibo_native_sovereign_capital_runtime(
    *,
    decision_id: str,
    option_id: str,
    opportunity: TraderOpportunityEnvelope,
    simultaneous_opportunities: tuple[TraderOpportunityEnvelope, ...] = (),
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
    portfolio_fixed_multiplier: int | None = None,
    lifecycle_requests: tuple[CiboLifecycleWireRequest, ...] = (),
    peak_realized_capital_usd: Decimal | None = None,
) -> CiboNativeSovereignCapitalDecision:
    """Execute CIBO native MAX intelligence before every capital decision."""

    shared = (
        simultaneous_opportunities
        if simultaneous_opportunities
        else (opportunity,)
    )
    if any(
        not isinstance(item, TraderOpportunityEnvelope)
        for item in shared
    ):
        raise CiboCapitalManagementError(
            "native sovereign shared opportunities must be canonical"
        )
    fingerprints = tuple(item.signal_fingerprint for item in shared)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "native sovereign shared opportunities contain duplicates"
        )
    if opportunity.signal_fingerprint not in fingerprints:
        raise CiboCapitalManagementError(
            "native sovereign target absent from shared opportunity surface"
        )
    if regime_state.opportunity_count != len(shared):
        raise CiboCapitalManagementError(
            "native sovereign regime/shared-opportunity count drift"
        )

    consultation = consult_cibo_economic_faculties(
        decision_at=twin.captured_at,
        opportunities=shared,
        regime_state=regime_state,
        evidence_ref=evidence_ref,
    )
    intelligence = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=shared,
        target=opportunity,
        regime_state=regime_state,
    )

    if bool(world_paths) != bool(option_schedules):
        raise CiboCapitalManagementError(
            "native sovereign MPC worlds/schedules must be supplied together"
        )
    native_mpc_derived = False
    effective_world_paths = world_paths
    effective_option_schedules = option_schedules
    if not effective_world_paths:
        (
            effective_world_paths,
            effective_option_schedules,
        ) = build_native_max_mpc_inputs(
            episode=intelligence.cognitive_episode,
            twin=twin,
        )
        native_mpc_derived = True

    capital_decision = run_cibo_sovereign_capital_runtime(
        decision_id=decision_id,
        option_id=option_id,
        opportunity=opportunity,
        synthesis=intelligence.synthesis,
        twin=twin,
        world_paths=effective_world_paths,
        option_schedules=effective_option_schedules,
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
        portfolio_fixed_multiplier=portfolio_fixed_multiplier,
        lifecycle_requests=lifecycle_requests,
        peak_realized_capital_usd=peak_realized_capital_usd,
    )

    return CiboNativeSovereignCapitalDecision(
        consultation=consultation,
        intelligence=intelligence,
        capital=capital_decision,
        native_mpc_derived_from_cognition=native_mpc_derived,
        mpc_world_path_ids=tuple(
            item.path_id for item in effective_world_paths
        ),
        target_signal_fingerprint=opportunity.signal_fingerprint,
    )
