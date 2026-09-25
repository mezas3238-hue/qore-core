from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r118_pre_cisd_failed_attempt_journey as r118,
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


def test_r118_records_failed_series_before_later_confirmed_cisd() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="95", close="98"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="98",
            high="99",
            low="97",
            close="99",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="99",
            high="100",
            low="96",
            close="97",
        ),
        _bar(
            t0 + timedelta(minutes=45),
            open_="97",
            high="101",
            low="96.5",
            close="100.5",
        ),
    )
    journey = r118._cisd_journey(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    )
    assert journey is not None
    assert journey["confirm_index"] == 3
    assert journey["sequence_start"] == 2
    assert journey["sequence_open"] == Decimal("99")
    assert journey["extreme"] == Decimal("96")
    assert len(journey["failed_attempts"]) == 1
    assert journey["failed_attempts"][0]["extreme"] == Decimal("95")


def test_r118_prior_deeper_relation_is_side_aware() -> None:
    failed = ({"extreme": Decimal("95")},)
    assert r118._prior_extreme_relation(
        side=DemoTradingSetupSide.LONG,
        final_extreme=Decimal("96"),
        failed_attempts=failed,
    ) == "PRIOR_DEEPER_THAN_FINAL_PS"
    assert r118._prior_extreme_relation(
        side=DemoTradingSetupSide.LONG,
        final_extreme=Decimal("94"),
        failed_attempts=failed,
    ) == "FINAL_DEEPER_THAN_PRIOR"

    failed_short = ({"extreme": Decimal("105")},)
    assert r118._prior_extreme_relation(
        side=DemoTradingSetupSide.SHORT,
        final_extreme=Decimal("104"),
        failed_attempts=failed_short,
    ) == "PRIOR_DEEPER_THAN_FINAL_PS"
    assert r118._prior_extreme_relation(
        side=DemoTradingSetupSide.SHORT,
        final_extreme=Decimal("106"),
        failed_attempts=failed_short,
    ) == "FINAL_DEEPER_THAN_PRIOR"


def test_r118_attempt_count_bucket_is_fixed() -> None:
    assert r118._attempt_count_bucket(0) == "ZERO"
    assert r118._attempt_count_bucket(1) == "ONE"
    assert r118._attempt_count_bucket(2) == "TWO_PLUS"
    assert r118._attempt_count_bucket(5) == "TWO_PLUS"


def test_r118_source_and_surface_are_pinned() -> None:
    assert r118.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r118.SOURCE_R117_RUN_ID == 35666961998
    assert r118.SOURCE_R117_ARTIFACT_ID == 10668719511
    assert r118.SOURCE_R117_ARTIFACT_DIGEST == (
        "sha256:966a40d7fb9ff2ae11a48a2de1a83b5dcec59d1f6a804da1f64f8139ad6bd984"
    )
