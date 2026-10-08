"""CEL-5 stressed-loss-aware marginal leverage utility.

This engine evaluates the *next proposed exposure increment* before it enters
the existing GEN-C6 Internal Capital Market. It does not allocate capital and
does not replace GEN-C6. The result is a research eligibility disposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_efficient_exposure import (
    CiboCapitalEfficientExposureState,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_four_motor_policy import (
    ZERO,
    FourMotorObservation,
    FourMotorPolicyError,
    FourMotorProposal,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)


class CiboMarginalLeverageDisposition(StrEnum):
    ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET = (
        "ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET"
    )
    REDUCE_INCREMENT = "REDUCE_INCREMENT"
    RESERVE_DOMINATED = "RESERVE_DOMINATED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CiboMarginalLeveragePolicy:
    policy_id: str
    minimum_net_return_per_stressed_loss: Decimal
    minimum_net_return_per_requested_capital: Decimal
    maximum_stressed_loss_headroom_pressure: Decimal
    maximum_margin_headroom_pressure: Decimal
    maximum_concentration_per_requested_capital: Decimal
    maximum_drawdown_proxy_per_requested_capital: Decimal
    maximum_epistemic_uncertainty: Decimal
    maximum_capital_minutes: Decimal
    source_only_calibration: bool
    evidence_refs: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise CiboCompoundCapitalError(
                "CEL-5 policy_id is required"
            )
        for name in (
            "minimum_net_return_per_stressed_loss",
            "minimum_net_return_per_requested_capital",
            "maximum_stressed_loss_headroom_pressure",
            "maximum_margin_headroom_pressure",
            "maximum_concentration_per_requested_capital",
            "maximum_drawdown_proxy_per_requested_capital",
            "maximum_epistemic_uncertainty",
            "maximum_capital_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"CEL-5 {name} must be finite non-negative Decimal"
                )
        if not self.source_only_calibration:
            raise CiboCompoundCapitalError(
                "CEL-5 policy calibration must be source-only"
            )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise CiboCompoundCapitalError(
                "CEL-5 policy evidence refs must be non-empty and canonical"
            )
        if self.productive_authority:
            raise CiboCompoundCapitalError(
                "CEL-5 research policy cannot authorize production"
            )


@dataclass(frozen=True, slots=True)
class CiboMarginalLeverageAssessment:
    candidate_id: str
    disposition: CiboMarginalLeverageDisposition
    net_expected_return_usd: Decimal
    net_return_per_stressed_loss: Decimal
    net_return_per_requested_capital: Decimal
    capital_time_productivity: Decimal
    stressed_loss_headroom_pressure: Decimal
    margin_headroom_pressure: Decimal
    concentration_per_requested_capital: Decimal
    drawdown_proxy_per_requested_capital: Decimal
    epistemic_uncertainty: Decimal
    reserve_utility_per_capital: Decimal
    reason_codes: tuple[str, ...]
    allocation_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "CEL-5 candidate_id is required"
            )
        if not self.reason_codes:
            raise CiboCompoundCapitalError(
                "CEL-5 assessment requires reason codes"
            )
        for name in (
            "net_expected_return_usd",
            "net_return_per_stressed_loss",
            "net_return_per_requested_capital",
            "capital_time_productivity",
            "stressed_loss_headroom_pressure",
            "margin_headroom_pressure",
            "concentration_per_requested_capital",
            "drawdown_proxy_per_requested_capital",
            "epistemic_uncertainty",
            "reserve_utility_per_capital",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"CEL-5 {name} must be finite Decimal"
                )
        if (
            self.allocation_authority
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCompoundCapitalError(
                "CEL-5 assessment cannot carry runtime authority"
            )


def _positive(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCompoundCapitalError(
            f"CEL-5 {name} must be finite positive Decimal"
        )


def assess_marginal_leverage_utility(
    *,
    candidate_id: str,
    exposure: CiboCapitalEfficientExposureState,
    marginal: MarginalCapitalUtilityEvidence,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    reserve_utility_per_capital: Decimal,
    policy: CiboMarginalLeveragePolicy,
) -> CiboMarginalLeverageAssessment:
    """Decide whether the next exposure increment deserves GEN-C6 competition."""

    if not isinstance(exposure, CiboCapitalEfficientExposureState):
        raise CiboCompoundCapitalError(
            "CEL-5 requires capital-efficient exposure state"
        )
    if not isinstance(marginal, MarginalCapitalUtilityEvidence):
        raise CiboCompoundCapitalError(
            "CEL-5 requires GEN-C4 marginal evidence"
        )
    if not isinstance(policy, CiboMarginalLeveragePolicy):
        raise CiboCompoundCapitalError(
            "CEL-5 requires canonical policy"
        )
    _positive(hard_risk_headroom_usd, "hard_risk_headroom_usd")
    _positive(margin_headroom_usd, "margin_headroom_usd")
    if (
        not isinstance(reserve_utility_per_capital, Decimal)
        or not reserve_utility_per_capital.is_finite()
    ):
        raise CiboCompoundCapitalError(
            "CEL-5 reserve utility must be finite Decimal"
        )
    if marginal.decision_at != exposure.decision_at:
        raise CiboCompoundCapitalError(
            "CEL-5 decision-time binding drift"
        )
    if marginal.outcome_present:
        raise CiboCompoundCapitalError(
            "CEL-5 cannot consume outcome-bearing marginal evidence"
        )

    requested = marginal.requested_incremental_capital_usd
    _positive(requested, "requested_incremental_capital_usd")
    duration = marginal.expected_capital_minutes
    _positive(duration, "expected_capital_minutes")

    net = (
        marginal.expected_incremental_return_usd
        - marginal.incremental_execution_cost_usd
        - marginal.incremental_optionality_consumed_usd
    )
    stressed = exposure.stressed_economic_loss_usd
    _positive(stressed, "stressed_economic_loss_usd")

    return_per_stressed = net / stressed
    return_per_capital = net / requested
    capital_time_productivity = net / (requested * duration)
    stressed_pressure = stressed / hard_risk_headroom_usd
    margin_pressure = exposure.margin_occupancy_usd / margin_headroom_usd
    concentration = (
        marginal.incremental_concentration_risk_usd / requested
    )
    drawdown = marginal.incremental_drawdown_risk_proxy_usd / requested
    uncertainty = marginal.epistemic_uncertainty

    reasons: list[str] = []
    insufficient = False
    reduce_increment = False
    reserve_dominated = False

    if uncertainty > policy.maximum_epistemic_uncertainty:
        insufficient = True
        reasons.append("EPISTEMIC_UNCERTAINTY_TOO_HIGH")
    if duration > policy.maximum_capital_minutes:
        reserve_dominated = True
        reasons.append("CAPITAL_DURATION_TOO_HIGH")
    if stressed_pressure > policy.maximum_stressed_loss_headroom_pressure:
        reduce_increment = True
        reasons.append("STRESSED_LOSS_PRESSURE_TOO_HIGH")
    if margin_pressure > policy.maximum_margin_headroom_pressure:
        reduce_increment = True
        reasons.append("MARGIN_PRESSURE_TOO_HIGH")
    if concentration > policy.maximum_concentration_per_requested_capital:
        reduce_increment = True
        reasons.append("CONCENTRATION_PRESSURE_TOO_HIGH")
    if drawdown > policy.maximum_drawdown_proxy_per_requested_capital:
        reduce_increment = True
        reasons.append("DRAWDOWN_PRESSURE_TOO_HIGH")
    if net <= 0:
        reserve_dominated = True
        reasons.append("NET_INCREMENTAL_RETURN_NON_POSITIVE")
    if (
        return_per_stressed
        < policy.minimum_net_return_per_stressed_loss
    ):
        reserve_dominated = True
        reasons.append("RETURN_PER_STRESSED_LOSS_BELOW_HURDLE")
    if (
        return_per_capital
        < policy.minimum_net_return_per_requested_capital
    ):
        reserve_dominated = True
        reasons.append("RETURN_PER_CAPITAL_BELOW_HURDLE")
    if return_per_capital <= reserve_utility_per_capital:
        reserve_dominated = True
        reasons.append("RESERVE_UTILITY_DOMINATES")

    if insufficient:
        disposition = CiboMarginalLeverageDisposition.INSUFFICIENT
    elif reduce_increment:
        disposition = CiboMarginalLeverageDisposition.REDUCE_INCREMENT
    elif reserve_dominated:
        disposition = CiboMarginalLeverageDisposition.RESERVE_DOMINATED
    else:
        disposition = (
            CiboMarginalLeverageDisposition.ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET
        )
        reasons.append("NEXT_INCREMENT_PASSES_MARGINAL_UTILITY_HURDLES")

    return CiboMarginalLeverageAssessment(
        candidate_id=candidate_id,
        disposition=disposition,
        net_expected_return_usd=net,
        net_return_per_stressed_loss=return_per_stressed,
        net_return_per_requested_capital=return_per_capital,
        capital_time_productivity=capital_time_productivity,
        stressed_loss_headroom_pressure=stressed_pressure,
        margin_headroom_pressure=margin_pressure,
        concentration_per_requested_capital=concentration,
        drawdown_proxy_per_requested_capital=drawdown,
        epistemic_uncertainty=uncertainty,
        reserve_utility_per_capital=reserve_utility_per_capital,
        reason_codes=tuple(sorted(set(reasons))),
    )



def propose_p0_adaptive_leverage_vote(observation: FourMotorObservation) -> FourMotorProposal:
    """Real USD margin and broker-unit lot capacity, not abstract leverage."""
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("canonical observation required")
    available = max(ZERO, observation.broker_free_margin_usd
                    - observation.broker_margin_reservations_usd)
    margin_cap = available * Decimal("0.8")
    volume_room = min(
        max(ZERO, observation.symbol_max_lots - observation.open_and_reserved_direction_lots),
        max(ZERO, observation.provider_direction_max_lots
            - observation.open_and_reserved_direction_lots),
    )
    max_lots = min(volume_room, margin_cap / observation.broker_margin_usd_per_lot)
    reasons = ("BROKER_MARGIN_PER_WHOLE_LOT_USD",
               "FREE_MARGIN_MINUS_HELD_MARGIN",
               "DIRECTIONAL_AND_PROVIDER_VOLUME_CONCENTRATION",
               "BROKER_ORDER_CHECK_STILL_REQUIRED")
    return FourMotorProposal("ADAPTIVE_LEVERAGE", observation,
                             {"approved_max_lots": str(max_lots),
                              "approved_margin_usd": str(margin_cap)}, reasons)
