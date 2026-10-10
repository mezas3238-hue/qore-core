from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import capitalizer_causal_loss_pressure_surface_v7 as lab


def test_step_down_never_below_supported_floor() -> None:
    assert lab._step_down(Decimal("1")) == Decimal("0.75")
    assert lab._step_down(Decimal("0.35")) == Decimal("0.20")
    assert lab._step_down(Decimal("0.20")) == Decimal("0.20")


def test_early_breadth_caps_on_global_shock() -> None:
    pressure = lab.PressureState(
        global_support=8,
        global_sum_r="-2.5",
        global_losses=5,
        global_negative_symbols=4,
        severe_support=10,
        severe_sum_r="-2.8",
        severe_losses=5,
        severe_negative_symbols=4,
        session_support=6,
        session_sum_r="-1",
        session_losses=3,
        global_shock=True,
        global_severe=False,
        session_shock=False,
    )
    value, reason = lab._pressure_multiplier(
        policy="EARLY_BREADTH_GUARD",
        base=Decimal("1"),
        current_dd=Decimal("2"),
        pressure=pressure,
    )
    assert value == Decimal("0.35")
    assert reason == "GLOBAL_SHOCK_CAP_035"


def test_v7_does_not_tighten_below_point_two() -> None:
    pressure = lab.PressureState(
        global_support=10,
        global_sum_r="-5",
        global_losses=8,
        global_negative_symbols=6,
        severe_support=10,
        severe_sum_r="-5",
        severe_losses=8,
        severe_negative_symbols=6,
        session_support=6,
        session_sum_r="-3",
        session_losses=5,
        global_shock=True,
        global_severe=True,
        session_shock=True,
    )
    value, reason = lab._pressure_multiplier(
        policy="VELOCITY_CONVEX",
        base=Decimal("0.20"),
        current_dd=Decimal("3"),
        pressure=pressure,
    )
    assert value == Decimal("0.20")
    assert reason == "BASE_ALREADY_MIN"
