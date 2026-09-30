from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_timed_fvg_cisd_continuation_v48 import (
    observe_first_timed_fvg_cisd_continuation,
)


def _bar(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48TimedSourceBar:
    opened = datetime(2026, 1, 6, 8, 0, tzinfo=UTC) + timedelta(minutes=15 * index)
    return V48TimedSourceBar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
    )


def test_bullish_timed_fvg_retrace_plus_cisd_confirms_continuation() -> None:
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
    result = observe_first_timed_fvg_cisd_continuation(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.confirmed is True
    assert result.cisd is not None
    assert result.cisd.source_valid is True
    assert result.outcome_used is False


def test_timed_fvg_without_later_cisd_stays_unconfirmed() -> None:
    bars = (
        _bar(0, "10.00", "10.10", "9.90", "10.05"),
        _bar(1, "10.05", "10.30", "10.00", "10.25"),
        _bar(2, "10.25", "10.50", "10.20", "10.45"),
        _bar(3, "10.45", "10.48", "10.05", "10.15"),
        _bar(4, "10.15", "10.25", "10.00", "10.08"),
    )
    result = observe_first_timed_fvg_cisd_continuation(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.confirmed is False
