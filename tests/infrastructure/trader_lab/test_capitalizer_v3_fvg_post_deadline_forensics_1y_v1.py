from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_v3_fvg_post_deadline_forensics_1y_v1 import (
    ARCHITECTURE,
    EXPECTED_V3_MAX3,
    EXPECTED_V3_NO_FILL_COHORT,
    OBSERVATION_MINUTES,
    _breach_between,
    _touch_bucket,
)


def _bar(at: datetime, low: str, high: str) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("1.10"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("1.10"),
        volume=None,
        digits=5,
    )


def test_post_deadline_contract_is_observational() -> None:
    assert ARCHITECTURE == "V3_FROZEN_FVG_NO_FILL_POST_H1_OBSERVATION_ONLY"
    assert EXPECTED_V3_NO_FILL_COHORT == 258
    assert EXPECTED_V3_MAX3 == 226
    assert OBSERVATION_MINUTES == 60


def test_touch_buckets_are_predeclared() -> None:
    assert _touch_bucket(None) == "NO_TOUCH_60"
    assert _touch_bucket(0) == "00_05"
    assert _touch_bucket(5) == "00_05"
    assert _touch_bucket(6) == "06_15"
    assert _touch_bucket(15) == "06_15"
    assert _touch_bucket(16) == "16_30"
    assert _touch_bucket(30) == "16_30"
    assert _touch_bucket(31) == "31_59"


def test_breach_between_respects_time_and_side() -> None:
    start = datetime(2026, 9, 22, 10, tzinfo=UTC)
    bars = (
        _bar(start, "1.09", "1.11"),
        _bar(start + timedelta(minutes=1), "1.07", "1.12"),
    )

    assert not _breach_between(
        bars,
        side=CapitalizerSide.LONG,
        level=Decimal("1.08"),
        start=start,
        end_exclusive=start + timedelta(minutes=1),
    )
    assert _breach_between(
        bars,
        side=CapitalizerSide.LONG,
        level=Decimal("1.08"),
        start=start,
        end_exclusive=start + timedelta(minutes=2),
    )
