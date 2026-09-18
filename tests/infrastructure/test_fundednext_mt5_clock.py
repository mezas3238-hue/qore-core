from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.fundednext_mt5_clock import (
    FUNDEDNEXT_SERVER_TZ,
    NEW_YORK_TZ,
    fundednext_server_epoch_to_new_york,
    normalise_fundednext_server_epoch,
)


def _pseudo_epoch(year: int, month: int, day: int, hour: int) -> int:
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp())


def test_fundednext_summer_server_clock_normalises_to_new_york() -> None:
    raw = _pseudo_epoch(2026, 9, 18, 9)
    utc = normalise_fundednext_server_epoch(raw)
    ny = fundednext_server_epoch_to_new_york(raw)

    assert str(FUNDEDNEXT_SERVER_TZ) == "Europe/Helsinki"
    assert str(NEW_YORK_TZ) == "America/New_York"
    assert utc == datetime(2026, 9, 18, 6, tzinfo=UTC)
    assert ny.isoformat() == "2026-09-18T02:00:00-04:00"


def test_fundednext_winter_server_clock_normalises_to_new_york() -> None:
    raw = _pseudo_epoch(2026, 1, 15, 9)
    utc = normalise_fundednext_server_epoch(raw)
    ny = fundednext_server_epoch_to_new_york(raw)

    assert utc == datetime(2026, 1, 15, 7, tzinfo=UTC)
    assert ny.isoformat() == "2026-01-15T02:00:00-05:00"
