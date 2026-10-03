from decimal import Decimal

from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    _floor_provider_volume,
)


def test_t02_provider_volume_preserves_exact_legal_step() -> None:
    assert _floor_provider_volume(
        requested_volume=Decimal("0.04"),
        volume_step=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    ) == Decimal("0.04")


def test_t02_provider_volume_floors_fractional_target_without_more_risk() -> None:
    requested = Decimal("0.039999999999999999")
    aligned = _floor_provider_volume(
        requested_volume=requested,
        volume_step=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )
    assert aligned == Decimal("0.03")
    assert aligned <= requested
    assert aligned / Decimal("0.01") == (
        aligned / Decimal("0.01")
    ).to_integral_value()


def test_t02_provider_volume_caps_at_provider_maximum() -> None:
    assert _floor_provider_volume(
        requested_volume=Decimal("100.009"),
        volume_step=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    ) == Decimal("100")
