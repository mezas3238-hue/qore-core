from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_loss_pressure_surface_v7 as pressure_v7,
)
from qore.infrastructure.trader_lab import capitalizer_dd_path_state_machine_v8 as lab


def _clear_pressure() -> pressure_v7.PressureState:
    return pressure_v7.PressureState(
        global_support=8,
        global_sum_r="1",
        global_losses=2,
        global_negative_symbols=2,
        severe_support=10,
        severe_sum_r="1",
        severe_losses=3,
        severe_negative_symbols=2,
        session_support=6,
        session_sum_r="1",
        session_losses=2,
        global_shock=False,
        global_severe=False,
        session_shock=False,
    )


def test_probe_rejects_active_pressure() -> None:
    pressure = pressure_v7.PressureState(
        global_support=8,
        global_sum_r="-2",
        global_losses=5,
        global_negative_symbols=4,
        severe_support=10,
        severe_sum_r="-3",
        severe_losses=6,
        severe_negative_symbols=4,
        session_support=6,
        session_sum_r="-2",
        session_losses=4,
        global_shock=True,
        global_severe=True,
        session_shock=True,
    )
    assert lab._probe_trigger(
        policy="PROBE_035",
        current_dd=Decimal("4"),
        pressure=pressure,
        recent3_sum=Decimal("2"),
        recent3_positive=3,
        adverse_votes=0,
        favorable_votes=3,
    ) is False


def test_context_probe_requires_favorable_context() -> None:
    pressure = _clear_pressure()
    assert lab._probe_trigger(
        policy="PROBE_CONTEXT_035",
        current_dd=Decimal("4"),
        pressure=pressure,
        recent3_sum=Decimal("1"),
        recent3_positive=2,
        adverse_votes=0,
        favorable_votes=2,
    ) is True
    assert lab._probe_trigger(
        policy="PROBE_CONTEXT_035",
        current_dd=Decimal("4"),
        pressure=pressure,
        recent3_sum=Decimal("1"),
        recent3_positive=2,
        adverse_votes=1,
        favorable_votes=2,
    ) is False


def test_strict_probe_requires_three_recent_winners() -> None:
    pressure = _clear_pressure()
    assert lab._probe_trigger(
        policy="PROBE_STRICT_035",
        current_dd=Decimal("4"),
        pressure=pressure,
        recent3_sum=Decimal("1.25"),
        recent3_positive=3,
        adverse_votes=0,
        favorable_votes=2,
    ) is True
    assert lab._probe_trigger(
        policy="PROBE_STRICT_035",
        current_dd=Decimal("4"),
        pressure=pressure,
        recent3_sum=Decimal("1.25"),
        recent3_positive=2,
        adverse_votes=0,
        favorable_votes=2,
    ) is False


def test_dynamic_recovery_releases_one_level_more_only_when_strong() -> None:
    value, reason = lab._release_multiplier(
        policy="PROBE_CONTEXT_DYNAMIC",
        base=Decimal("0.20"),
        current_dd=Decimal("3.5"),
        favorable_votes=3,
        adverse_votes=0,
    )
    assert value == Decimal("0.55")
    assert reason == "RECOVERY_RELEASE_055"

    conservative, conservative_reason = lab._release_multiplier(
        policy="PROBE_CONTEXT_DYNAMIC",
        base=Decimal("0.20"),
        current_dd=Decimal("4.5"),
        favorable_votes=3,
        adverse_votes=0,
    )
    assert conservative == Decimal("0.35")
    assert conservative_reason == "RECOVERY_RELEASE_035"
