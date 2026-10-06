"""Target-free robust capacity envelope for the CIBO USD60 certification.

This module replaces "use the whole account" capability sizing in the USD60
exam. It does not impose a universal risk percentage. Deployable stop-risk is
derived from current realized capital, operating floor, causal reserves,
capital-source availability, QORE Risk headroom and a frozen drawdown multiple
calibrated exclusively on burned development evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture


@dataclass(frozen=True, slots=True)
class CiboSurvivalEnvelopeCalibration:
    calibration_id: str
    posture: CiboRegimePosture
    certified_drawdown_multiple: Decimal
    evidence_refs: tuple[str, ...]
    frozen_at: datetime
    burned_development_evidence_only: bool = True
    holdout_outcomes_used: bool = False
    economic_target_used: bool = False

    def __post_init__(self) -> None:
        if not self.calibration_id or not self.evidence_refs:
            raise CiboCapitalManagementError(
                "survival-envelope calibration identity/evidence required"
            )
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "survival-envelope posture must be canonical"
            )
        if (
            not isinstance(self.certified_drawdown_multiple, Decimal)
            or not self.certified_drawdown_multiple.is_finite()
            or self.certified_drawdown_multiple <= 0
        ):
            raise CiboCapitalManagementError(
                "certified drawdown multiple must be finite positive Decimal"
            )
        if (
            self.frozen_at.tzinfo is None
            or self.frozen_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "survival-envelope freeze must be timezone-aware"
            )
        if (
            not self.burned_development_evidence_only
            or self.holdout_outcomes_used
            or self.economic_target_used
        ):
            raise CiboCapitalManagementError(
                "survival-envelope calibration governance violation"
            )


@dataclass(frozen=True, slots=True)
class CiboRobustCapitalState:
    realized_capital_usd: Decimal
    minimum_operating_capital_usd: Decimal
    causal_reserve_usd: Decimal
    optionality_reserve_usd: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    source_capacity_usd: Decimal
    committed_stop_risk_usd: Decimal

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if self.realized_capital_usd <= 0:
            raise CiboCapitalManagementError(
                "realized capital must be positive"
            )
        if (
            self.minimum_operating_capital_usd
            + self.causal_reserve_usd
            + self.optionality_reserve_usd
            > self.realized_capital_usd
        ):
            raise CiboCapitalManagementError(
                "operating floor/reserves exceed realized capital"
            )


@dataclass(frozen=True, slots=True)
class CiboRobustCapacityEnvelope:
    posture: CiboRegimePosture
    realized_capital_usd: Decimal
    protected_operating_floor_usd: Decimal
    economic_surplus_usd: Decimal
    drawdown_limited_new_stop_risk_usd: Decimal
    deployable_new_stop_risk_usd: Decimal
    margin_headroom_usd: Decimal
    source_capacity_usd: Decimal
    economic_target_usd: None = None

    def __post_init__(self) -> None:
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "robust capacity posture must be canonical"
            )
        for name in (
            "realized_capital_usd",
            "protected_operating_floor_usd",
            "economic_surplus_usd",
            "drawdown_limited_new_stop_risk_usd",
            "deployable_new_stop_risk_usd",
            "margin_headroom_usd",
            "source_capacity_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if self.economic_target_usd is not None:
            raise CiboCapitalManagementError(
                "robust capacity envelope cannot contain an economic target"
            )
        if self.deployable_new_stop_risk_usd > min(
            self.drawdown_limited_new_stop_risk_usd,
            self.source_capacity_usd,
        ):
            raise CiboCapitalManagementError(
                "deployable risk exceeds calibrated/source capacity"
            )


def derive_robust_capacity_envelope(
    *,
    state: CiboRobustCapitalState,
    calibration: CiboSurvivalEnvelopeCalibration,
) -> CiboRobustCapacityEnvelope:
    """Compute maximum deployable risk consistent with the frozen survival proof."""

    if not isinstance(state, CiboRobustCapitalState):
        raise CiboCapitalManagementError(
            "robust capacity requires canonical capital state"
        )
    if not isinstance(calibration, CiboSurvivalEnvelopeCalibration):
        raise CiboCapitalManagementError(
            "robust capacity requires canonical calibration"
        )
    protected_floor = (
        state.minimum_operating_capital_usd
        + state.causal_reserve_usd
        + state.optionality_reserve_usd
    )
    surplus = max(
        Decimal(0),
        state.realized_capital_usd - protected_floor,
    )
    drawdown_limited = (
        surplus / calibration.certified_drawdown_multiple
    )
    deployable = min(
        drawdown_limited,
        state.hard_risk_headroom_usd,
        state.source_capacity_usd,
    )
    return CiboRobustCapacityEnvelope(
        posture=calibration.posture,
        realized_capital_usd=state.realized_capital_usd,
        protected_operating_floor_usd=protected_floor,
        economic_surplus_usd=surplus,
        drawdown_limited_new_stop_risk_usd=drawdown_limited,
        deployable_new_stop_risk_usd=deployable,
        margin_headroom_usd=state.margin_headroom_usd,
        source_capacity_usd=state.source_capacity_usd,
    )
