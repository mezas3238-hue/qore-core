"""E2 observed-H4: strict as-of with 45/60 and 5m freshness."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.qore_london_eurgbp_h4_observed_e2_v1 import (
    REGIMES, h4_prior,
)

RAID = datetime(2026, 7, 15, 10, 20, tzinfo=UTC)


def m1(at: datetime, p: Decimal) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at, closed_at=at+timedelta(minutes=1),
        open=p, high=p+Decimal("0.0001"), low=p-Decimal("0.0001"),
        close=p, volume=1, digits=5,
    )


def prior() -> dict[datetime, CapitalizerM1Bar]:
    start=datetime(2026, 7, 14, 20, tzinfo=UTC)
    return {
        start+timedelta(minutes=i):m1(
            start+timedelta(minutes=i), Decimal("1.10000")+Decimal(i)*Decimal("0.000001")
        )
        for i in range(720)
    }


def test_observed_h4_allows_sparse_single_missing_minute_per_hour_without_ffill():
    data=prior()
    start=datetime(2026, 7, 14, 20, tzinfo=UTC)
    for h in range(12):
        del data[start+timedelta(hours=h,minutes=20)]
    value=h4_prior(data,RAID,"HIGH")
    assert value["status"]==REGIMES[0]
    assert all(all(n==59 for n in block) for block in value["per_block_hourly_minute_counts"])
    assert value["observed_H4_close_timestamps"][-1] == "2026-07-15T08:00:00+00:00"
    data[RAID+timedelta(minutes=2)]=m1(RAID+timedelta(minutes=2),Decimal("9.9999"))
    assert h4_prior(data,RAID,"HIGH")==value


def test_unknown_when_44_of_60_observed_in_one_hour():
    data=prior()
    for i in range(16):
        del data[datetime(2026,7,14,20,i,tzinfo=UTC)]
    result=h4_prior(data,RAID,"HIGH")
    assert result["status"]=="H4_PROXY_UNKNOWN_LOW_COVERAGE"
    assert result["minutes_observed"]==44


def test_unknown_when_last_close_is_more_than_5_minutes_stale():
    data=prior()
    for i in range(6):
        del data[datetime(2026,7,15,7,59-i,tzinfo=UTC)]
    result=h4_prior(data,RAID,"HIGH")
    assert result["status"]=="H4_PROXY_UNKNOWN_CLOSE_STALE"


def test_opposite_raid_direction_changes_alignment_not_data():
    data=prior()
    assert h4_prior(data,RAID,"HIGH")["status"]==REGIMES[0]
    assert h4_prior(data,RAID,"LOW")["status"]==REGIMES[1]
