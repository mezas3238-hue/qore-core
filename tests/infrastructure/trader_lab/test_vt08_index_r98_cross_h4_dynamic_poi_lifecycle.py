from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r98_cross_h4_dynamic_poi_lifecycle as r98,
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


def test_r98_first_invalidation_is_structural() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="102", low="99.2", close="101"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="101",
            high="102",
            low="98.9",
            close="100",
        ),
    )
    assert r98._first_invalidation_index(
        bars,
        start_index=0,
        end_index=2,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    ) == 1


def test_r98_continuation_is_break_and_close() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99.2", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100",
            close="101.5",
        ),
    )
    assert r98._first_continuation_index(
        bars,
        start_index=1,
        end_index=2,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    ) == 1


def test_r98_invalidation_prevents_continuation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99.2", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="98.9",
            close="101.5",
        ),
    )
    assert r98._first_continuation_index(
        bars,
        start_index=1,
        end_index=2,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    ) is None


def test_r98_r97_evidence_is_pinned() -> None:
    assert r98.SOURCE_R97_RUN_ID == 35535136703
    assert r98.SOURCE_R97_ARTIFACT_ID == 10613125272
    assert r98.SOURCE_R97_ARTIFACT_DIGEST == (
        "sha256:97864b91f41ff6578d5c16ebb98a88559795e2698110cb7297d4afad949eebf7"
    )
