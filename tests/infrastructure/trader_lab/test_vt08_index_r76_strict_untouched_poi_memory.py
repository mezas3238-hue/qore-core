from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r76_strict_untouched_poi_memory as r76,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    high: str,
    low: str,
) -> Vt08IndexC2R1Bar:
    midpoint = (Decimal(high) + Decimal(low)) / Decimal("2")
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=midpoint,
        high=Decimal(high),
        low=Decimal(low),
        close=midpoint,
    )


def test_r76_age_buckets_are_fixed_not_optimized() -> None:
    assert r76._age_bucket(2) == "AGE_2_H4"
    assert r76._age_bucket(3) == "AGE_3_4_H4"
    assert r76._age_bucket(4) == "AGE_3_4_H4"
    assert r76._age_bucket(5) == "AGE_5_8_H4"
    assert r76._age_bucket(9) == "AGE_9PLUS_H4"


def test_r76_first_retouched_is_strictly_after_observation() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    poi = v6.SourcePoi(
        v6.PoiKind.FVG,
        Decimal("100"),
        Decimal("101"),
        start + timedelta(minutes=15),
    )
    bars = (
        _bar(start, high="100.5", low="99.5"),
        _bar(start + timedelta(minutes=15), high="99.9", low="99"),
        _bar(start + timedelta(minutes=30), high="100.2", low="99.8"),
    )
    opened = tuple(bar.opened_at for bar in bars)
    assert r76._first_retouched_at(
        poi,
        bars=bars,
        opened=opened,
    ) == start + timedelta(minutes=30)


def test_r76_expected_no_poi_contract_is_frozen_from_r72() -> None:
    assert r76.EXPECTED_NO_POI == {
        "5Y": 2337,
        "2Y": 936,
        "R66": 934,
    }


def test_r76_source_evidence_is_pinned() -> None:
    assert r76.SOURCE_R72_RUN_ID == 35506163421
    assert r76.SOURCE_R72_ARTIFACT_ID == 10604260215
    assert r76.SOURCE_R75_RUN_ID == 35513157662
    assert r76.SOURCE_R75_ARTIFACT_ID == 10605704489
