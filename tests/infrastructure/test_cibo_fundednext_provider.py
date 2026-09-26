# ruff: noqa: I001
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_fundednext_provider import (
    build_fundednext_vt08_opportunity,
    fundednext_cibo_symbol_spec,
)
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboAuthorization,
    Vt08ForexCiboSetup,
    evaluate_vt08_forex_cibo,
)


NOW = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)


def _spec(symbol: str = "GBPUSD") -> Mt5SymbolSpecification:
    return Mt5SymbolSpecification(
        provider_symbol=symbol,
        bid=Decimal("1.2500"),
        ask=Decimal("1.2502"),
        spread_points=Decimal("2"),
        digits=5,
        point=Decimal("0.0001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.0001"),
        tick_value=Decimal("10"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("1000"),
        trade_enabled=True,
        session_open=True,
        observed_at=NOW,
    )


def _authorization() -> Vt08ForexCiboAuthorization:
    setup = Vt08ForexCiboSetup(
        signal_fingerprint="signal-1",
        setup_fingerprint="setup-1",
        qore_symbol="GBPUSD",
        side="short",
        entry_type="market",
        intended_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2550"),
        take_profit=Decimal("1.2400"),
        methodology_fingerprint=R315_METHOD_FINGERPRINT,
        risk_policy_fingerprint=R315_RISK_FINGERPRINT,
        decided_at=NOW,
        expires_at=NOW + timedelta(minutes=2),
    )
    return evaluate_vt08_forex_cibo(
        setup,
        enabled=True,
        certification_current=True,
        now=NOW,
    )


def test_fundednext_adapter_adds_official_commission_without_volume() -> None:
    normalized = fundednext_cibo_symbol_spec(
        qore_symbol="GBPUSD",
        side="long",
        spec=_spec(),
    )

    assert normalized.minimum_volume == Decimal("0.01")
    assert normalized.volume_step == Decimal("0.01")
    assert normalized.open_commission_per_lot_usd > 0


def test_vt08_fundednext_opportunity_is_volume_free_and_provider_exact() -> None:
    opportunity = build_fundednext_vt08_opportunity(
        cibo_authorization=_authorization(),
        provider_spec=_spec(),
    )

    assert opportunity.trader_id.value == "VT08_FOREX"
    assert opportunity.qore_symbol == "GBPUSD"
    assert opportunity.minimum_volume == Decimal("0.01")
    assert opportunity.volume_step == Decimal("0.01")
    assert opportunity.stop_loss_per_volume > Decimal("500")
    assert not hasattr(opportunity, "requested_volume")
