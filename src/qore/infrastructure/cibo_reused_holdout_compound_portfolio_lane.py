"""Compound + portfolio-compound ablation for the reused USD60 capability exam.

The treatment consumes the exact FULL_CIBO_CORE selection surface. It may add
only an incremental minimum executable seed funded by profit that was already
realized before the decision epoch. Positive Core settlements and earlier
compound settlements form one account-local pool, so capital can be redeployed
across Traders without changing Trader edge or the Core selection.

QORE Risk remains sovereign over every incremental request. Capital Science
predecision evaluation consumes the enabled native GEN-C engines from the
runtime bridge; no function is hidden by historical replay time or TEST mission.
This is a NON_CERTIFYING_REUSED_HOLDOUT research lane and grants no
broker/LIVE/real/production/merge authority. GEN-C10 conservation checks are
precision-safe so high-precision replay balances do not disable native engines;
the runtime bridge preserves those balances and utilization ratios with expanded
Decimal precision, including GEN-C10 observed and projected world-capacity conservation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    RiskDecision,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CiboCapitalManagementError,
    CiboCapitalState,
    minimum_seed_volume,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capital_science_runtime_bridge import (
    CapitalScienceDisposition,
    CapitalScienceDirective,
    CapitalScienceKnownOpportunity,
    CapitalScienceOpenEconomicPosition,
    CapitalSciencePredecisionInput,
    CapitalScienceReceipt,
    aggregate_capital_science_receipts,
    build_capital_science_lane_receipt,
    build_capital_science_postrun_receipts,
    evaluate_capital_science_predecision,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    execution_efficient_volume_cap,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalExecutionReport,
    Phase22HistoricalRegimeEvidence,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    Genc7PreservationProposalEvidence,
    Genc7SourceBucket,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    POLICY_ID,
    maximum_reinvestment_capital_need_usd,
    protected_loss_reserve_usd,
    protected_reinvestment_candidate_allowed,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

LANE_ID = "FULL_CIBO_COMPOUND_PORTFOLIO"
POOL_SCOPE_ACCOUNT = "ACCOUNT"
POOL_SCOPE_TRADER_LOCAL = "TRADER_LOCAL"


@dataclass(frozen=True, slots=True)
class CompoundRedeployAuthorization:
    """Fresh/OOS predecision evidence for productive-policy qualification."""

    signal_fingerprint: str
    known_at: datetime
    evidence_id: str
    marginal_utility_oos: bool
    profit_preservation_ready: bool
    adaptive_speed_ready: bool
    growth_ruin_ready: bool
    forward_controller_ready: bool
    crisis_governance_ready: bool
    policy_authorized: bool

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.evidence_id:
            raise CiboCapitalManagementError("compound redeploy authorization identity required")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound redeploy authorization known_at must be timezone-aware"
            )
        prerequisites = (
            self.marginal_utility_oos,
            self.profit_preservation_ready,
            self.adaptive_speed_ready,
            self.growth_ruin_ready,
            self.forward_controller_ready,
            self.crisis_governance_ready,
        )
        if any(type(item) is not bool for item in (*prerequisites, self.policy_authorized)):
            raise CiboCapitalManagementError("compound redeploy authorization flags must be bool")
        if self.policy_authorized and not all(prerequisites):
            raise CiboCapitalManagementError(
                "compound redeploy policy cannot outrun GEN-C readiness"
            )


@dataclass(frozen=True, slots=True)
class CompoundResearchRedeployAuthorization:
    """Research-only causal redeploy permission for reused-holdout capability work.

    This contract exists specifically so a reused holdout never has to lie by
    setting marginal_utility_oos=True. It cannot grant productive authority.
    Candidate admission remains independently governed by the frozen protected
    reinvestment policy plus CMA and sovereign QORE Risk.
    """

    signal_fingerprint: str
    known_at: datetime
    evidence_id: str
    policy_id: str
    calibration_mode: str
    research_redeploy_authorized: bool = True
    fresh_oos_utility_demonstrated: bool = False
    certification_claimed: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.evidence_id or not self.policy_id:
            raise CiboCapitalManagementError("compound research redeploy identity required")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound research redeploy known_at must be timezone-aware"
            )
        if self.calibration_mode != "NON_CERTIFYING_REUSED_HOLDOUT":
            raise CiboCapitalManagementError(
                "compound research redeploy requires reused-holdout calibration"
            )
        flags = (
            self.research_redeploy_authorized,
            self.fresh_oos_utility_demonstrated,
            self.certification_claimed,
            self.broker_mutation_authorized,
            self.live_authorized,
            self.real_capital_authorized,
            self.production_authorized,
        )
        if any(type(item) is not bool for item in flags):
            raise CiboCapitalManagementError("compound research redeploy flags must be bool")
        if (
            not self.research_redeploy_authorized
            or self.fresh_oos_utility_demonstrated
            or self.certification_claimed
            or self.broker_mutation_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
        ):
            raise CiboCapitalManagementError("compound research redeploy governance contamination")


@dataclass(frozen=True, slots=True)
class _Budget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


@dataclass(slots=True)
class _Open:
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    side: str
    entry_at: datetime
    exit_at: datetime
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    authorization_id: str
    authorized_volume: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    gross_structural_outcome_r: Decimal
    provider_cost_usd: Decimal
    entry_expected_net_value_usd: Decimal
    entry_expected_capital_minutes: Decimal
    expectation_evidence_sha256: str
    protected_loss_reserve_usd: Decimal
    source_traders_before_entry: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompoundPortfolioTrade:
    signal_fingerprint: str
    trader_id: str
    exit_at: datetime
    authorized_volume: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    gross_structural_outcome_r: Decimal
    provider_cost_usd: Decimal
    incremental_realized_pnl_usd: Decimal
    source_traders_before_entry: tuple[str, ...]
    cross_trader_pool_used: bool

    def payload(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = format(value, "f")
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


@dataclass(frozen=True, slots=True)
class CompoundT06ExpansionDecision:
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    requested_volume: Decimal
    authorized_volume: Decimal
    requested_stop_risk_usd: Decimal
    authorized_stop_risk_usd: Decimal
    requested_margin_usd: Decimal
    authorized_margin_usd: Decimal
    action: str
    capital_source: str | None
    reason: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id or not self.reason:
            raise CiboCapitalManagementError(
                "compound T06 decision identity/reason required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound T06 decision_at must be timezone-aware"
            )
        for name in (
            "requested_volume",
            "authorized_volume",
            "requested_stop_risk_usd",
            "authorized_stop_risk_usd",
            "requested_margin_usd",
            "authorized_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"compound T06 {name} must be finite non-negative Decimal"
                )
        if self.authorized_volume > self.requested_volume:
            raise CiboCapitalManagementError(
                "compound T06 may not increase the requested exposure"
            )
        if self.action not in {
            CapitalAction.EXPAND.value,
            CapitalAction.HOLD.value,
        }:
            raise CiboCapitalManagementError("compound T06 action invalid")
        if (
            self.action == CapitalAction.EXPAND.value
            and self.capital_source
            not in {
                CapitalSource.REALIZED_PROFIT.value,
                CapitalSource.PROTECTED_ECONOMIC_FLOOR.value,
            }
        ):
            raise CiboCapitalManagementError(
                "compound T06 expansion must use proven non-base capital"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "decision_at": self.decision_at.isoformat(),
            "requested_volume": format(self.requested_volume, "f"),
            "authorized_volume": format(self.authorized_volume, "f"),
            "requested_stop_risk_usd": format(
                self.requested_stop_risk_usd, "f"
            ),
            "authorized_stop_risk_usd": format(
                self.authorized_stop_risk_usd, "f"
            ),
            "requested_margin_usd": format(self.requested_margin_usd, "f"),
            "authorized_margin_usd": format(self.authorized_margin_usd, "f"),
            "action": self.action,
            "capital_source": self.capital_source,
            "reason": self.reason,
            "causal_predecision": True,
            "outcome_used": False,
            "broker_mutation": False,
            "risk_authority": False,
        }


@dataclass(frozen=True, slots=True)
class CompoundT14DeRiskDecision:
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    pre_volume: Decimal
    retained_volume: Decimal
    reduction_volume: Decimal
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    retention_factor: Decimal
    action: str
    reason: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id or not self.reason:
            raise CiboCapitalManagementError(
                "compound T14 decision identity/reason required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound T14 decision_at must be timezone-aware"
            )
        for name in (
            "pre_volume",
            "retained_volume",
            "reduction_volume",
            "released_stop_risk_usd",
            "released_margin_usd",
            "retention_factor",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"compound T14 {name} must be finite non-negative Decimal"
                )
        if self.retention_factor > 1:
            raise CiboCapitalManagementError(
                "compound T14 retention factor cannot exceed one"
            )
        if self.action not in {
            CiboDeRiskAction.HOLD.value,
            CiboDeRiskAction.REDUCE.value,
            CiboDeRiskAction.RELEASE_ALL.value,
        }:
            raise CiboCapitalManagementError("compound T14 action invalid")
        if self.retained_volume + self.reduction_volume != self.pre_volume:
            raise CiboCapitalManagementError(
                "compound T14 volume conservation drift"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "decision_at": self.decision_at.isoformat(),
            "pre_volume": format(self.pre_volume, "f"),
            "retained_volume": format(self.retained_volume, "f"),
            "reduction_volume": format(self.reduction_volume, "f"),
            "released_stop_risk_usd": format(
                self.released_stop_risk_usd,
                "f",
            ),
            "released_margin_usd": format(self.released_margin_usd, "f"),
            "retention_factor": format(self.retention_factor, "f"),
            "action": self.action,
            "reason": self.reason,
            "causal_predecision": True,
            "outcome_used": False,
            "broker_mutation": False,
            "risk_authority": False,
        }


@dataclass(frozen=True, slots=True)
class CompoundLeverageDecision:
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    requested_multiplier: Decimal
    effective_multiplier: Decimal
    genc8_posture: str
    t11_requested_volume: Decimal
    t11_gross_edge_per_volume_usd: Decimal
    t11_spread_cost_per_volume_usd: Decimal
    t11_commission_cost_per_volume_usd: Decimal
    t11_slippage_cost_per_volume_usd: Decimal
    t11_impact_cost_per_volume_squared_usd: Decimal
    t11_execution_cap_volume: Decimal
    t11_allows_compound: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id or not self.reason:
            raise CiboCapitalManagementError(
                "compound leverage decision identity/reason required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound leverage decision_at must be timezone-aware"
            )
        for name in (
            "requested_multiplier",
            "effective_multiplier",
            "t11_requested_volume",
            "t11_spread_cost_per_volume_usd",
            "t11_commission_cost_per_volume_usd",
            "t11_slippage_cost_per_volume_usd",
            "t11_impact_cost_per_volume_squared_usd",
            "t11_execution_cap_volume",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"compound leverage {name} must be finite non-negative Decimal"
                )
        if (
            not isinstance(self.t11_gross_edge_per_volume_usd, Decimal)
            or not self.t11_gross_edge_per_volume_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "compound leverage T11 gross edge must be finite Decimal"
            )
        if self.effective_multiplier > self.requested_multiplier:
            raise CiboCapitalManagementError(
                "compound leverage cannot exceed requested multiplier"
            )
        if self.genc8_posture not in {
            "PAUSE",
            "DEFENSIVE",
            "CAUTIOUS",
            "NORMAL",
            "ACCELERATED",
            "GENC5_CANONICAL_INPUT_UNAVAILABLE",
        }:
            raise CiboCapitalManagementError(
                "compound leverage GEN-C8 posture invalid"
            )
        if type(self.t11_allows_compound) is not bool:
            raise CiboCapitalManagementError(
                "compound leverage T11 allow flag must be bool"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "decision_at": self.decision_at.isoformat(),
            "requested_multiplier": format(self.requested_multiplier, "f"),
            "effective_multiplier": format(self.effective_multiplier, "f"),
            "genc8_posture": self.genc8_posture,
            "t11_requested_volume": format(self.t11_requested_volume, "f"),
            "t11_gross_edge_per_volume_usd": format(
                self.t11_gross_edge_per_volume_usd,
                "f",
            ),
            "t11_spread_cost_per_volume_usd": format(
                self.t11_spread_cost_per_volume_usd,
                "f",
            ),
            "t11_commission_cost_per_volume_usd": format(
                self.t11_commission_cost_per_volume_usd,
                "f",
            ),
            "t11_slippage_cost_per_volume_usd": format(
                self.t11_slippage_cost_per_volume_usd,
                "f",
            ),
            "t11_impact_cost_per_volume_squared_usd": format(
                self.t11_impact_cost_per_volume_squared_usd,
                "f",
            ),
            "t11_execution_cap_volume": format(
                self.t11_execution_cap_volume,
                "f",
            ),
            "t11_allows_compound": self.t11_allows_compound,
            "reason": self.reason,
            "causal_predecision": True,
            "outcome_used": False,
        }


def _t14_compound_retention_factor(
    regime_state: CiboCapitalRegimeState | None,
) -> Decimal:
    """Return a causal retention factor for incremental compound exposure."""

    if regime_state is None:
        return Decimal(1)
    if regime_state.evidence_stale:
        return Decimal(0)
    factor = Decimal(1)
    if regime_state.provider_condition.value == "UNAVAILABLE":
        return Decimal(0)
    if regime_state.provider_condition.value == "DEGRADED":
        factor = min(factor, Decimal("0.50"))
    if regime_state.liquidity.value == "STRESSED":
        factor = min(factor, Decimal("0.50"))
    elif regime_state.liquidity.value == "THIN":
        factor = min(factor, Decimal("0.75"))
    if regime_state.volatility.value == "DISLOCATED":
        factor = min(factor, Decimal("0.50"))
    elif regime_state.volatility.value == "ELEVATED":
        factor = min(factor, Decimal("0.75"))
    if regime_state.correlation.value == "BREAK":
        factor = min(factor, Decimal("0.50"))
    elif regime_state.correlation.value == "CONCENTRATED":
        factor = min(factor, Decimal("0.75"))
    if regime_state.drawdown_utilization >= Decimal("0.50"):
        factor = min(factor, Decimal("0.50"))
    elif regime_state.drawdown_utilization >= Decimal("0.25"):
        factor = min(factor, Decimal("0.75"))
    if regime_state.position_path_adverse:
        factor = min(factor, Decimal("0.50"))
    return factor


_GENC8_MULTIPLIER_CAP = {
    "PAUSE": Decimal(0),
    "DEFENSIVE": Decimal(1),
    "CAUTIOUS": Decimal(1),
    "NORMAL": Decimal(2),
    "ACCELERATED": Decimal(4),
    "GENC5_CANONICAL_INPUT_UNAVAILABLE": Decimal(0),
}


def _compound_scarcity_score(
    candidate: object,
    *,
    decision_at: datetime,
) -> Decimal:
    opportunity = candidate.projection.candidate.capital_input.opportunity
    volume = minimum_seed_volume(opportunity)
    risk = volume * opportunity.stop_loss_per_volume
    cost = (
        candidate.projection.provider_envelope.execution_cost_per_volume_usd
        * volume
    )
    expectation = build_frozen_train_expectation(
        trader_id=opportunity.trader_id,
        stop_risk_usd=risk,
        as_of=decision_at,
    )
    capital_need = risk + cost
    if capital_need <= 0:
        return Decimal("-Infinity")
    return expectation.expected_net_value_usd / capital_need


def _lane_owned_capital_science_receipts(
    *,
    state: CapitalSciencePredecisionInput,
    funding_pool_usd: Decimal,
    available_profit_usd: Decimal,
    pool_scope: str,
    source_traders: set[str],
    current_trader: str,
    scarcity_rank: int,
    scarcity_count: int,
    scarcity_score: Decimal,
    scarcity_order_changed: bool,
    dynamic_leverage: bool,
) -> tuple[CapitalScienceReceipt, ...]:
    profit_available = funding_pool_usd > 0 and available_profit_usd > 0
    genc1 = build_capital_science_lane_receipt(
        state=state,
        function_code="GEN-C1",
        disposition=(
            CapitalScienceDisposition.APPLIED
            if profit_available
            else CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
        ),
        reason=(
            "causally prior realized profit is available for incremental compound"
            if profit_available
            else "no causally prior deployable realized profit is available"
        ),
        downstream_consumer="CIBO_COMPOUND_FUNDING_POOL",
        consumer_action=(
            "REALIZED_PROFIT_CAPACITY_AVAILABLE"
            if profit_available
            else "NO_REALIZED_PROFIT_CAPACITY"
        ),
        decision_changed=profit_available,
        capital_source_usage=(("REALIZED_PROFIT",) if profit_available else ()),
        output_details={
            "funding_pool_usd": format(funding_pool_usd, "f"),
            "available_profit_usd": format(available_profit_usd, "f"),
        },
        native_engine_name="evaluate_genc1_realized_profit_eligibility",
    )

    cross_sources = tuple(
        sorted(source for source in source_traders if source != current_trader)
    )
    genc3_applied = (
        pool_scope == POOL_SCOPE_ACCOUNT
        and funding_pool_usd > 0
        and bool(cross_sources)
    )
    genc3 = build_capital_science_lane_receipt(
        state=state,
        function_code="GEN-C3",
        disposition=(
            CapitalScienceDisposition.APPLIED
            if genc3_applied
            else (
                CapitalScienceDisposition.ELIGIBLE_NO_CHANGE
                if pool_scope == POOL_SCOPE_ACCOUNT
                else CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
            )
        ),
        reason=(
            "account-local realized-profit pool contains capacity realized by "
            "other Trader lineages"
            if genc3_applied
            else (
                "account pool evaluated but no cross-Trader realized-profit source "
                "is currently available"
                if pool_scope == POOL_SCOPE_ACCOUNT
                else "Trader-local compound intentionally disables cross-Trader pooling"
            )
        ),
        downstream_consumer="CIBO_COMPOUND_PORTFOLIO_POOL",
        consumer_action=(
            "CROSS_TRADER_CAPACITY_AVAILABLE"
            if genc3_applied
            else "ACCOUNT_POOL_NO_CROSS_TRADER_CHANGE"
            if pool_scope == POOL_SCOPE_ACCOUNT
            else "TRADER_LOCAL_SCOPE"
        ),
        decision_changed=genc3_applied,
        capital_source_usage=(("REALIZED_PROFIT",) if funding_pool_usd > 0 else ()),
        output_details={
            "pool_scope": pool_scope,
            "cross_source_traders": list(cross_sources),
        },
        native_engine_name="evaluate_genc3_account_pool_eligibility",
    )

    scarcity_applied = (
        dynamic_leverage
        and pool_scope == POOL_SCOPE_ACCOUNT
        and scarcity_count > 1
    )
    genc6 = build_capital_science_lane_receipt(
        state=state,
        function_code="GEN-C6",
        disposition=(
            CapitalScienceDisposition.APPLIED
            if scarcity_applied
            else CapitalScienceDisposition.JUSTIFIED_NOT_APPLICABLE
        ),
        reason=(
            "causal frozen-prior utility ranked simultaneous Compound Portfolio "
            "claims before scarce realized-profit deployment"
            if scarcity_applied
            else "no account-level simultaneous scarcity auction was required"
        ),
        downstream_consumer="CIBO_COMPOUND_PORTFOLIO_ALLOCATION_ORDER",
        consumer_action=(
            f"SCARCITY_RANK_{scarcity_rank}_OF_{scarcity_count}"
            if scarcity_applied
            else "NO_SCARCITY_AUCTION"
        ),
        decision_changed=scarcity_applied and scarcity_order_changed,
        capital_source_usage=(("REALIZED_PROFIT",) if scarcity_applied else ()),
        output_details={
            "scarcity_rank": scarcity_rank,
            "scarcity_count": scarcity_count,
            "scarcity_score": format(scarcity_score, "f"),
            "order_changed": scarcity_order_changed,
        },
        native_engine_name="evaluate_genc6_internal_capital_market",
    )
    return (genc1, genc3, genc6)


def _known_options_with_current_geometry(
    options: tuple[CapitalScienceKnownOpportunity, ...],
    *,
    signal_fingerprint: str,
    stop_risk_usd: Decimal,
    margin_usd: Decimal,
    provider_cost_usd: Decimal,
) -> tuple[CapitalScienceKnownOpportunity, ...]:
    matches = tuple(
        item for item in options if item.option_id == signal_fingerprint
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "compound current signal must exist exactly once in epoch options"
        )
    return tuple(
        replace(
            item,
            requested_capital_usd=stop_risk_usd + provider_cost_usd,
            stop_risk_usd=stop_risk_usd,
            margin_usd=margin_usd,
        )
        if item.option_id == signal_fingerprint
        else item
        for item in options
    )


def _genc8_posture(capital_science: object) -> str:
    receipts = tuple(
        item
        for item in getattr(capital_science, "receipts", ())
        if item.function_code == "GEN-C8"
    )
    if len(receipts) != 1:
        raise CiboCapitalManagementError(
            "compound dynamic leverage requires exactly one GEN-C8 receipt"
        )
    posture = receipts[0].consumer_action
    if posture not in _GENC8_MULTIPLIER_CAP:
        raise CiboCapitalManagementError(
            "compound dynamic leverage GEN-C8 posture drift"
        )
    return posture


def _t11_execution_cap(
    *,
    requested_volume: Decimal,
    expected_structural_value_usd: Decimal,
    provider_envelope: object,
) -> tuple[Decimal, str, dict[str, Decimal]]:
    """Apply causal execution economics and expose the exact consumed inputs."""

    if requested_volume <= 0:
        return (
            Decimal(0),
            "T11 requested volume is non-positive",
            {
                "requested_volume": requested_volume,
                "gross_edge_per_volume_usd": Decimal(0),
                "spread_cost_per_volume_usd": Decimal(0),
                "commission_cost_per_volume_usd": Decimal(0),
                "slippage_cost_per_volume_usd": Decimal(0),
                "impact_cost_per_volume_squared_usd": Decimal(0),
            },
        )
    structural_edge_per_volume = (
        expected_structural_value_usd / requested_volume
    )
    spread = provider_envelope.spread_cost_per_volume_usd
    commission = provider_envelope.commission_per_volume_usd
    slippage = provider_envelope.slippage_reserve_per_volume_usd
    impact = (
        slippage
        / max(
            provider_envelope.maximum_volume,
            provider_envelope.volume_step,
        )
    )
    inputs = {
        "requested_volume": requested_volume,
        "gross_edge_per_volume_usd": structural_edge_per_volume,
        "spread_cost_per_volume_usd": spread,
        "commission_cost_per_volume_usd": commission,
        "slippage_cost_per_volume_usd": slippage,
        "impact_cost_per_volume_squared_usd": impact,
    }
    if structural_edge_per_volume <= 0:
        return (
            Decimal(0),
            "T11 frozen structural expectation is non-positive before execution cost",
            inputs,
        )
    curve = ExecutionCostCurveInput(
        evidence_id="cibo-burned-research-linear-provider-economics",
        volume_step=provider_envelope.volume_step,
        maximum_volume=requested_volume,
        gross_edge_per_volume_usd=structural_edge_per_volume,
        spread_cost_per_volume_usd=spread,
        commission_cost_per_volume_usd=commission,
        slippage_cost_per_volume_usd=slippage,
        impact_cost_per_volume_squared_usd=impact,
    )
    cap = execution_efficient_volume_cap(curve)
    return (
        cap.volume_cap,
        (
            cap.reason
            + "; nonlinear impact uses the preregistered provider-slippage upper-bound "
            "proxy and carries no empirical-certification claim"
        ),
        inputs,
    )


@dataclass(frozen=True, slots=True)
class CompoundPortfolioShadowDecision:
    signal_fingerprint: str
    trader_id: str
    decision_at: datetime
    open_position_count: int
    allocation_multiplier: int
    allocation_expected_net_utility_usd: Decimal
    position_competition_observed: bool
    fits_without_release: bool
    release_proposed: bool
    proposed_released_stop_risk_usd: Decimal
    proposed_released_margin_usd: Decimal
    net_incremental_utility_usd: Decimal
    admit_opportunity: bool

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id:
            raise CiboCapitalManagementError(
                "portfolio shadow identity required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "portfolio shadow decision_at must be timezone-aware"
            )
        if (
            not isinstance(self.open_position_count, int)
            or isinstance(self.open_position_count, bool)
            or self.open_position_count < 0
        ):
            raise CiboCapitalManagementError(
                "portfolio shadow open_position_count invalid"
            )
        if self.allocation_multiplier not in {0, 1, 2, 3, 4}:
            raise CiboCapitalManagementError(
                "portfolio shadow allocation multiplier outside 0..4"
            )
        for name in (
            "allocation_expected_net_utility_usd",
            "proposed_released_stop_risk_usd",
            "proposed_released_margin_usd",
            "net_incremental_utility_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"portfolio shadow {name} must be finite Decimal"
                )
        if (
            self.proposed_released_stop_risk_usd < 0
            or self.proposed_released_margin_usd < 0
        ):
            raise CiboCapitalManagementError(
                "portfolio shadow release capacity cannot be negative"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "decision_at": self.decision_at.isoformat(),
            "open_position_count": self.open_position_count,
            "allocation_multiplier": self.allocation_multiplier,
            "allocation_expected_net_utility_usd": format(
                self.allocation_expected_net_utility_usd,
                "f",
            ),
            "position_competition_observed": self.position_competition_observed,
            "fits_without_release": self.fits_without_release,
            "release_proposed": self.release_proposed,
            "proposed_released_stop_risk_usd": format(
                self.proposed_released_stop_risk_usd,
                "f",
            ),
            "proposed_released_margin_usd": format(
                self.proposed_released_margin_usd,
                "f",
            ),
            "net_incremental_utility_usd": format(
                self.net_incremental_utility_usd,
                "f",
            ),
            "admit_opportunity": self.admit_opportunity,
            "shadow_only": True,
            "risk_authority": False,
            "execution_authority": False,
        }


def _portfolio_shadow_decision(
    *,
    state: CapitalSciencePredecisionInput,
    directive: CapitalScienceDirective,
) -> CompoundPortfolioShadowDecision:
    allocation_line = next(
        (
            item
            for item in (
                directive.portfolio_allocation_plan.lines
                if directive.portfolio_allocation_plan is not None
                else ()
            )
            if item.option_id == state.signal_fingerprint
        ),
        None,
    )
    competition = directive.position_competition_plan
    release_proposed = bool(
        competition is not None
        and competition.admit_opportunity
        and any(
            item.proposed_action == "RELEASE"
            for item in competition.position_lines
        )
    )
    return CompoundPortfolioShadowDecision(
        signal_fingerprint=state.signal_fingerprint,
        trader_id=state.trader_id,
        decision_at=state.decision_at,
        open_position_count=len(state.open_economic_positions),
        allocation_multiplier=(
            0 if allocation_line is None else allocation_line.multiplier
        ),
        allocation_expected_net_utility_usd=(
            Decimal(0)
            if allocation_line is None
            else allocation_line.expected_net_utility_usd
        ),
        position_competition_observed=competition is not None,
        fits_without_release=(
            False if competition is None else competition.fits_without_release
        ),
        release_proposed=release_proposed,
        proposed_released_stop_risk_usd=(
            Decimal(0)
            if competition is None
            else competition.released_stop_risk_usd
        ),
        proposed_released_margin_usd=(
            Decimal(0)
            if competition is None
            else competition.released_margin_usd
        ),
        net_incremental_utility_usd=(
            Decimal(0)
            if competition is None
            else competition.net_incremental_utility_usd
        ),
        admit_opportunity=(
            allocation_line is not None
            and allocation_line.multiplier > 0
            and (
                competition is None
                or competition.admit_opportunity
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class CompoundPortfolioLaneResult:
    core_ending_capital_usd: Decimal
    compound_incremental_pnl_usd: Decimal
    ending_capital_usd: Decimal
    net_realized_pnl_usd: Decimal
    compound_selected_count: int
    compound_allowed_count: int
    compound_reduced_count: int
    compound_rejected_count: int
    compound_settled_count: int
    cross_trader_compound_deployments: int
    profit_factor: Decimal | None
    trader_incremental_pnl_usd: tuple[tuple[str, Decimal], ...]
    trader_compound_entries: tuple[tuple[str, int], ...]
    trades: tuple[CompoundPortfolioTrade, ...]
    blocker_reasons: tuple[tuple[str, int], ...]
    function_accountability: tuple[dict[str, object], ...]
    capital_science_receipts: tuple[dict[str, object], ...] = ()
    leverage_decisions: tuple[CompoundLeverageDecision, ...] = ()
    t06_expansion_decisions: tuple[CompoundT06ExpansionDecision, ...] = ()
    t14_derisk_decisions: tuple[CompoundT14DeRiskDecision, ...] = ()
    portfolio_shadow_decisions: tuple[CompoundPortfolioShadowDecision, ...] = ()
    dynamic_leverage_enabled: bool = False
    rational_redeploy_gate_enabled: bool = False
    noncertifying_research_redeploy_enabled: bool = False
    protected_reinvestment_policy_id: str = ""
    pool_scope: str = POOL_SCOPE_ACCOUNT
    seed_multiplier: Decimal = Decimal("1")
    lane_id: str = LANE_ID
    same_core_selection_surface: bool = True
    realized_profit_only: bool = True
    floating_pnl_used_as_funding: bool = False
    qore_risk_sovereign: bool = True
    outcome_aware_tuning_used: bool = False
    broker_mutation_performed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
        if self.ending_capital_usd != (
            self.core_ending_capital_usd + self.compound_incremental_pnl_usd
        ):
            raise CiboCapitalManagementError("compound lane capital identity drift")
        if self.net_realized_pnl_usd != self.ending_capital_usd - initial:
            raise CiboCapitalManagementError("compound lane PnL identity drift")
        if self.compound_selected_count != (
            self.compound_allowed_count + self.compound_reduced_count + self.compound_rejected_count
        ):
            raise CiboCapitalManagementError("compound lane Risk count drift")
        if self.compound_settled_count != (
            self.compound_allowed_count + self.compound_reduced_count
        ):
            raise CiboCapitalManagementError("compound lane settlement count drift")
        if self.compound_settled_count != len(self.trades):
            raise CiboCapitalManagementError("compound lane trade count drift")
        if type(self.dynamic_leverage_enabled) is not bool:
            raise CiboCapitalManagementError(
                "compound dynamic leverage flag must be bool"
            )
        if any(
            not isinstance(item, CompoundLeverageDecision)
            for item in self.leverage_decisions
        ):
            raise CiboCapitalManagementError(
                "compound leverage decisions must be canonical"
            )
        if any(
            not isinstance(item, CompoundT06ExpansionDecision)
            for item in self.t06_expansion_decisions
        ):
            raise CiboCapitalManagementError(
                "compound T06 decisions must be canonical"
            )
        if any(
            not isinstance(item, CompoundT14DeRiskDecision)
            for item in self.t14_derisk_decisions
        ):
            raise CiboCapitalManagementError(
                "compound T14 decisions must be canonical"
            )
        if any(
            not isinstance(item, CompoundPortfolioShadowDecision)
            for item in self.portfolio_shadow_decisions
        ):
            raise CiboCapitalManagementError(
                "compound portfolio shadow decisions must be canonical"
            )
        if type(self.rational_redeploy_gate_enabled) is not bool:
            raise CiboCapitalManagementError("compound rational redeploy gate flag must be bool")
        if type(self.noncertifying_research_redeploy_enabled) is not bool:
            raise CiboCapitalManagementError("compound research redeploy flag must be bool")
        if not isinstance(self.protected_reinvestment_policy_id, str):
            raise CiboCapitalManagementError(
                "compound protected reinvestment policy id must be str"
            )
        if self.pool_scope not in {POOL_SCOPE_ACCOUNT, POOL_SCOPE_TRADER_LOCAL}:
            raise CiboCapitalManagementError("compound pool scope invalid")
        if self.pool_scope == POOL_SCOPE_TRADER_LOCAL and self.cross_trader_compound_deployments:
            raise CiboCapitalManagementError(
                "trader-local compound cannot report cross-Trader deployment"
            )
        if (
            not isinstance(self.seed_multiplier, Decimal)
            or not self.seed_multiplier.is_finite()
            or self.seed_multiplier < 1
            or self.seed_multiplier != self.seed_multiplier.to_integral_value()
        ):
            raise CiboCapitalManagementError(
                "compound seed multiplier must be finite integer Decimal >= 1"
            )
        if not all(
            (
                self.same_core_selection_surface,
                self.realized_profit_only,
                self.qore_risk_sovereign,
            )
        ) or any(
            (
                self.floating_pnl_used_as_funding,
                self.outcome_aware_tuning_used,
                self.broker_mutation_performed,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError("compound lane governance drift")

    def payload(self, *, core_executed_count: int) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "initial_capital_usd": format(
                FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd, "f"
            ),
            "core_ending_capital_usd": format(self.core_ending_capital_usd, "f"),
            "compound_incremental_pnl_usd": format(self.compound_incremental_pnl_usd, "f"),
            "ending_capital_usd": format(self.ending_capital_usd, "f"),
            "net_realized_pnl_usd": format(self.net_realized_pnl_usd, "f"),
            "core_executed_count": core_executed_count,
            "compound_selected_count": self.compound_selected_count,
            "compound_allowed_count": self.compound_allowed_count,
            "compound_reduced_count": self.compound_reduced_count,
            "compound_rejected_count": self.compound_rejected_count,
            "compound_settled_count": self.compound_settled_count,
            "total_executed_count": core_executed_count + self.compound_settled_count,
            "cross_trader_compound_deployments": (self.cross_trader_compound_deployments),
            "profit_factor": (
                None if self.profit_factor is None else format(self.profit_factor, "f")
            ),
            "trader_incremental_pnl_usd": {
                trader: format(value, "f") for trader, value in self.trader_incremental_pnl_usd
            },
            "trader_compound_entries": {
                trader: count for trader, count in self.trader_compound_entries
            },
            "trades": [item.payload() for item in self.trades],
            "blocker_reasons": [
                {"reason": reason, "count": count} for reason, count in self.blocker_reasons
            ],
            "function_accountability": list(self.function_accountability),
            "capital_science_receipts": list(self.capital_science_receipts),
            "leverage_decisions": [
                item.payload() for item in self.leverage_decisions
            ],
            "t06_expansion_decisions": [
                item.payload() for item in self.t06_expansion_decisions
            ],
            "t14_derisk_decisions": [
                item.payload() for item in self.t14_derisk_decisions
            ],
            "portfolio_shadow_decisions": [
                item.payload() for item in self.portfolio_shadow_decisions
            ],
            "dynamic_leverage_enabled": self.dynamic_leverage_enabled,
            "rational_redeploy_gate_enabled": self.rational_redeploy_gate_enabled,
            "noncertifying_research_redeploy_enabled": (
                self.noncertifying_research_redeploy_enabled
            ),
            "protected_reinvestment_policy_id": (self.protected_reinvestment_policy_id),
            "pool_scope": self.pool_scope,
            "seed_multiplier": format(self.seed_multiplier, "f"),
            "same_core_selection_surface": self.same_core_selection_surface,
            "realized_profit_only": self.realized_profit_only,
            "floating_pnl_used_as_funding": self.floating_pnl_used_as_funding,
            "qore_risk_sovereign": self.qore_risk_sovereign,
            "outcome_aware_tuning_used": self.outcome_aware_tuning_used,
            "broker_mutation_performed": self.broker_mutation_performed,
            "live_authorized": self.live_authorized,
            "real_capital_authorized": self.real_capital_authorized,
            "production_authorized": self.production_authorized,
            "merge_authorized": self.merge_authorized,
        }


def run_compound_portfolio_lane(
    *,
    plan: Phase22ChronologicalReplayPlan,
    core_execution: Phase22HistoricalExecutionReport,
    lab_use_executed_core_surface: bool = False,
    lab_require_rational_redeploy: bool = False,
    redeploy_authorizations: tuple[CompoundRedeployAuthorization, ...] = (),
    lab_allow_noncertifying_research_redeploy: bool = False,
    research_redeploy_authorizations: tuple[CompoundResearchRedeployAuthorization, ...] = (),
    lab_pool_scope: str = POOL_SCOPE_ACCOUNT,
    lab_seed_multiplier: Decimal = Decimal("1"),
    lab_dynamic_leverage: bool = False,
    regime_evidence: tuple[Phase22HistoricalRegimeEvidence, ...] = (),
) -> CompoundPortfolioLaneResult:
    """Add causal profit-funded seeds without changing Core policy selection."""

    if type(lab_use_executed_core_surface) is not bool:
        raise CiboCapitalManagementError("lab_use_executed_core_surface must be bool")
    if type(lab_require_rational_redeploy) is not bool:
        raise CiboCapitalManagementError("lab_require_rational_redeploy must be bool")
    if type(lab_allow_noncertifying_research_redeploy) is not bool:
        raise CiboCapitalManagementError("lab_allow_noncertifying_research_redeploy must be bool")
    if type(lab_dynamic_leverage) is not bool:
        raise CiboCapitalManagementError("lab_dynamic_leverage must be bool")
    if lab_pool_scope not in {POOL_SCOPE_ACCOUNT, POOL_SCOPE_TRADER_LOCAL}:
        raise CiboCapitalManagementError("lab_pool_scope is invalid")
    if (
        not isinstance(lab_seed_multiplier, Decimal)
        or not lab_seed_multiplier.is_finite()
        or lab_seed_multiplier < 1
        or lab_seed_multiplier != lab_seed_multiplier.to_integral_value()
    ):
        raise CiboCapitalManagementError("lab_seed_multiplier must be finite integer Decimal >= 1")
    if any(not isinstance(item, CompoundRedeployAuthorization) for item in redeploy_authorizations):
        raise CiboCapitalManagementError(
            "compound redeploy authorizations must use canonical contract"
        )
    authorization_by_signal = {item.signal_fingerprint: item for item in redeploy_authorizations}
    if len(authorization_by_signal) != len(redeploy_authorizations):
        raise CiboCapitalManagementError(
            "compound redeploy authorization fingerprints must be unique"
        )
    if any(
        not isinstance(item, CompoundResearchRedeployAuthorization)
        for item in research_redeploy_authorizations
    ):
        raise CiboCapitalManagementError(
            "compound research redeploy authorizations must use canonical contract"
        )
    research_authorization_by_signal = {
        item.signal_fingerprint: item for item in research_redeploy_authorizations
    }
    if len(research_authorization_by_signal) != len(research_redeploy_authorizations):
        raise CiboCapitalManagementError("compound research redeploy fingerprints must be unique")
    if any(not isinstance(item, Phase22HistoricalRegimeEvidence) for item in regime_evidence):
        raise CiboCapitalManagementError(
            "compound regime evidence must use canonical Phase22 contracts"
        )
    regime_by_epoch = {item.decision_epoch_id: item for item in regime_evidence}
    if len(regime_by_epoch) != len(regime_evidence):
        raise CiboCapitalManagementError("compound regime evidence epoch ids must be unique")
    if regime_evidence and set(regime_by_epoch) != {item.decision_epoch_id for item in plan.epochs}:
        raise CiboCapitalManagementError(
            "compound regime evidence must cover the exact replay epoch set"
        )
    if research_redeploy_authorizations and not lab_allow_noncertifying_research_redeploy:
        raise CiboCapitalManagementError(
            "research redeploy authorizations require explicit lab opt-in"
        )

    initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    core_realized = initial
    pool = Decimal(0)
    pool_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    incremental = Decimal(0)
    source_traders: set[str] = set()
    risk_engine = AccountWideRiskEngine()
    open_rows: dict[str, _Open] = {}
    trades: list[CompoundPortfolioTrade] = []
    blockers: Counter[str] = Counter()
    capital_science_receipts: list[CapitalScienceReceipt] = []
    leverage_decisions: list[CompoundLeverageDecision] = []
    t06_expansion_decisions: list[CompoundT06ExpansionDecision] = []
    t14_derisk_decisions: list[CompoundT14DeRiskDecision] = []
    portfolio_shadow_by_signal: dict[
        str,
        CompoundPortfolioShadowDecision,
    ] = {}
    selected = allowed = reduced = rejected = cross_trader = 0
    peak_realized_capital = initial

    outcomes = {item.signal_fingerprint: item for item in plan.outcome_events}
    core_settlements = sorted(
        core_execution.books.cma_settlement.settlements,
        key=lambda item: (item.capital_released_at, item.signal_fingerprint),
    )
    core_index = 0
    evidence_by_epoch = {
        item.decision_epoch_id: item for item in core_execution.books.holdout_evidence.decisions
    }
    core_release_by_signal = {
        item.signal_fingerprint: item.capital_released_at
        for item in core_execution.books.cma_settlement.settlements
    }
    core_risk_rows = tuple(
        item
        for item in core_execution.books.executed_risk.executed_risk
        if item.risk_decision is not RiskDecision.REJECT
    )

    core_selected_by_epoch: dict[datetime, tuple[str, ...]] = {}
    if lab_use_executed_core_surface:
        grouped: dict[datetime, list[str]] = defaultdict(list)
        for item in core_risk_rows:
            grouped[item.decided_at].append(item.signal_fingerprint)
        core_selected_by_epoch = {key: tuple(sorted(values)) for key, values in grouped.items()}

    def core_open_capacity(clock: datetime) -> tuple[Decimal, Decimal]:
        rows = tuple(
            item
            for item in core_risk_rows
            if item.decided_at <= clock
            and item.signal_fingerprint in core_release_by_signal
            and clock < core_release_by_signal[item.signal_fingerprint]
        )
        return (
            sum((item.authorized_stop_risk_usd for item in rows), Decimal(0)),
            sum((item.authorized_margin_usd for item in rows), Decimal(0)),
        )

    def settle_until(clock: datetime) -> None:
        nonlocal core_index, core_realized, pool, incremental, peak_realized_capital
        while (
            core_index < len(core_settlements)
            and core_settlements[core_index].capital_released_at <= clock
        ):
            item = core_settlements[core_index]
            core_realized += item.realized_net_pnl_usd
            peak_realized_capital = max(
                peak_realized_capital,
                core_realized + incremental,
            )
            if item.realized_net_pnl_usd > 0:
                if lab_pool_scope == POOL_SCOPE_TRADER_LOCAL:
                    pool_by_trader[item.trader_id] += item.realized_net_pnl_usd
                else:
                    pool += item.realized_net_pnl_usd
                    source_traders.add(item.trader_id)
            core_index += 1

        due = sorted(
            (item for item in open_rows.values() if item.exit_at <= clock),
            key=lambda item: (item.exit_at, item.signal_fingerprint),
        )
        for item in due:
            open_rows.pop(item.signal_fingerprint, None)
            pnl = (
                item.gross_structural_outcome_r * item.authorized_stop_risk_usd
                - item.provider_cost_usd
            )
            if lab_pool_scope == POOL_SCOPE_TRADER_LOCAL:
                pool_by_trader[item.trader_id] += pnl
                if pool_by_trader[item.trader_id] < 0:
                    raise CiboCapitalManagementError("trader-local compound pool became negative")
            else:
                pool += pnl
                if pool < 0:
                    raise CiboCapitalManagementError(
                        "compound pool became negative despite fail-closed funding"
                    )
            incremental += pnl
            peak_realized_capital = max(
                peak_realized_capital,
                core_realized + incremental,
            )
            cross = any(source != item.trader_id for source in item.source_traders_before_entry)
            trades.append(
                CompoundPortfolioTrade(
                    signal_fingerprint=item.signal_fingerprint,
                    trader_id=item.trader_id,
                    exit_at=item.exit_at,
                    authorized_volume=item.authorized_volume,
                    authorized_stop_risk_usd=item.authorized_stop_risk_usd,
                    authorized_margin_usd=item.authorized_margin_usd,
                    gross_structural_outcome_r=item.gross_structural_outcome_r,
                    provider_cost_usd=item.provider_cost_usd,
                    incremental_realized_pnl_usd=pnl,
                    source_traders_before_entry=item.source_traders_before_entry,
                    cross_trader_pool_used=cross,
                )
            )

    for epoch in plan.epochs:
        settle_until(epoch.market_decision_at)
        decision = evidence_by_epoch.get(epoch.decision_epoch_id)
        if decision is None:
            raise CiboCapitalManagementError("compound lane missing Core decision")
        policy = core_execution.books.holdout_policy.decision_for_evidence(decision.evidence_sha256)
        if policy is None:
            raise CiboCapitalManagementError("compound lane missing Core policy")
        by_signal = {item.signal_fingerprint: item for item in epoch.candidates}
        selected_signals = (
            core_selected_by_epoch.get(epoch.market_decision_at, ())
            if lab_use_executed_core_surface
            else tuple(policy.selected_signal_fingerprints)
        )
        scarcity_scores = {
            signal: _compound_scarcity_score(
                by_signal[signal],
                decision_at=epoch.market_decision_at,
            )
            for signal in selected_signals
        }
        compound_signal_order = (
            tuple(
                sorted(
                    selected_signals,
                    key=lambda signal: (
                        -scarcity_scores[signal],
                        signal,
                    ),
                )
            )
            if (
                lab_dynamic_leverage
                and lab_pool_scope == POOL_SCOPE_ACCOUNT
                and len(selected_signals) > 1
            )
            else tuple(selected_signals)
        )
        scarcity_rank_by_signal = {
            signal: index + 1
            for index, signal in enumerate(compound_signal_order)
        }
        scarcity_order_changed = compound_signal_order != tuple(selected_signals)
        known_epoch_options: list[CapitalScienceKnownOpportunity] = []
        for known_signal in selected_signals:
            known_candidate = by_signal[known_signal]
            known_opportunity = known_candidate.projection.candidate.capital_input.opportunity
            known_volume = minimum_seed_volume(known_opportunity) * (
                Decimal(1) if lab_dynamic_leverage else lab_seed_multiplier
            )
            if known_volume > known_opportunity.maximum_volume:
                continue
            known_risk = known_volume * known_opportunity.stop_loss_per_volume
            known_margin = known_volume * known_opportunity.margin_per_volume
            known_cost = (
                known_candidate.projection.provider_envelope.execution_cost_per_volume_usd
                * known_volume
            )
            known_expectation = build_frozen_train_expectation(
                trader_id=known_opportunity.trader_id,
                stop_risk_usd=known_risk,
                as_of=epoch.market_decision_at,
            )
            known_epoch_options.append(
                CapitalScienceKnownOpportunity(
                    option_id=known_signal,
                    trader_id=known_candidate.trader_id,
                    qore_symbol=known_candidate.qore_symbol,
                    known_at=epoch.market_decision_at,
                    earliest_action_at=max(
                        epoch.market_decision_at,
                        known_candidate.entry_at,
                    ),
                    expires_at=max(
                        known_candidate.entry_at + timedelta(seconds=1),
                        epoch.market_decision_at
                        + timedelta(
                            minutes=max(
                                1,
                                int(known_expectation.expected_capital_minutes) + 1,
                            )
                        ),
                    ),
                    requested_capital_usd=known_risk + known_cost,
                    stop_risk_usd=known_risk,
                    margin_usd=known_margin,
                    evidence_sha256=known_candidate.fingerprint(),
                    expected_net_value_usd=known_expectation.expected_net_value_usd,
                    expected_capital_minutes=known_expectation.expected_capital_minutes,
                )
            )

        for signal in compound_signal_order:
            selected += 1
            if lab_require_rational_redeploy:
                redeploy = authorization_by_signal.get(signal)
                research_redeploy = research_authorization_by_signal.get(signal)
                if redeploy is not None:
                    if redeploy.known_at > epoch.market_decision_at:
                        blockers["COMPOUND_REDEPLOY_EVIDENCE_FUTURE_KNOWN"] += 1
                        rejected += 1
                        continue
                    if not redeploy.policy_authorized:
                        blockers["COMPOUND_REDEPLOY_UTILITY_NOT_AUTHORIZED"] += 1
                        rejected += 1
                        continue
                elif lab_allow_noncertifying_research_redeploy and research_redeploy is not None:
                    if research_redeploy.known_at > epoch.market_decision_at:
                        blockers["COMPOUND_RESEARCH_REDEPLOY_EVIDENCE_FUTURE_KNOWN"] += 1
                        rejected += 1
                        continue
                else:
                    blockers["COMPOUND_REDEPLOY_UTILITY_NOT_AUTHORIZED"] += 1
                    rejected += 1
                    continue
            candidate = by_signal[signal]
            opportunity = candidate.projection.candidate.capital_input.opportunity
            base_volume = minimum_seed_volume(opportunity)
            requested_multiplier = lab_seed_multiplier
            if lab_dynamic_leverage:
                maximum_multiplier = (
                    opportunity.maximum_volume / base_volume
                ).to_integral_value(rounding="ROUND_FLOOR")
                requested_multiplier = min(
                    requested_multiplier,
                    maximum_multiplier,
                )
            volume = base_volume * requested_multiplier
            if requested_multiplier < 1 or volume > opportunity.maximum_volume:
                blockers["SHADOW_SEED_MULTIPLIER_EXCEEDS_MAXIMUM_VOLUME"] += 1
                rejected += 1
                continue
            risk = volume * opportunity.stop_loss_per_volume
            margin = volume * opportunity.margin_per_volume
            cost = candidate.projection.provider_envelope.execution_cost_per_volume_usd * volume
            loss_reserve = protected_loss_reserve_usd(risk)
            committed_rows = (
                tuple(item for item in open_rows.values() if item.trader_id == candidate.trader_id)
                if lab_pool_scope == POOL_SCOPE_TRADER_LOCAL
                else tuple(open_rows.values())
            )
            committed_loss = sum(
                (
                    item.authorized_stop_risk_usd
                    + item.provider_cost_usd
                    + item.protected_loss_reserve_usd
                    for item in committed_rows
                ),
                Decimal(0),
            )
            committed_deployed_profit = sum(
                (
                    item.authorized_stop_risk_usd + item.provider_cost_usd
                    for item in committed_rows
                ),
                Decimal(0),
            )
            committed_protected_reserve = sum(
                (item.protected_loss_reserve_usd for item in committed_rows),
                Decimal(0),
            )
            funding_pool = (
                pool_by_trader[candidate.trader_id]
                if lab_pool_scope == POOL_SCOPE_TRADER_LOCAL
                else pool
            )
            available = max(Decimal(0), funding_pool - committed_loss)
            equity = max(Decimal(0), core_realized + incremental)
            if equity <= 0:
                blockers["CURRENT_REALIZED_CAPITAL_NOT_POSITIVE"] += 1
                rejected += 1
                continue
            dynamic_limit = maximum_reinvestment_capital_need_usd(equity)
            expectation = build_frozen_train_expectation(
                trader_id=opportunity.trader_id,
                stop_risk_usd=risk,
                as_of=epoch.market_decision_at,
            )

            core_open_risk_cs, core_open_margin_cs = core_open_capacity(epoch.market_decision_at)
            compound_open_risk_cs = sum(
                (item.authorized_stop_risk_usd for item in open_rows.values()),
                Decimal(0),
            )
            compound_open_margin_cs = sum(
                (item.authorized_margin_usd for item in open_rows.values()),
                Decimal(0),
            )
            total_open_risk_cs = core_open_risk_cs + compound_open_risk_cs
            total_open_margin_cs = core_open_margin_cs + compound_open_margin_cs
            regime_source = regime_by_epoch.get(epoch.decision_epoch_id)
            regime_state = None
            if regime_source is not None:
                risk_capacity = total_open_risk_cs + max(Decimal(0), equity - total_open_risk_cs)
                margin_capacity = total_open_margin_cs + max(
                    Decimal(0), equity - total_open_margin_cs
                )
                regime_state = CiboCapitalRegimeState(
                    liquidity=regime_source.liquidity,
                    volatility=regime_source.volatility,
                    correlation=regime_source.correlation,
                    provider_condition=regime_source.provider_condition,
                    risk_utilization=(
                        Decimal(0) if risk_capacity <= 0 else total_open_risk_cs / risk_capacity
                    ),
                    margin_utilization=(
                        Decimal(0)
                        if margin_capacity <= 0
                        else total_open_margin_cs / margin_capacity
                    ),
                    drawdown_utilization=(
                        Decimal(0)
                        if peak_realized_capital <= 0
                        else (peak_realized_capital - equity) / peak_realized_capital
                    ),
                    opportunity_count=max(1, len(known_epoch_options)),
                    position_path_adverse=regime_source.position_path_adverse,
                    evidence_stale=regime_source.evidence_stale,
                )
            capital_science_state = CapitalSciencePredecisionInput(
                    decision_epoch_id=epoch.decision_epoch_id,
                    signal_fingerprint=signal,
                    trader_id=candidate.trader_id,
                    qore_symbol=candidate.qore_symbol,
                    decision_at=epoch.market_decision_at,
                    realized_capital_usd=equity,
                    peak_realized_capital_usd=max(
                        peak_realized_capital,
                        equity,
                    ),
                    realized_profit_pool_usd=funding_pool,
                    protected_capacity_usd=min(
                        funding_pool,
                        committed_protected_reserve + loss_reserve,
                    ),
                    deployed_profit_usd=min(
                        max(
                            Decimal(0),
                            funding_pool - committed_protected_reserve - loss_reserve,
                        ),
                        committed_deployed_profit,
                    ),
                    open_stop_risk_usd=total_open_risk_cs,
                    open_margin_usd=total_open_margin_cs,
                    requested_stop_risk_usd=risk,
                    requested_margin_usd=margin,
                    provider_cost_usd=cost,
                    expected_net_value_usd=expectation.expected_net_value_usd,
                    expected_capital_minutes=expectation.expected_capital_minutes,
                    hard_risk_headroom_usd=max(
                        Decimal(0),
                        equity - total_open_risk_cs,
                    ),
                    margin_headroom_usd=max(
                        Decimal(0),
                        equity - total_open_margin_cs,
                    ),
                    competing_candidates=len(selected_signals),
                    account_identity=CiboAccountCapitalIdentity(
                        provider_key="ctrader-demo",
                        account_ref="phase22-v4-counterfactual-usd60",
                        environment=MarketRuntimeEnvironment.DEMO,
                    ),
                    regime_state=regime_state,
                    known_simultaneous_opportunities=(
                        _known_options_with_current_geometry(
                            tuple(known_epoch_options),
                            signal_fingerprint=signal,
                            stop_risk_usd=risk,
                            margin_usd=margin,
                            provider_cost_usd=cost,
                        )
                    ),
                    open_economic_positions=tuple(
                        CapitalScienceOpenEconomicPosition(
                            signal_fingerprint=item.signal_fingerprint,
                            trader_id=item.trader_id,
                            qore_symbol=item.qore_symbol,
                            side=item.side,
                            entry_at=item.entry_at,
                            planned_exit_at=item.exit_at,
                            current_volume=item.authorized_volume,
                            current_stop_risk_usd=item.authorized_stop_risk_usd,
                            current_margin_usd=item.authorized_margin_usd,
                            entry_price=item.entry_price,
                            structural_stop=item.structural_stop,
                            technical_target=item.technical_target,
                            provider_cost_usd=item.provider_cost_usd,
                            entry_expected_net_value_usd=(
                                item.entry_expected_net_value_usd
                            ),
                            entry_expected_capital_minutes=(
                                item.entry_expected_capital_minutes
                            ),
                            expectation_evidence_sha256=(
                                item.expectation_evidence_sha256
                            ),
                            continuation_value_identified=False,
                        )
                        for item in open_rows.values()
                    ),
                    genc7_proposal=Genc7PreservationProposalEvidence(
                        proposal_id=f"compound-redeploy:{epoch.decision_epoch_id}:{signal}",
                        decision_at=epoch.market_decision_at,
                        account_identity=CiboAccountCapitalIdentity(
                            provider_key="ctrader-demo",
                            account_ref="phase22-v4-counterfactual-usd60",
                            environment=MarketRuntimeEnvironment.DEMO,
                        ),
                        action=Genc7Action.COMPOUND,
                        source_bucket=(
                            Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY
                        ),
                        amount_usd=risk + cost,
                        evidence_sha256=candidate.fingerprint(),
                        rationale_code="PROTECTED_REINVESTMENT_V2_CANDIDATE",
                        evaluation_horizon_minutes=max(
                            1,
                            int(expectation.expected_capital_minutes) + 1,
                        ),
                        calibrated=True,
                        capital_eligible=True,
                    ),
                )
            capital_science = evaluate_capital_science_predecision(
                capital_science_state
            )
            portfolio_shadow_by_signal[signal] = _portfolio_shadow_decision(
                state=capital_science_state,
                directive=capital_science,
            )
            if lab_dynamic_leverage:
                effective_multiplier = requested_multiplier
                final_t11_cap = volume
                final_t11_reason = "T11 not yet evaluated"
                final_t11_inputs = {
                    "requested_volume": volume,
                    "gross_edge_per_volume_usd": Decimal(0),
                    "spread_cost_per_volume_usd": Decimal(0),
                    "commission_cost_per_volume_usd": Decimal(0),
                    "slippage_cost_per_volume_usd": Decimal(0),
                    "impact_cost_per_volume_squared_usd": Decimal(0),
                }
                final_posture = _genc8_posture(capital_science)
                for _iteration in range(4):
                    final_posture = _genc8_posture(capital_science)
                    genc8_cap = _GENC8_MULTIPLIER_CAP[final_posture]
                    (
                        final_t11_cap,
                        final_t11_reason,
                        final_t11_inputs,
                    ) = _t11_execution_cap(
                        requested_volume=volume,
                        expected_structural_value_usd=(
                            expectation.expected_net_value_usd
                        ),
                        provider_envelope=candidate.projection.provider_envelope,
                    )
                    t11_multiplier_cap = (
                        final_t11_cap / base_volume
                    ).to_integral_value(rounding="ROUND_FLOOR")
                    next_multiplier = min(
                        effective_multiplier,
                        genc8_cap,
                        t11_multiplier_cap,
                    )
                    if next_multiplier == effective_multiplier:
                        break
                    if next_multiplier <= 0:
                        effective_multiplier = Decimal(0)
                        break
                    effective_multiplier = next_multiplier
                    volume = base_volume * effective_multiplier
                    risk = volume * opportunity.stop_loss_per_volume
                    margin = volume * opportunity.margin_per_volume
                    cost = (
                        candidate.projection.provider_envelope.execution_cost_per_volume_usd
                        * volume
                    )
                    loss_reserve = protected_loss_reserve_usd(risk)
                    expectation = build_frozen_train_expectation(
                        trader_id=opportunity.trader_id,
                        stop_risk_usd=risk,
                        as_of=epoch.market_decision_at,
                    )
                    genc7 = capital_science_state.genc7_proposal
                    assert genc7 is not None
                    capital_science_state = replace(
                        capital_science_state,
                        protected_capacity_usd=min(
                            funding_pool,
                            committed_protected_reserve + loss_reserve,
                        ),
                        deployed_profit_usd=min(
                            max(
                                Decimal(0),
                                funding_pool
                                - committed_protected_reserve
                                - loss_reserve,
                            ),
                            committed_deployed_profit,
                        ),
                        requested_stop_risk_usd=risk,
                        requested_margin_usd=margin,
                        provider_cost_usd=cost,
                        expected_net_value_usd=(
                            expectation.expected_net_value_usd
                        ),
                        expected_capital_minutes=(
                            expectation.expected_capital_minutes
                        ),
                        known_simultaneous_opportunities=(
                            _known_options_with_current_geometry(
                                tuple(known_epoch_options),
                                signal_fingerprint=signal,
                                stop_risk_usd=risk,
                                margin_usd=margin,
                                provider_cost_usd=cost,
                            )
                        ),
                        genc7_proposal=replace(
                            genc7,
                            amount_usd=risk + cost,
                            evaluation_horizon_minutes=max(
                                1,
                                int(expectation.expected_capital_minutes) + 1,
                            ),
                        ),
                    )
                    capital_science = evaluate_capital_science_predecision(
                        capital_science_state
                    )

                leverage_decisions.append(
                    CompoundLeverageDecision(
                        signal_fingerprint=signal,
                        trader_id=candidate.trader_id,
                        decision_at=epoch.market_decision_at,
                        requested_multiplier=requested_multiplier,
                        effective_multiplier=effective_multiplier,
                        genc8_posture=final_posture,
                        t11_requested_volume=final_t11_inputs[
                            "requested_volume"
                        ],
                        t11_gross_edge_per_volume_usd=final_t11_inputs[
                            "gross_edge_per_volume_usd"
                        ],
                        t11_spread_cost_per_volume_usd=final_t11_inputs[
                            "spread_cost_per_volume_usd"
                        ],
                        t11_commission_cost_per_volume_usd=final_t11_inputs[
                            "commission_cost_per_volume_usd"
                        ],
                        t11_slippage_cost_per_volume_usd=final_t11_inputs[
                            "slippage_cost_per_volume_usd"
                        ],
                        t11_impact_cost_per_volume_squared_usd=final_t11_inputs[
                            "impact_cost_per_volume_squared_usd"
                        ],
                        t11_execution_cap_volume=final_t11_cap,
                        t11_allows_compound=(effective_multiplier > 0),
                        reason=(
                            f"GEN-C8 posture={final_posture}; "
                            + final_t11_reason
                        ),
                    )
                )
                if effective_multiplier <= 0:
                    lane_receipts = _lane_owned_capital_science_receipts(
                        state=capital_science_state,
                        funding_pool_usd=funding_pool,
                        available_profit_usd=available,
                        pool_scope=lab_pool_scope,
                        source_traders=source_traders,
                        current_trader=candidate.trader_id,
                        scarcity_rank=scarcity_rank_by_signal[signal],
                        scarcity_count=len(compound_signal_order),
                        scarcity_score=scarcity_scores[signal],
                        scarcity_order_changed=scarcity_order_changed,
                        dynamic_leverage=lab_dynamic_leverage,
                    )
                    capital_science_receipts.extend(lane_receipts)
                    capital_science_receipts.extend(
                        capital_science.receipts
                    )
                    if _GENC8_MULTIPLIER_CAP[final_posture] <= 0:
                        blockers["GENC8_DYNAMIC_LEVERAGE_PAUSED"] += 1
                    else:
                        blockers["T11_EXECUTION_EFFICIENCY_REJECTED_COMPOUND"] += 1
                    rejected += 1
                    continue
            t14_factor = _t14_compound_retention_factor(regime_state)
            t14_pre_volume = volume
            t14_decision = plan_dynamic_derisking(
                CiboDeRiskingInput(
                    current_volume=volume,
                    minimum_retained_volume=base_volume,
                    volume_step=opportunity.volume_step,
                    stop_risk_per_volume_usd=opportunity.stop_loss_per_volume,
                    margin_per_volume_usd=opportunity.margin_per_volume,
                    maximum_retained_stop_risk_usd=risk * t14_factor,
                    maximum_retained_margin_usd=margin * t14_factor,
                    methodology_position_valid=True,
                )
            )
            t14_derisk_decisions.append(
                CompoundT14DeRiskDecision(
                    signal_fingerprint=signal,
                    trader_id=candidate.trader_id,
                    decision_at=epoch.market_decision_at,
                    pre_volume=t14_pre_volume,
                    retained_volume=t14_decision.retained_volume,
                    reduction_volume=t14_decision.reduction_volume,
                    released_stop_risk_usd=(
                        t14_decision.released_stop_risk_usd
                    ),
                    released_margin_usd=t14_decision.released_margin_usd,
                    retention_factor=t14_factor,
                    action=t14_decision.action.value,
                    reason=t14_decision.reason,
                )
            )
            if t14_decision.action is CiboDeRiskAction.RELEASE_ALL:
                blockers["T14_DYNAMIC_DERISK_RELEASE_ALL"] += 1
                rejected += 1
                continue
            if t14_decision.action is CiboDeRiskAction.REDUCE:
                volume = t14_decision.retained_volume
                risk = t14_decision.retained_stop_risk_usd
                margin = t14_decision.retained_margin_usd
                cost = (
                    candidate.projection.provider_envelope.execution_cost_per_volume_usd
                    * volume
                )
                loss_reserve = protected_loss_reserve_usd(risk)
                expectation = build_frozen_train_expectation(
                    trader_id=opportunity.trader_id,
                    stop_risk_usd=risk,
                    as_of=epoch.market_decision_at,
                )
                genc7 = capital_science_state.genc7_proposal
                assert genc7 is not None
                capital_science_state = replace(
                    capital_science_state,
                    protected_capacity_usd=min(
                        funding_pool,
                        committed_protected_reserve + loss_reserve,
                    ),
                    deployed_profit_usd=min(
                        max(
                            Decimal(0),
                            funding_pool
                            - committed_protected_reserve
                            - loss_reserve,
                        ),
                        committed_deployed_profit,
                    ),
                    requested_stop_risk_usd=risk,
                    requested_margin_usd=margin,
                    provider_cost_usd=cost,
                    expected_net_value_usd=expectation.expected_net_value_usd,
                    expected_capital_minutes=expectation.expected_capital_minutes,
                    known_simultaneous_opportunities=(
                        _known_options_with_current_geometry(
                            tuple(known_epoch_options),
                            signal_fingerprint=signal,
                            stop_risk_usd=risk,
                            margin_usd=margin,
                            provider_cost_usd=cost,
                        )
                    ),
                    genc7_proposal=replace(
                        genc7,
                        amount_usd=risk + cost,
                        evaluation_horizon_minutes=max(
                            1,
                            int(expectation.expected_capital_minutes) + 1,
                        ),
                    ),
                )
                capital_science = evaluate_capital_science_predecision(
                    capital_science_state
                )

            lane_receipts = _lane_owned_capital_science_receipts(
                state=capital_science_state,
                funding_pool_usd=funding_pool,
                available_profit_usd=available,
                pool_scope=lab_pool_scope,
                source_traders=source_traders,
                current_trader=candidate.trader_id,
                scarcity_rank=scarcity_rank_by_signal[signal],
                scarcity_count=len(compound_signal_order),
                scarcity_score=scarcity_scores[signal],
                scarcity_order_changed=scarcity_order_changed,
                dynamic_leverage=lab_dynamic_leverage,
            )
            capital_science_receipts.extend(lane_receipts)
            capital_science_receipts.extend(capital_science.receipts)
            available = min(
                available,
                capital_science.deployable_profit_usd,
            )
            if not capital_science.allow_incremental_compound:
                blockers["CAPITAL_SCIENCE_PREDECISION_ABSTAINED_OR_FAIL_CLOSED"] += 1
                rejected += 1
                continue
            if risk + cost + loss_reserve > available:
                blockers["REALIZED_PROFIT_POOL_BELOW_SEED_COST_AND_LOSS_RESERVE"] += 1
                rejected += 1
                continue
            if risk + cost > dynamic_limit:
                blockers["DYNAMIC_CURRENT_CAPITAL_REINVESTMENT_LIMIT_EXCEEDED"] += 1
                rejected += 1
                continue
            if not protected_reinvestment_candidate_allowed(
                side=opportunity.side,
                capital_need_usd=risk + cost,
                eligible_current_capital_usd=equity,
                entry_type=opportunity.entry_type,
                expected_net_value_usd=expectation.expected_net_value_usd,
                expected_capital_minutes=expectation.expected_capital_minutes,
            ):
                blockers["PROTECTED_REINVESTMENT_V2_CAUSAL_GATE_REJECTED"] += 1
                rejected += 1
                continue
            headroom = min(
                equity,
                max(Decimal(0), available - cost - loss_reserve),
            )
            if risk > headroom or margin > headroom:
                blockers["COMPOUND_RISK_OR_MARGIN_HEADROOM_INSUFFICIENT"] += 1
                rejected += 1
                continue

            t06_requested_volume = volume
            t06_requested_risk = risk
            t06_requested_margin = margin
            t06_state = CiboCapitalState(
                assigned_capital_usd=equity,
                hard_risk_headroom_usd=risk,
                margin_headroom_usd=margin,
                base_capital_at_risk_usd=min(initial, equity),
                realized_net_profit_usd=funding_pool,
                protected_open_economic_floor_usd=Decimal(0),
                proven_self_financing_capacity_usd=risk,
                reserved_expansion_risk_usd=Decimal(0),
                cost_reserve_usd=cost + loss_reserve,
            )
            plan_row = plan_self_financing_expansion(
                opportunity,
                t06_state,
            )
            t06_expansion_decisions.append(
                CompoundT06ExpansionDecision(
                    signal_fingerprint=signal,
                    trader_id=candidate.trader_id,
                    decision_at=epoch.market_decision_at,
                    requested_volume=t06_requested_volume,
                    authorized_volume=plan_row.volume,
                    requested_stop_risk_usd=t06_requested_risk,
                    authorized_stop_risk_usd=plan_row.stop_risk_usd,
                    requested_margin_usd=t06_requested_margin,
                    authorized_margin_usd=plan_row.margin_usd,
                    action=plan_row.action.value,
                    capital_source=(
                        None
                        if plan_row.capital_source is None
                        else plan_row.capital_source.value
                    ),
                    reason=plan_row.reason,
                )
            )
            if plan_row.action is not CapitalAction.EXPAND:
                blockers["T06_SELF_FINANCING_EXPANSION_NO_CHANGE"] += 1
                rejected += 1
                continue
            if (
                plan_row.capital_source is CapitalSource.ORIGINAL_BASE_CAPITAL
                or plan_row.stop_risk_usd > t06_requested_risk
                or plan_row.margin_usd > t06_requested_margin
            ):
                raise CiboCapitalManagementError(
                    "T06 universal expansion violated non-base or no-increase invariant"
                )
            volume = plan_row.volume
            risk = plan_row.stop_risk_usd
            margin = plan_row.margin_usd
            request = build_cma_risk_request(
                request_id=f"compound:{epoch.decision_epoch_id}:{signal}",
                opportunity=opportunity,
                plan=plan_row,
                requested_at=epoch.market_decision_at,
                expires_at=max(
                    candidate.entry_at,
                    epoch.market_decision_at + timedelta(seconds=1),
                ),
                capital_source_id=f"compound-realized-profit-pool:{signal}",
            )
            core_open_risk, core_open_margin = core_open_capacity(epoch.market_decision_at)
            compound_open_risk = sum(
                (item.authorized_stop_risk_usd for item in open_rows.values()),
                Decimal(0),
            )
            compound_open_margin = sum(
                (item.authorized_margin_usd for item in open_rows.values()),
                Decimal(0),
            )
            total_open_risk = core_open_risk + compound_open_risk
            total_open_margin = core_open_margin + compound_open_margin
            external_headroom = max(Decimal(0), equity - total_open_risk)
            snapshot = AccountRiskSnapshot(
                account_binding_id="phase22-v4-compound-shadow",
                equity=equity,
                margin_used=total_open_margin,
                free_margin=max(Decimal(0), equity - total_open_margin),
                open_stop_worst_case_loss=total_open_risk,
                open_floating_loss=Decimal(0),
                pending_broker_worst_case_loss=Decimal(0),
                qore_authorizable_headroom=min(headroom, external_headroom),
                provider_budget=_Budget(
                    provider_headroom=equity,
                    max_risk_at_any_time=equity,
                    active_mll=Decimal(0),
                    hard_breach=equity <= 0,
                ),
                reconciled_at=epoch.market_decision_at,
            )
            auth = risk_engine.authorize(
                request,
                snapshot,
                now=epoch.market_decision_at,
            )
            if auth.decision is RiskDecision.REJECT:
                rejected += 1
                blockers["QORE_RISK_REJECTED_COMPOUND_SEED"] += 1
                continue
            if auth.decision is RiskDecision.ALLOW:
                allowed += 1
            else:
                reduced += 1
            event = outcomes[signal]
            source_snapshot = (
                (candidate.trader_id,)
                if lab_pool_scope == POOL_SCOPE_TRADER_LOCAL
                and pool_by_trader[candidate.trader_id] > 0
                else tuple(sorted(source_traders))
            )
            if any(item != candidate.trader_id for item in source_snapshot):
                cross_trader += 1
            risk_engine.record_full_fill(auth.authorization_id)
            reservation = next(
                (
                    item
                    for item in risk_engine.reservations()
                    if item.authorization.authorization_id == auth.authorization_id
                ),
                None,
            )
            if reservation is None:
                raise CiboCapitalManagementError("compound Risk reservation disappeared after fill")
            state = reservation.state.value
            if state == "filled-unreconciled":
                risk_engine.reconcile_fill(auth.authorization_id)
            elif state != "released":
                raise CiboCapitalManagementError(
                    "compound Risk fill reached unexpected reservation state: " + state
                )
            open_rows[signal] = _Open(
                signal_fingerprint=signal,
                trader_id=candidate.trader_id,
                qore_symbol=candidate.qore_symbol,
                side=opportunity.side,
                entry_at=epoch.market_decision_at,
                exit_at=event.exit_at,
                entry_price=Decimal(str(opportunity.intended_entry)),
                structural_stop=Decimal(str(opportunity.stop_loss)),
                technical_target=Decimal(str(opportunity.take_profit)),
                authorization_id=auth.authorization_id,
                authorized_volume=auth.authorized_volume,
                authorized_stop_risk_usd=auth.monetary_stop_loss,
                authorized_margin_usd=auth.margin_reserved,
                gross_structural_outcome_r=event.gross_structural_outcome_r,
                provider_cost_usd=(
                    candidate.projection.provider_envelope.execution_cost_per_volume_usd
                    * auth.authorized_volume
                ),
                entry_expected_net_value_usd=expectation.expected_net_value_usd,
                entry_expected_capital_minutes=expectation.expected_capital_minutes,
                expectation_evidence_sha256=(
                    "sha256:" + sha256(
                        expectation.evidence_id.encode("utf-8")
                    ).hexdigest()
                ),
                protected_loss_reserve_usd=protected_loss_reserve_usd(auth.monetary_stop_loss),
                source_traders_before_entry=source_snapshot,
            )
            # The open position is represented explicitly in open_rows and
            # therefore in subsequent AccountRiskSnapshot open-risk/margin.

    if core_settlements or open_rows:
        final_clock = max(
            [item.capital_released_at for item in core_settlements]
            + [item.exit_at for item in open_rows.values()]
        )
        settle_until(final_clock)

    by_trader: dict[str, Decimal] = defaultdict(Decimal)
    entries: Counter[str] = Counter()
    pnl_rows = [
        item.realized_net_pnl_usd for item in core_execution.books.cma_settlement.settlements
    ]
    for item in trades:
        by_trader[item.trader_id] += item.incremental_realized_pnl_usd
        entries[item.trader_id] += 1
        pnl_rows.append(item.incremental_realized_pnl_usd)
    positives = sum((item for item in pnl_rows if item > 0), Decimal(0))
    losses = -sum((item for item in pnl_rows if item < 0), Decimal(0))
    pf = None if losses == 0 else positives / losses

    admitted = sum(
        1
        for item in core_execution.books.cma_settlement.settlements
        if item.realized_net_pnl_usd > 0
    )
    applied = len(trades)

    final_observed_at = max(
        [epoch.market_decision_at for epoch in plan.epochs]
        + [item.capital_released_at for item in core_settlements]
        + [item.exit_at for item in trades]
    )
    postrun_receipts = build_capital_science_postrun_receipts(
        observed_at=final_observed_at,
        ending_capital_usd=core_execution.final_realized_capital_usd + incremental,
        net_realized_pnl_usd=(core_execution.final_realized_capital_usd + incremental - initial),
        settlement_rows=tuple(
            (
                item.signal_fingerprint,
                item.trader_id,
                item.realized_net_pnl_usd,
            )
            for item in core_execution.books.cma_settlement.settlements
        )
        + tuple(
            (
                item.signal_fingerprint,
                item.trader_id,
                item.incremental_realized_pnl_usd,
            )
            for item in trades
        ),
    )
    capital_science_receipts.extend(postrun_receipts)
    capital_science_functions = aggregate_capital_science_receipts(capital_science_receipts)

    functions = (
        {
            "function_code": "GEN-C1_COMPOUND_CAPITAL",
            "function_type": "COMPOUND",
            "status": "APPLIED" if admitted else "FAIL_CLOSED",
            "eligible_epochs": len(plan.epochs),
            "invoked_count": len(plan.epochs),
            "executed_count": admitted,
            "blocked_count": 0 if admitted else len(plan.epochs),
            "reason": (
                "positive terminal Core settlements admitted as realized-profit-only "
                "compound capacity"
                if admitted
                else "no positive realized Core settlement existed before deployment"
            ),
        },
        {
            "function_code": "GEN-C3_CORE_COMPOUND_PORTFOLIO",
            "function_type": "COMPOUND_PORTFOLIO",
            "status": "APPLIED" if applied else "FAIL_CLOSED",
            "eligible_epochs": selected,
            "invoked_count": selected,
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "account-local realized-profit pool was redeployed across the "
                f"Core selection surface; cross-Trader deployments={cross_trader}"
                if applied
                else (
                    "rational redeploy utility/preservation/governance evidence "
                    "did not authorize incremental capital"
                    if lab_require_rational_redeploy
                    else "realized-profit pool never reached one legal minimum seed"
                )
            ),
        },
        {
            "function_code": "GEN-C5_SEQUENTIAL_COMPOUNDING",
            "function_type": "COMPOUND",
            "status": "APPLIED" if applied else "FAIL_CLOSED",
            "eligible_epochs": selected,
            "invoked_count": selected,
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "causally prior realized profit funded later incremental seeds"
                if applied
                else (
                    "sequential compound remained fail-closed because rational "
                    "redeploy policy authorization was absent"
                    if lab_require_rational_redeploy
                    else "no later selected opportunity could consume realized-profit capacity"
                )
            ),
        },
        {
            "function_code": "GEN-C6_INTERNAL_CAPITAL_MARKET",
            "function_type": "COMPOUND_PORTFOLIO",
            "status": "JUSTIFIED_NOT_APPLICABLE",
            "eligible_epochs": 0,
            "invoked_count": len(plan.epochs),
            "executed_count": 0,
            "blocked_count": 0,
            "reason": (
                "this ablation measures the frozen Core selection plus a shared "
                "Compound Portfolio; it does not replace Core selection with a "
                "new scarcity-ranking policy"
            ),
        },
    ) + capital_science_functions

    return CompoundPortfolioLaneResult(
        core_ending_capital_usd=core_execution.final_realized_capital_usd,
        compound_incremental_pnl_usd=incremental,
        ending_capital_usd=core_execution.final_realized_capital_usd + incremental,
        net_realized_pnl_usd=(core_execution.final_realized_capital_usd + incremental - initial),
        compound_selected_count=selected,
        compound_allowed_count=allowed,
        compound_reduced_count=reduced,
        compound_rejected_count=rejected,
        compound_settled_count=len(trades),
        cross_trader_compound_deployments=cross_trader,
        profit_factor=pf,
        trader_incremental_pnl_usd=tuple(sorted(by_trader.items())),
        trader_compound_entries=tuple(sorted(entries.items())),
        trades=tuple(trades),
        blocker_reasons=tuple(sorted(blockers.items())),
        function_accountability=functions,
        capital_science_receipts=tuple(item.payload() for item in capital_science_receipts),
        leverage_decisions=tuple(leverage_decisions),
        t06_expansion_decisions=tuple(t06_expansion_decisions),
        t14_derisk_decisions=tuple(t14_derisk_decisions),
        portfolio_shadow_decisions=tuple(
            portfolio_shadow_by_signal[key]
            for key in sorted(portfolio_shadow_by_signal)
        ),
        dynamic_leverage_enabled=lab_dynamic_leverage,
        rational_redeploy_gate_enabled=lab_require_rational_redeploy,
        noncertifying_research_redeploy_enabled=(lab_allow_noncertifying_research_redeploy),
        protected_reinvestment_policy_id=POLICY_ID,
        pool_scope=lab_pool_scope,
        seed_multiplier=lab_seed_multiplier,
    )
