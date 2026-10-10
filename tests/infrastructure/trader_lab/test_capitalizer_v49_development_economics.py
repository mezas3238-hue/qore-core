from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    IDENTITY as TRADER_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    V49TradeDirection,
    V49TradeIntent,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    _metrics,
    _portfolio_select,
    _replay_one,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 13, 30, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="XAUUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def _intent(entry_at: datetime) -> V49TradeIntent:
    return V49TradeIntent(
        identity=TRADER_IDENTITY,
        symbol="XAUUSD",
        session="NEW_YORK",
        operating_date="2026-01-05",
        direction=V49TradeDirection.LONG,
        entry_at=entry_at,
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("102"),
        trigger_family="LIQUIDITY_SWEEP_CISD",
        h1_state_basis="H1_C2",
    )


def test_target_exit_realizes_planned_r() -> None:
    bars = (
        _bar(0, open_="100", high="101", low="99.5", close="100.5"),
        _bar(1, open_="100.5", high="102.1", low="100.2", close="102"),
    )
    trade = _replay_one(bars, _intent(bars[0].opened_at))
    assert trade is not None
    assert trade.exit_reason == "TARGET"
    assert Decimal(trade.realized_gross_r) == Decimal("2")


def test_same_bar_stop_target_is_fail_closed_stop_first() -> None:
    bars = (
        _bar(0, open_="100", high="102.1", low="98.9", close="100"),
    )
    trade = _replay_one(bars, _intent(bars[0].opened_at))
    assert trade is not None
    assert trade.exit_reason == "STOP"
    assert trade.same_bar_stop_target_ambiguity is True
    assert Decimal(trade.realized_gross_r) == Decimal("-1")


def test_cost_stress_reduces_every_trade_by_explicit_r() -> None:
    bars = (_bar(0, open_="100", high="102.1", low="99.5", close="102"),)
    trade = _replay_one(bars, _intent(bars[0].opened_at))
    assert trade is not None
    gross = _metrics((trade,), cost_r=Decimal("0"))
    stressed = _metrics((trade,), cost_r=Decimal("0.05"))
    assert Decimal(gross.total_r) == Decimal("2")
    assert Decimal(stressed.total_r) == Decimal("1.95")


def test_portfolio_selection_is_chronological_not_outcome_aware() -> None:
    base = datetime(2026, 1, 5, 13, 30, tzinfo=UTC)
    rows = []
    for index in range(5):
        trade = _replay_one(
            (_bar(index, open_="100", high="102.1", low="99.5", close="102"),),
            _intent(base + timedelta(minutes=index)),
        )
        assert trade is not None
        rows.append(trade)
    selected = _portfolio_select(tuple(rows))
    assert len(selected) == 3
    assert [ordinal for ordinal, _ in selected] == [1, 2, 3]
    assert all(trade.outcome_used_for_selection is False for _, trade in selected)
