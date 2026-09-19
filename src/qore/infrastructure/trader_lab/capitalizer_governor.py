"""Capitalization posture governor for the QORE Capitalizer cognitive layer.

This governor is advisory/fail-closed cognition. It does not own lot sizing, broker access,
or capital authorization; QORE RISK remains sovereign.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizationPosture


@dataclass(frozen=True, slots=True)
class CapitalizerPortfolioState:
    """Decision-time portfolio facts supplied by governed CORE state."""

    day_stop_required: bool = False
    session_stop_required: bool = False
    loss_cluster_active: bool = False
    core_exposure_saturated: bool = False
    uncertainty_high: bool = False
    execution_environment_degraded: bool = False
    session_realized_r: Decimal = Decimal("0")
    session_profit_objective_reached: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.session_realized_r, Decimal) or not self.session_realized_r.is_finite():
            raise ValueError("session_realized_r must be finite")


@dataclass(frozen=True, slots=True)
class CapitalizerGovernorRecommendation:
    posture: CapitalizationPosture
    reasons: tuple[str, ...]
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("Capitalization Governor cannot grant capital authority")


def recommend_capitalization_posture(
    state: CapitalizerPortfolioState,
) -> CapitalizerGovernorRecommendation:
    """Derive a deterministic posture without inventing economic thresholds."""

    if state.day_stop_required:
        return CapitalizerGovernorRecommendation(
            posture=CapitalizationPosture.STOP_DAY,
            reasons=("UPSTREAM_DAY_STOP_REQUIRED",),
        )
    if state.session_stop_required:
        return CapitalizerGovernorRecommendation(
            posture=CapitalizationPosture.STOP_SESSION,
            reasons=("UPSTREAM_SESSION_STOP_REQUIRED",),
        )
    if state.session_profit_objective_reached:
        return CapitalizerGovernorRecommendation(
            posture=CapitalizationPosture.STOP_SESSION,
            reasons=("UPSTREAM_SESSION_PROFIT_OBJECTIVE_REACHED",),
        )

    severe_selectivity: list[str] = []
    if state.loss_cluster_active:
        severe_selectivity.append("LOSS_CLUSTER_ACTIVE")
    if state.core_exposure_saturated:
        severe_selectivity.append("CORE_EXPOSURE_SATURATED")
    if severe_selectivity:
        return CapitalizerGovernorRecommendation(
            posture=CapitalizationPosture.HIGH_SELECTIVITY,
            reasons=tuple(severe_selectivity),
        )

    cautious: list[str] = []
    if state.uncertainty_high:
        cautious.append("UNCERTAINTY_HIGH")
    if state.execution_environment_degraded:
        cautious.append("EXECUTION_ENVIRONMENT_DEGRADED")
    if cautious:
        return CapitalizerGovernorRecommendation(
            posture=CapitalizationPosture.CAUTIOUS,
            reasons=tuple(cautious),
        )

    return CapitalizerGovernorRecommendation(
        posture=CapitalizationPosture.NORMAL,
        reasons=("NO_CAPITALIZATION_RESTRICTION",),
    )
