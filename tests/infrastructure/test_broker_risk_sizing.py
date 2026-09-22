from decimal import Decimal

import pytest

from qore.infrastructure.broker_risk_sizing import (
    BrokerMinimumVolumeRiskRejectError,
    size_volume_for_risk,
)


def test_minimum_lot_is_requested_when_shared_risk_must_decide() -> None:
    sizing = size_volume_for_risk(
        requested_risk_usd=Decimal("4"),
        stop_loss_per_volume=Decimal("810.8476128"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("50"),
    )
    assert sizing.raw_volume < Decimal("0.01")
    assert sizing.authorized_volume == Decimal("0.01")
    assert sizing.risk_at_minimum_volume_usd == Decimal("8.108476128")
    assert sizing.minimum_volume_uplifted is True


def test_exact_minimum_is_not_false_rejected_by_decimal_floor() -> None:
    sizing = size_volume_for_risk(
        requested_risk_usd=Decimal("8.108476128"),
        stop_loss_per_volume=Decimal("810.8476128"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("50"),
    )
    assert sizing.authorized_volume == Decimal("0.01")
    assert sizing.minimum_volume_uplifted is False


def test_strict_mode_can_still_reject_minimum_volume_uplift() -> None:
    with pytest.raises(BrokerMinimumVolumeRiskRejectError) as captured:
        size_volume_for_risk(
            requested_risk_usd=Decimal("4"),
            stop_loss_per_volume=Decimal("810.8476128"),
            volume_step=Decimal("0.01"),
            minimum_volume=Decimal("0.01"),
            maximum_volume=Decimal("50"),
            allow_minimum_volume_uplift=False,
        )
    telemetry = captured.value.telemetry()
    assert telemetry["risk_decision"] == "RISK_REJECT_MINIMUM_BROKER_VOLUME"
    assert telemetry["risk_at_broker_min_volume"] == "8.108476128"
