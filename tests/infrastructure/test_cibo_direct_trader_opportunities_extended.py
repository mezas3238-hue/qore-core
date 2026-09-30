from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.ctrader_demo_compat import CTraderDemoSymbolSpecification
from qore.infrastructure.ctrader_demo_vt08_sizing import (
    build_ctrader_demo_vt08_opportunity,
)
from qore.infrastructure.r38_gbpjpy_live import build_r38_gbpjpy_opportunity
from qore.infrastructure.r42_audjpy_live import build_r42_audjpy_opportunity
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboSetup,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt31_nas100_live import build_vt31_opportunity


def _broker(symbol: str, now: datetime) -> Any:
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
        contract_size=Decimal("100000"),
        point=Decimal("0.1"),
        spread_points=Decimal("2"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        trade_enabled=True,
        session_open=True,
        observed_at=now,
        open_commission_per_lot_usd=Decimal("2"),
    )


def _signal(now: datetime, risk_scale: str = "999") -> Any:
    return SimpleNamespace(
        signal_fingerprint="signal-1",
        entry_at=now,
        side="long",
        certified_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        risk_scale=Decimal(risk_scale),
    )


def test_gbpjpy_direct_builder_has_no_sizing_authority() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    opportunity = build_r38_gbpjpy_opportunity(
        signal=_signal(now),
        provider_spec=_broker("GBPJPY", now),
    )

    assert opportunity.trader_id is TraderLineage.R38_GBPJPY
    assert not hasattr(opportunity, "requested_volume")


def test_audjpy_direct_builder_preserves_deadline_but_not_risk_scale() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    low = build_r42_audjpy_opportunity(
        signal=_signal(now, "0.01"),
        provider_spec=_broker("AUDJPY", now),
        now=now,
    )
    high = build_r42_audjpy_opportunity(
        signal=_signal(now, "999"),
        provider_spec=_broker("AUDJPY", now),
        now=now,
    )

    assert low == high
    assert low.trader_id is TraderLineage.R42_AUDJPY


def test_vt31_direct_builder_removes_certified_risk_r_from_opportunity() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    provider = _broker("NDX100", now)
    provider.ask = Decimal("30000.1")
    provider.bid = Decimal("29999.9")
    provider.point = Decimal("1")
    provider.tick_size = Decimal("1")

    opportunity = build_vt31_opportunity(
        signal_fingerprint="vt31-signal",
        side="long",
        entry=Decimal("30000"),
        stop_loss=Decimal("29900"),
        take_profit=Decimal("30200"),
        provider_spec=provider,
        decision_anchor=now,
        now=now,
    )

    assert opportunity.trader_id is TraderLineage.VT31_NAS100
    assert opportunity.minimum_execution_steps == 4
    assert not hasattr(opportunity, "certified_risk_r")
    assert not hasattr(opportunity, "requested_volume")


def test_vt08_direct_builder_does_not_need_equity_or_symbol_bps() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    setup = Vt08ForexCiboSetup(
        signal_fingerprint="vt08-signal",
        setup_fingerprint="vt08-setup",
        qore_symbol="GBPJPY",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        methodology_fingerprint=R315_METHOD_FINGERPRINT,
        risk_policy_fingerprint=R315_RISK_FINGERPRINT,
        decided_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    authorization = evaluate_vt08_forex_cibo(
        setup,
        enabled=True,
        certification_current=True,
        now=now,
    )
    provider = CTraderDemoSymbolSpecification(
        provider_symbol="GBPJPY",
        bid=Decimal("99.9"),
        ask=Decimal("100.1"),
        spread_points=Decimal("2"),
        digits=3,
        point=Decimal("0.001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.001"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("20"),
        trade_enabled=True,
        session_open=True,
        observed_at=now,
        open_commission_per_lot_usd=Decimal("0"),
    )

    opportunity = build_ctrader_demo_vt08_opportunity(
        cibo_authorization=authorization,
        provider_spec=provider,
    )

    assert opportunity.trader_id is TraderLineage.VT08_FOREX
    assert opportunity.qore_symbol == "GBPJPY"
    assert not hasattr(opportunity, "requested_volume")
