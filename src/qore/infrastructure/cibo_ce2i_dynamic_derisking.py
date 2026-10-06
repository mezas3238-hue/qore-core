"""CE2I T14 dynamic de-risking contract for CIBO CMA.

CIBO may reduce capital consumption without manufacturing a different technical
stop. Hedging/risk-transfer and convex instruments are intentionally outside
this contract and remain separately gated.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboDeRiskAction(StrEnum):
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    RELEASE_ALL = "RELEASE_ALL"


@dataclass(frozen=True, slots=True)
class CiboDeRiskingInput:
    current_volume: Decimal
    minimum_retained_volume: Decimal
    volume_step: Decimal
    stop_risk_per_volume_usd: Decimal
    margin_per_volume_usd: Decimal
    maximum_retained_stop_risk_usd: Decimal
    maximum_retained_margin_usd: Decimal
    methodology_position_valid: bool

    def __post_init__(self) -> None:
        for name in (
            "current_volume",
            "minimum_retained_volume",
            "volume_step",
            "stop_risk_per_volume_usd",
            "margin_per_volume_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite positive Decimal"
                )
        for name in (
            "maximum_retained_stop_risk_usd",
            "maximum_retained_margin_usd",
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
        if self.minimum_retained_volume > self.current_volume:
            raise CiboCapitalManagementError(
                "minimum retained volume cannot exceed current volume"
            )
        if type(self.methodology_position_valid) is not bool:
            raise CiboCapitalManagementError(
                "methodology_position_valid must be bool"
            )


@dataclass(frozen=True, slots=True)
class CiboDeRiskingDecision:
    action: CiboDeRiskAction
    retained_volume: Decimal
    reduction_volume: Decimal
    retained_stop_risk_usd: Decimal
    released_stop_risk_usd: Decimal
    retained_margin_usd: Decimal
    released_margin_usd: Decimal
    reason: str

    def __post_init__(self) -> None:
        if type(self.action) is not CiboDeRiskAction:
            raise CiboCapitalManagementError(
                "action must be CiboDeRiskAction"
            )
        for name in (
            "retained_volume",
            "reduction_volume",
            "retained_stop_risk_usd",
            "released_stop_risk_usd",
            "retained_margin_usd",
            "released_margin_usd",
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
        if not self.reason:
            raise CiboCapitalManagementError(
                "de-risk decision reason required"
            )
        if self.action is CiboDeRiskAction.HOLD and self.reduction_volume != 0:
            raise CiboCapitalManagementError(
                "HOLD cannot reduce volume"
            )
        if self.action is CiboDeRiskAction.RELEASE_ALL and self.retained_volume != 0:
            raise CiboCapitalManagementError(
                "RELEASE_ALL cannot retain volume"
            )


def plan_dynamic_derisking(
    evidence: CiboDeRiskingInput,
) -> CiboDeRiskingDecision:
    """Return the least reduction required to satisfy current capital ceilings."""

    if not isinstance(evidence, CiboDeRiskingInput):
        raise CiboCapitalManagementError(
            "evidence must be CiboDeRiskingInput"
        )

    current_risk = (
        evidence.current_volume * evidence.stop_risk_per_volume_usd
    )
    current_margin = (
        evidence.current_volume * evidence.margin_per_volume_usd
    )

    if not evidence.methodology_position_valid:
        return _release_all(
            evidence,
            current_risk=current_risk,
            current_margin=current_margin,
            reason="Trader methodology invalidated the position",
        )

    if (
        current_risk <= evidence.maximum_retained_stop_risk_usd
        and current_margin <= evidence.maximum_retained_margin_usd
    ):
        return CiboDeRiskingDecision(
            action=CiboDeRiskAction.HOLD,
            retained_volume=evidence.current_volume,
            reduction_volume=Decimal(0),
            retained_stop_risk_usd=current_risk,
            released_stop_risk_usd=Decimal(0),
            retained_margin_usd=current_margin,
            released_margin_usd=Decimal(0),
            reason="current position already fits retained capital ceilings",
        )

    by_risk = (
        evidence.maximum_retained_stop_risk_usd
        / evidence.stop_risk_per_volume_usd
    )
    by_margin = (
        evidence.maximum_retained_margin_usd
        / evidence.margin_per_volume_usd
    )
    raw_retained = min(evidence.current_volume, by_risk, by_margin)
    steps = (raw_retained / evidence.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    retained = steps * evidence.volume_step

    if retained < evidence.minimum_retained_volume:
        return _release_all(
            evidence,
            current_risk=current_risk,
            current_margin=current_margin,
            reason=(
                "capital ceilings cannot retain methodology/provider minimum "
                "without breaching survival constraints"
            ),
        )

    retained_risk = retained * evidence.stop_risk_per_volume_usd
    retained_margin = retained * evidence.margin_per_volume_usd
    reduction = evidence.current_volume - retained
    if reduction <= 0:
        raise CiboCapitalManagementError(
            "de-risking cap breach produced no executable reduction"
        )
    return CiboDeRiskingDecision(
        action=CiboDeRiskAction.REDUCE,
        retained_volume=retained,
        reduction_volume=reduction,
        retained_stop_risk_usd=retained_risk,
        released_stop_risk_usd=current_risk - retained_risk,
        retained_margin_usd=retained_margin,
        released_margin_usd=current_margin - retained_margin,
        reason=(
            "minimum step-aligned reduction restores risk/margin ceilings "
            "without changing structural stop"
        ),
    )


def _release_all(
    evidence: CiboDeRiskingInput,
    *,
    current_risk: Decimal,
    current_margin: Decimal,
    reason: str,
) -> CiboDeRiskingDecision:
    return CiboDeRiskingDecision(
        action=CiboDeRiskAction.RELEASE_ALL,
        retained_volume=Decimal(0),
        reduction_volume=evidence.current_volume,
        retained_stop_risk_usd=Decimal(0),
        released_stop_risk_usd=current_risk,
        retained_margin_usd=Decimal(0),
        released_margin_usd=current_margin,
        reason=reason,
    )
