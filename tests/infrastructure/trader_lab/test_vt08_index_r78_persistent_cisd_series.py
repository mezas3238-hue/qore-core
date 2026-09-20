from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r78_persistent_cisd_series as r78,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
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


def test_r78_persists_series_through_failed_non_opposing_bar() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(
            start,
            open_="100",
            high="100.2",
            low="98",
            close="99",
        ),
        _bar(
            start + timedelta(minutes=15),
            open_="99",
            high="99.7",
            low="98.8",
            close="99.5",
        ),
        _bar(
            start + timedelta(minutes=30),
            open_="99.5",
            high="100.8",
            low="99.4",
            close="100.5",
        ),
    )

    assert v6._first_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    ) is None
    assert r78._persistent_first_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    ) == (2, Decimal("100"), Decimal("98"))


def test_r78_does_not_confirm_without_close_through() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(
            start,
            open_="100",
            high="100.2",
            low="98",
            close="99",
        ),
        _bar(
            start + timedelta(minutes=15),
            open_="99",
            high="99.8",
            low="98.7",
            close="99.6",
        ),
        _bar(
            start + timedelta(minutes=30),
            open_="99.6",
            high="99.9",
            low="99.2",
            close="99.8",
        ),
    )
    assert r78._persistent_first_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    ) is None


def test_r78_extends_same_opposing_series_after_failed_bar() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(
            start,
            open_="100",
            high="100.1",
            low="98.5",
            close="99",
        ),
        _bar(
            start + timedelta(minutes=15),
            open_="99",
            high="99.8",
            low="98.9",
            close="99.5",
        ),
        _bar(
            start + timedelta(minutes=30),
            open_="99.5",
            high="99.6",
            low="97.5",
            close="98",
        ),
        _bar(
            start + timedelta(minutes=45),
            open_="98",
            high="100.5",
            low="97.8",
            close="100.2",
        ),
    )
    assert r78._persistent_first_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    ) == (3, Decimal("100"), Decimal("97.5"))


def test_r78_source_r77_evidence_is_pinned() -> None:
    assert r78.SOURCE_R77_RUN_ID == 35515490620
    assert r78.SOURCE_R77_ARTIFACT_ID == 10607130490
    assert r78.SOURCE_R77_ARTIFACT_DIGEST.startswith("sha256:")
