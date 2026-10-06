"""Predecision Native MAX epoch for chronological historical ceiling replay.

The provider plane is an explicit counterfactual research assumption.  It is
never represented as observed broker history.  Current realized capital,
already-open risk and provider-cost reserves come only from the chronological
historical capital ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_ceiling_ablation import CiboCeilingAblationMode
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
    CiboCeilingOpportunityEvidence,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    CiboHistoricalResearchCapitalState,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_state import (
    CiboHistoricalCeilingEpochState,
    build_historical_ceiling_epoch_state,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_executor import (
    CiboSovereignCeilingEpochResult,
    execute_sovereign_ceiling_epoch,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef


@dataclass(frozen=True, slots=True)
class CiboHistoricalProviderAssumption:
    risk_headroom_multiple_of_equity: Decimal = Decimal("1")
    max_risk_multiple_of_equity: Decimal = Decimal("1")
    margin_capacity_multiple_of_equity: Decimal = Decimal("100")
    active_mll_usd: Decimal = Decimal(0)
    hard_breach: bool = False

    def __post_init__(self) -> None:
        for name in (
            "risk_headroom_multiple_of_equity",
            "max_risk_multiple_of_equity",
            "margin_capacity_multiple_of_equity",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"historical ceiling provider {name} must be positive"
                )
        if (
            not isinstance(self.active_mll_usd, Decimal)
            or not self.active_mll_usd.is_finite()
            or self.active_mll_usd < 0
        ):
            raise CiboCapitalManagementError(
                "historical ceiling provider active MLL must be non-negative"
            )
        if type(self.hard_breach) is not bool:
            raise CiboCapitalManagementError(
                "historical ceiling provider hard_breach must be bool"
            )


@dataclass(frozen=True, slots=True)
class _HistoricalProviderBudget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


@dataclass(frozen=True, slots=True)
class CiboPreparedHistoricalSovereignCeilingEpoch:
    epoch_state: CiboHistoricalCeilingEpochState
    risk_snapshot: AccountRiskSnapshot
    execution: CiboSovereignCeilingEpochResult


def run_predecision_historical_sovereign_ceiling_epoch(
    *,
    decision_epoch_id: str,
    decision_at: datetime,
    expires_at: datetime,
    account_identity: CiboAccountCapitalIdentity,
    historical_capital: CiboHistoricalResearchCapitalState,
    open_exposures: tuple[CiboCeilingOpenExposure, ...],
    opportunities: tuple[CiboCeilingOpportunityEvidence, ...],
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
    mission_policy: CiboCapitalMissionPolicy,
    risk_engine: AccountWideRiskEngine,
    provider_assumption: CiboHistoricalProviderAssumption,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    ablation_mode: CiboCeilingAblationMode = CiboCeilingAblationMode.FULL,
) -> CiboPreparedHistoricalSovereignCeilingEpoch:
    """Execute one historical epoch without reading any settlement outcome."""

    if not decision_epoch_id:
        raise CiboCapitalManagementError(
            "historical ceiling decision_epoch_id is required"
        )
    if not isinstance(
        provider_assumption,
        CiboHistoricalProviderAssumption,
    ):
        raise CiboCapitalManagementError(
            "historical ceiling provider assumption must be canonical"
        )

    realized = historical_capital.realized_capital_usd
    provider_cost_reserve = (
        historical_capital.open_provider_cost_reserve_usd
    )
    with localcontext() as context:
        context.prec = 100
        stop_capacity = max(
            Decimal(0),
            realized - provider_cost_reserve,
        )
        provider_risk_headroom = (
            realized
            * provider_assumption.risk_headroom_multiple_of_equity
        )
        provider_max_risk = (
            realized
            * provider_assumption.max_risk_multiple_of_equity
        )
        gross_margin_capacity = (
            realized
            * provider_assumption.margin_capacity_multiple_of_equity
        )
        effective_margin_capacity = max(
            Decimal(0),
            gross_margin_capacity - provider_cost_reserve,
        )

    if historical_capital.open_stop_risk_usd > stop_capacity:
        raise CiboCapitalManagementError(
            "historical ceiling current open risk exceeds realizable capital"
        )
    if historical_capital.open_margin_usd > effective_margin_capacity:
        raise CiboCapitalManagementError(
            "historical ceiling current margin exceeds provider assumption"
        )

    epoch = build_historical_ceiling_epoch_state(
        account_identity=account_identity,
        historical_capital=historical_capital,
        captured_at=decision_at,
        expires_at=expires_at,
        opportunities=opportunities,
        open_exposures=open_exposures,
        total_stop_risk_capacity_usd=stop_capacity,
        total_margin_capacity_usd=effective_margin_capacity,
    )

    qore_total_authorizable = min(
        stop_capacity,
        provider_risk_headroom,
        provider_max_risk,
    )
    provider_budget = _HistoricalProviderBudget(
        provider_headroom=provider_risk_headroom,
        max_risk_at_any_time=provider_max_risk,
        active_mll=provider_assumption.active_mll_usd,
        hard_breach=provider_assumption.hard_breach,
    )
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_identity.account_ref,
        equity=realized,
        margin_used=historical_capital.open_margin_usd,
        free_margin=epoch.capital_twin.margin_headroom_usd,
        open_stop_worst_case_loss=historical_capital.open_stop_risk_usd,
        open_floating_loss=Decimal(0),
        pending_broker_worst_case_loss=Decimal(0),
        # AccountWideRiskEngine subtracts current open/pending risk from
        # this value, so this is the total internal account limit, not the
        # already-remaining headroom exposed by the capital twin.
        qore_authorizable_headroom=qore_total_authorizable,
        provider_budget=provider_budget,
        reconciled_at=decision_at,
    )

    envelopes = tuple(item.opportunity for item in opportunities)
    execution = execute_sovereign_ceiling_epoch(
        decision_epoch_id=decision_epoch_id,
        decision_at=decision_at,
        expires_at=expires_at,
        opportunities=envelopes,
        option_id_by_signal=tuple(
            (
                item.signal_fingerprint,
                item.signal_fingerprint,
            )
            for item in envelopes
        ),
        twin=epoch.twin,
        capital=epoch.capital,
        regime_state=regime_state,
        evidence_ref=evidence_ref,
        mission_policy=mission_policy,
        risk_snapshot=snapshot,
        risk_engine=risk_engine,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
        ablation_mode=ablation_mode,
    )
    return CiboPreparedHistoricalSovereignCeilingEpoch(
        epoch_state=epoch,
        risk_snapshot=snapshot,
        execution=execution,
    )
