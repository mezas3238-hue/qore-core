from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import (
    Phase20MpcKnownOption,
    plan_phase20i_receding_horizon_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture


def _option(
    opportunity_id: str,
    step: int,
    risk: str,
    margin: str,
) -> Phase20MpcKnownOption:
    return Phase20MpcKnownOption(
        opportunity_id=opportunity_id,
        decision_step=step,
        minimum_stop_risk_usd=Decimal(risk),
        minimum_margin_usd=Decimal(margin),
    )


def test_phase20i_finite_horizon_uses_one_representative_per_step() -> None:
    plan = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=(
            _option("step1-margin-heavy", 1, "4", "80"),
            _option("step1-balanced", 1, "10", "20"),
            _option("step2", 2, "6", "30"),
            _option("outside", 4, "15", "90"),
        ),
    )

    assert plan.considered_option_ids == (
        "step1-balanced",
        "step1-margin-heavy",
        "step2",
    )
    assert plan.representative_option_ids == ("step1-balanced", "step2")
    assert plan.reserve_stop_risk_usd == Decimal("10")
    assert plan.reserve_margin_usd == Decimal("30")
    assert plan.deployable_stop_risk_usd == Decimal("10")
    assert plan.deployable_margin_usd == Decimal("70")
    assert plan.horizon_fully_coverable is True


def test_phase20i_receding_horizon_replans_from_current_step() -> None:
    options = (
        _option("step1", 1, "4", "20"),
        _option("step2", 2, "6", "30"),
        _option("step4", 4, "15", "90"),
    )
    first = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=options,
    )
    second = plan_phase20i_receding_horizon_capacity(
        current_step=2,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=options,
    )

    assert first.considered_option_ids == ("step1", "step2")
    assert first.reserve_stop_risk_usd == Decimal("6")
    assert first.reserve_margin_usd == Decimal("30")
    assert second.considered_option_ids == ("step4",)
    assert second.reserve_stop_risk_usd == Decimal("15")
    assert second.reserve_margin_usd == Decimal("90")


def test_phase20i_recovery_preserves_complete_capacity() -> None:
    plan = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=3,
        posture=CiboRegimePosture.RECOVERY,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=(_option("future", 2, "10", "40"),),
    )

    assert plan.reserve_stop_risk_usd == Decimal("60")
    assert plan.reserve_margin_usd == Decimal("500")
    assert plan.deployable_stop_risk_usd == 0
    assert plan.deployable_margin_usd == 0
    assert plan.horizon_fully_coverable is True


def test_phase20i_empty_horizon_reserves_nothing() -> None:
    plan = plan_phase20i_receding_horizon_capacity(
        current_step=5,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=(_option("past", 2, "5", "10"),),
    )

    assert plan.considered_option_ids == ()
    assert plan.reserve_stop_risk_usd == 0
    assert plan.reserve_margin_usd == 0
    assert plan.deployable_stop_risk_usd == Decimal("20")
    assert plan.deployable_margin_usd == Decimal("100")


def test_phase20i_insufficient_headroom_is_explicit_not_invented() -> None:
    plan = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("20"),
        known_options=(_option("too-large", 1, "10", "40"),),
    )

    assert plan.horizon_fully_coverable is False
    assert plan.reserve_stop_risk_usd == Decimal("5")
    assert plan.reserve_margin_usd == Decimal("20")
    assert plan.deployable_stop_risk_usd == 0
    assert plan.deployable_margin_usd == 0


def test_phase20i_duplicate_option_identity_fails_closed() -> None:
    with pytest.raises(CiboCapitalManagementError, match="unique"):
        plan_phase20i_receding_horizon_capacity(
            current_step=0,
            horizon_steps=2,
            posture=CiboRegimePosture.STABLE,
            hard_risk_headroom_usd=Decimal("20"),
            margin_headroom_usd=Decimal("100"),
            known_options=(
                _option("dup", 1, "4", "20"),
                _option("dup", 2, "5", "30"),
            ),
        )


def test_phase20i_contract_has_no_forecast_or_runtime_authority() -> None:
    plan = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=(_option("future", 1, "4", "20"),),
    )

    assert plan.forecast_model_used is False
    assert plan.outcome_aware is False
    assert plan.validation_tuned is False
    assert plan.phase19j_burned_validation_reused is False
    assert plan.policy_certified is False
    assert plan.allocation_authority is False
    assert plan.risk_authority is False
    assert plan.execution_authority is False
    assert plan.live_authorized is False
    assert plan.real_capital_authorized is False
