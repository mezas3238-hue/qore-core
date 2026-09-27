from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ctrader_demo_sizing import (
    build_ctrader_demo_cibo_sizing,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState

NOW = datetime(2026, 9, 27, 20, 0, tzinfo=UTC)


def _account() -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("1000"),
        equity=Decimal("1000"),
        margin=Decimal("100"),
        free_margin=Decimal("500"),
        observed_at=NOW,
    )


def _opportunity(trader: TraderLineage) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=f"signal-{trader.value}",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("200"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def test_demo_cibo_uses_full_account_not_one_seventh_trader_slice() -> None:
    sizing = build_ctrader_demo_cibo_sizing(
        request_id="demo-max-1",
        opportunity=_opportunity(TraderLineage.R38_EURUSD),
        account_ref="demo-account",
        account_state=_account(),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )

    assert sizing.account_capital_usd == Decimal("1000")
    assert sizing.plan.action is CapitalAction.OPEN_CAPABILITY_MAX
    assert sizing.plan.volume == Decimal("2.50")
    assert sizing.plan.stop_risk_usd == Decimal("250.00")
    assert sizing.plan.margin_usd == Decimal("500.00")
    assert sizing.request.strategy_requested_risk_usd is None


def test_demo_same_geometry_has_same_cibo_size_across_trader_lineages() -> None:
    first = build_ctrader_demo_cibo_sizing(
        request_id="demo-max-r38",
        opportunity=_opportunity(TraderLineage.R38_EURUSD),
        account_ref="demo-account",
        account_state=_account(),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )
    second = build_ctrader_demo_cibo_sizing(
        request_id="demo-max-r43",
        opportunity=_opportunity(TraderLineage.R43_GBPUSD),
        account_ref="demo-account",
        account_state=_account(),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )

    assert first.plan.volume == second.plan.volume
    assert first.request.requested_stop_risk == second.request.requested_stop_risk
