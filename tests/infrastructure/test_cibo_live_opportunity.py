from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_live_opportunity import build_live_opportunity


def _build(**overrides: object) -> TraderOpportunityEnvelope:
    values: dict[str, object] = {
        "trader_id": TraderLineage.R34_XAUUSD,
        "signal_fingerprint": "signal-1",
        "qore_symbol": "XAUUSD",
        "provider_symbol": "XAUUSD",
        "side": "long",
        "entry_type": "market",
        "certified_entry": Decimal("2600"),
        "execution_entry": Decimal("2601"),
        "stop_loss": Decimal("2590"),
        "take_profit": Decimal("2620"),
        "tick_size": Decimal("0.1"),
        "tick_value": Decimal("1"),
        "margin_per_volume": Decimal("100"),
        "volume_step": Decimal("0.01"),
        "minimum_volume": Decimal("0.01"),
        "maximum_volume": Decimal("100"),
        "broker_risk_buffer": Decimal("1.02"),
        "commission_per_volume_usd": Decimal("2"),
        "maximum_adverse_entry_drift_r": Decimal("0.10"),
        "minimum_execution_steps": 1,
    }
    values.update(overrides)
    return build_live_opportunity(**values)  # type: ignore[arg-type]


def test_builder_produces_volume_free_opportunity() -> None:
    opportunity = _build()

    assert not hasattr(opportunity, "requested_volume")
    assert opportunity.intended_entry == Decimal("2601")
    assert opportunity.stop_loss_per_volume == Decimal("13.26")


def test_adverse_entry_drift_is_preserved_before_cibo_sizing() -> None:
    with pytest.raises(CiboCapitalManagementError, match="drift"):
        _build(execution_entry=Decimal("2602"))


def test_short_geometry_is_supported() -> None:
    opportunity = _build(
        side="short",
        certified_entry=Decimal("2600"),
        execution_entry=Decimal("2599"),
        stop_loss=Decimal("2610"),
        take_profit=Decimal("2580"),
    )

    assert opportunity.side == "short"


def test_vt31_can_require_four_execution_steps_without_sizing() -> None:
    opportunity = _build(
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        provider_symbol="USTEC",
        entry_type="limit",
        certified_entry=Decimal("30000"),
        execution_entry=Decimal("30000"),
        stop_loss=Decimal("29900"),
        take_profit=Decimal("30200"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        commission_per_volume_usd=Decimal("0"),
        maximum_adverse_entry_drift_r=None,
        minimum_execution_steps=4,
    )

    assert opportunity.minimum_execution_steps == 4


def test_invalid_provider_volume_range_fails_closed() -> None:
    with pytest.raises(CiboCapitalManagementError, match="volume range"):
        _build(maximum_volume=Decimal("0.001"))
