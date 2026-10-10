from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    observe_first_m1_fvg_cisd_continuation,
)


def _bar(
    minute: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 2, 10, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=5,
    )


def test_bullish_fvg_retrace_plus_cisd_confirms_continuation() -> None:
    bars = (
        _bar(0, "10.00", "10.10", "9.90", "10.05"),
        _bar(1, "10.05", "10.30", "10.00", "10.25"),
        _bar(2, "10.25", "10.50", "10.20", "10.45"),
        _bar(3, "10.45", "10.48", "10.05", "10.15"),
        _bar(4, "10.15", "10.25", "10.00", "10.08"),
        _bar(5, "10.08", "10.20", "9.95", "10.02"),
        _bar(6, "10.02", "10.20", "10.00", "10.12"),
        _bar(7, "10.12", "10.60", "10.10", "10.55"),
    )
    result = observe_first_m1_fvg_cisd_continuation(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.confirmed is True
    assert result.fvg_lower_price == "10.10"
    assert result.fvg_upper_price == "10.20"
    assert result.outcome_used is False
    assert result.exact_entry_selected is False


def test_wrong_direction_fvg_does_not_confirm() -> None:
    bars = (
        _bar(0, "10.40", "10.50", "10.30", "10.35"),
        _bar(1, "10.35", "10.40", "10.10", "10.15"),
        _bar(2, "10.15", "10.20", "9.90", "9.95"),
        _bar(3, "9.95", "10.30", "9.90", "10.20"),
        _bar(4, "10.20", "10.40", "10.15", "10.35"),
    )
    result = observe_first_m1_fvg_cisd_continuation(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.confirmed is False
