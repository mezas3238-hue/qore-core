from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_v4_regime_forensics import (
    _bias_family,
    _body_aligned,
    _metrics,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(
    *,
    opened_at: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=23),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_bias_family_distinguishes_breakout_and_reversal() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    previous = _bar(
        opened_at=opened,
        open_="100",
        high="110",
        low="90",
        close="102",
    )
    breakout = _bar(
        opened_at=opened + timedelta(days=1),
        open_="102",
        high="116",
        low="100",
        close="112",
    )
    reversal = _bar(
        opened_at=opened + timedelta(days=2),
        open_="102",
        high="108",
        low="88",
        close="96",
    )
    assert _bias_family(previous, breakout) == "breakout"
    assert _bias_family(previous, reversal) == "reversal"


def test_previous_body_alignment_is_side_relative() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    bullish = _bar(
        opened_at=opened,
        open_="100",
        high="111",
        low="99",
        close="108",
    )
    assert _body_aligned(bullish, DemoTradingSetupSide.LONG) is True
    assert _body_aligned(bullish, DemoTradingSetupSide.SHORT) is False


def test_metrics_apply_frozen_point_zero_five_r_stress() -> None:
    rows: list[dict[str, object]] = [
        {"signal_at": "2026-01-01T00:00:00+00:00", "symbol": "A", "r_multiple": "1"},
        {"signal_at": "2026-01-02T00:00:00+00:00", "symbol": "A", "r_multiple": "-1"},
        {"signal_at": "2026-01-03T00:00:00+00:00", "symbol": "A", "r_multiple": "0.5"},
    ]
    result = _metrics(rows)
    assert result["sample"] == 3
    assert result["total_r"] == "0.5"
    assert result["mean_r"] == str(Decimal("0.5") / 3)
    assert result["stressed_mean_r"] == str(Decimal("0.35") / 3)
    assert result["max_drawdown_r"] == "1"
