from decimal import Decimal

from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)


def _input(
    *,
    current: str = "1.00",
    minimum: str = "0.10",
    step: str = "0.10",
    risk_per_volume: str = "100",
    margin_per_volume: str = "200",
    max_risk: str = "100",
    max_margin: str = "200",
    valid: bool = True,
) -> CiboDeRiskingInput:
    return CiboDeRiskingInput(
        current_volume=Decimal(current),
        minimum_retained_volume=Decimal(minimum),
        volume_step=Decimal(step),
        stop_risk_per_volume_usd=Decimal(risk_per_volume),
        margin_per_volume_usd=Decimal(margin_per_volume),
        maximum_retained_stop_risk_usd=Decimal(max_risk),
        maximum_retained_margin_usd=Decimal(max_margin),
        methodology_position_valid=valid,
    )


def test_position_inside_capital_ceilings_is_held() -> None:
    decision = plan_dynamic_derisking(_input())

    assert decision.action is CiboDeRiskAction.HOLD
    assert decision.retained_volume == Decimal("1.00")
    assert decision.reduction_volume == 0


def test_risk_ceiling_reduces_only_required_step_aligned_volume() -> None:
    decision = plan_dynamic_derisking(
        _input(max_risk="55", max_margin="500")
    )

    assert decision.action is CiboDeRiskAction.REDUCE
    assert decision.retained_volume == Decimal("0.50")
    assert decision.reduction_volume == Decimal("0.50")
    assert decision.retained_stop_risk_usd == Decimal("50.00")
    assert decision.released_stop_risk_usd == Decimal("50.00")


def test_margin_ceiling_can_drive_reduction_independently() -> None:
    decision = plan_dynamic_derisking(
        _input(max_risk="500", max_margin="90")
    )

    assert decision.action is CiboDeRiskAction.REDUCE
    assert decision.retained_volume == Decimal("0.40")
    assert decision.retained_margin_usd == Decimal("80.00")


def test_if_no_minimum_position_can_survive_cibo_requests_full_release() -> None:
    decision = plan_dynamic_derisking(
        _input(max_risk="5", max_margin="10")
    )

    assert decision.action is CiboDeRiskAction.RELEASE_ALL
    assert decision.retained_volume == 0
    assert decision.released_stop_risk_usd == Decimal("100.00")


def test_trader_methodology_invalidation_requests_full_release() -> None:
    decision = plan_dynamic_derisking(_input(valid=False))

    assert decision.action is CiboDeRiskAction.RELEASE_ALL
    assert "methodology invalidated" in decision.reason
