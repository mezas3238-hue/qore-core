from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r114_standard_cisd_ps_anatomy_attribution as r114,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r114_trace_anatomy_tracks_series_extreme_and_confirmation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="98", close="99"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="99",
            high="100",
            low="96",
            close="97",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="97",
            high="101",
            low="96.5",
            close="100.5",
        ),
    )
    trace = r114._trace_anatomy(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    )
    assert trace is not None
    assert trace["sequence_start"] == 0
    assert trace["sequence_end"] == 1
    assert trace["confirm_index"] == 2
    assert trace["sequence_open"] == Decimal("100")
    assert trace["extreme"] == Decimal("96")
    assert trace["extreme_index"] == 1
    assert trace["series_length"] == 2


def test_r114_discrete_buckets_are_fixed_source_anatomy_states() -> None:
    assert r114._series_length_bucket(1) == "ONE"
    assert r114._series_length_bucket(2) == "TWO"
    assert r114._series_length_bucket(3) == "THREE_PLUS"
    assert r114._series_length_bucket(7) == "THREE_PLUS"

    assert r114._slot_bucket(0) == "M15_0"
    assert r114._slot_bucket(1) == "M15_1"
    assert r114._slot_bucket(2) == "M15_2_PLUS"
    assert r114._slot_bucket(8) == "M15_2_PLUS"


def test_r114_extreme_position_is_structural_not_price_threshold() -> None:
    assert r114._extreme_position(
        sequence_start=2,
        sequence_end=2,
        extreme_index=2,
    ) == "ONLY_BAR"
    assert r114._extreme_position(
        sequence_start=2,
        sequence_end=4,
        extreme_index=2,
    ) == "FIRST_BAR"
    assert r114._extreme_position(
        sequence_start=2,
        sequence_end=5,
        extreme_index=4,
    ) == "INTERIOR_BAR"
    assert r114._extreme_position(
        sequence_start=2,
        sequence_end=4,
        extreme_index=4,
    ) == "LAST_BAR"


def test_r114_surface_and_r112_source_are_pinned() -> None:
    assert r114.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r114.SOURCE_R112_RUN_ID == 35661839898
    assert r114.SOURCE_R112_ARTIFACT_ID == 10667714516
    assert r114.SOURCE_R112_ARTIFACT_DIGEST == (
        "sha256:e0b2dfd0363c2920ba7566672ffef05264d69fbfb4778e81de8568dba05f0e53"
    )
