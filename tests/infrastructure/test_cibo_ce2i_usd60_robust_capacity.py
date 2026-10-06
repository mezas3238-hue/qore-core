from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture
from qore.infrastructure.cibo_ce2i_usd60_robust_capacity import (
    CiboRobustCapitalState,
    CiboSurvivalEnvelopeCalibration,
    derive_robust_capacity_envelope,
)


def _calibration(
    multiple: str = "4",
) -> CiboSurvivalEnvelopeCalibration:
    return CiboSurvivalEnvelopeCalibration(
        calibration_id="burned-development:stable:v1",
        posture=CiboRegimePosture.STABLE,
        certified_drawdown_multiple=Decimal(multiple),
        evidence_refs=("phase19:burned", "phase20:monte-carlo"),
        frozen_at=datetime(2026, 9, 28, 12, 45, tzinfo=UTC),
    )


def test_usd60_capacity_is_derived_not_fixed_percentage() -> None:
    state = CiboRobustCapitalState(
        realized_capital_usd=Decimal("60"),
        minimum_operating_capital_usd=Decimal("5"),
        causal_reserve_usd=Decimal("10"),
        optionality_reserve_usd=Decimal("5"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("50"),
        source_capacity_usd=Decimal("40"),
        committed_stop_risk_usd=Decimal("0"),
    )

    envelope = derive_robust_capacity_envelope(
        state=state,
        calibration=_calibration("4"),
    )

    assert envelope.protected_operating_floor_usd == Decimal("20")
    assert envelope.economic_surplus_usd == Decimal("40")
    assert envelope.drawdown_limited_new_stop_risk_usd == Decimal("10")
    assert envelope.deployable_new_stop_risk_usd == Decimal("10")
    assert envelope.economic_target_usd is None


def test_growing_realized_capital_expands_capacity_without_balance_steps() -> None:
    common = dict(
        minimum_operating_capital_usd=Decimal("5"),
        causal_reserve_usd=Decimal("10"),
        optionality_reserve_usd=Decimal("5"),
        hard_risk_headroom_usd=Decimal("1000"),
        margin_headroom_usd=Decimal("1000"),
        source_capacity_usd=Decimal("1000"),
        committed_stop_risk_usd=Decimal("0"),
    )
    low = derive_robust_capacity_envelope(
        state=CiboRobustCapitalState(
            realized_capital_usd=Decimal("60"),
            **common,
        ),
        calibration=_calibration("4"),
    )
    high = derive_robust_capacity_envelope(
        state=CiboRobustCapitalState(
            realized_capital_usd=Decimal("1000"),
            **common,
        ),
        calibration=_calibration("4"),
    )

    assert high.deployable_new_stop_risk_usd > low.deployable_new_stop_risk_usd
    assert high.deployable_new_stop_risk_usd == Decimal("245")


def test_source_capacity_and_qore_risk_headroom_remain_hard_bounds() -> None:
    state = CiboRobustCapitalState(
        realized_capital_usd=Decimal("1000"),
        minimum_operating_capital_usd=Decimal("5"),
        causal_reserve_usd=Decimal("5"),
        optionality_reserve_usd=Decimal("5"),
        hard_risk_headroom_usd=Decimal("7"),
        margin_headroom_usd=Decimal("100"),
        source_capacity_usd=Decimal("6"),
        committed_stop_risk_usd=Decimal("0"),
    )

    envelope = derive_robust_capacity_envelope(
        state=state,
        calibration=_calibration("2"),
    )

    assert envelope.deployable_new_stop_risk_usd == Decimal("6")


def test_reserves_reduce_capacity_without_protecting_entire_usd60_base() -> None:
    state = CiboRobustCapitalState(
        realized_capital_usd=Decimal("60"),
        minimum_operating_capital_usd=Decimal("5"),
        causal_reserve_usd=Decimal("20"),
        optionality_reserve_usd=Decimal("10"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("60"),
        source_capacity_usd=Decimal("60"),
        committed_stop_risk_usd=Decimal("0"),
    )

    envelope = derive_robust_capacity_envelope(
        state=state,
        calibration=_calibration("5"),
    )

    assert envelope.protected_operating_floor_usd == Decimal("35")
    assert envelope.deployable_new_stop_risk_usd == Decimal("5")
    assert envelope.protected_operating_floor_usd < Decimal("60")
