from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.r34_xauusd_live import build_r34_opportunity
from qore.infrastructure.r38_eurusd_live import build_r38_opportunity
from qore.infrastructure.r43_gbpusd_live import build_r43_opportunity


def _provider(symbol: str) -> Any:
    return SimpleNamespace(
        provider_symbol=symbol,
        ask=Decimal("100.1"),
        bid=Decimal("99.9"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        contract_size=Decimal("100"),
        open_commission_per_lot_usd=Decimal("2"),
    )


def _signal(*, risk_scale: str = "1") -> Any:
    return SimpleNamespace(
        signal_fingerprint="signal-1",
        side="long",
        certified_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        risk_scale=Decimal(risk_scale),
    )


def test_r34_direct_opportunity_has_no_volume_authority() -> None:
    opportunity = build_r34_opportunity(
        signal=_signal(risk_scale="999"),
        provider_spec=_provider("XAUUSD"),
    )

    assert opportunity.trader_id is TraderLineage.R34_XAUUSD
    assert not hasattr(opportunity, "requested_volume")


def test_r38_direct_opportunity_ignores_legacy_risk_scale() -> None:
    low = build_r38_opportunity(
        signal=_signal(risk_scale="0.01"),
        provider_spec=_provider("EURUSD"),
    )
    high = build_r38_opportunity(
        signal=_signal(risk_scale="999"),
        provider_spec=_provider("EURUSD"),
    )

    assert low == high
    assert low.trader_id is TraderLineage.R38_EURUSD


def test_r43_direct_opportunity_ignores_legacy_risk_scale() -> None:
    low = build_r43_opportunity(
        signal=_signal(risk_scale="0.01"),
        provider_spec=_provider("GBPUSD"),
    )
    high = build_r43_opportunity(
        signal=_signal(risk_scale="999"),
        provider_spec=_provider("GBPUSD"),
    )

    assert low == high
    assert low.trader_id is TraderLineage.R43_GBPUSD
