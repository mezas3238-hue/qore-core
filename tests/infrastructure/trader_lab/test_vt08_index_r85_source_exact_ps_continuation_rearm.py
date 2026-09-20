from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
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


def _candidate(
    *,
    opened: datetime,
    protected: str = "99",
    confirm_index: int = 1,
) -> r85.SourcePsCandidate:
    event = r84.ProtectedSwingEvent(
        symbol="NAS100",
        h4_opened_at=opened,
        side=DemoTradingSetupSide.LONG,
        confirmed_at=opened + timedelta(minutes=30),
        protected_swing=Decimal(protected),
        series_open=Decimal("100"),
        family=r84.FAMILY_LIQUIDITY,
        source_poi_kind=v6.PoiKind.RELEVANT_SWING.value,
        poi_touch_at=opened,
    )
    poi = v6.SourcePoi(
        kind=v6.PoiKind.RELEVANT_SWING,
        low=Decimal("99"),
        high=Decimal("99"),
        observed_at=opened,
    )
    return r85.SourcePsCandidate(
        event=event,
        source_poi=poi,
        confirm_index=confirm_index,
    )


def test_r85_same_c2_valid_continuation_executes_in_body() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(t0, open_="100", high="101", low="99.5", close="100.2"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.2",
            high="101.1",
            low="99.2",
            close="100.8",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="100.8",
            high="102",
            low="100.5",
            close="101.5",
        ),
    )
    h4 = Vt08IndexC2R1Bar(
        opened_at=t0,
        closed_at=t0 + timedelta(hours=4),
        open=Decimal("100"),
        high=Decimal("103"),
        low=Decimal("98"),
        close=Decimal("102"),
    )
    row, reason = r85._executable_from_event(
        _candidate(opened=t0, confirm_index=0),
        inside=inside,
        h4_bar=h4,
        model_kind=v6.H4ModelKind.SAME_C2,
    )
    assert reason == "EXECUTABLE"
    assert row is not None
    assert row.entry == Decimal("101.5")


def test_r85_same_c2_wick_not_body_is_rejected() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(t0, open_="100", high="99.6", low="99", close="99.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="99.5",
            high="99.9",
            low="99.1",
            close="99.8",
        ),
    )
    h4 = Vt08IndexC2R1Bar(
        opened_at=t0,
        closed_at=t0 + timedelta(hours=4),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("98"),
        close=Decimal("99.8"),
    )
    row, reason = r85._executable_from_event(
        _candidate(opened=t0, protected="98.5", confirm_index=0),
        inside=inside,
        h4_bar=h4,
        model_kind=v6.H4ModelKind.SAME_C2,
    )
    assert row is None
    assert reason == "SAME_C2_WICK_NOT_BODY"


def test_r85_owner_disabled_14_is_not_executable() -> None:
    assert 14 not in tuple(r85.r4.V7_ANCHORS)
    assert tuple(r85.r4.V7_ANCHORS) == tuple(
        r85.v7.EXECUTABLE_H4_ANCHORS_NY
    )


def test_r85_r84_evidence_is_pinned() -> None:
    assert r85.SOURCE_R84_RUN_ID == 35520178299
    assert r85.SOURCE_R84_ARTIFACT_ID == 10607704304
    assert r85.SOURCE_R84_ARTIFACT_DIGEST == (
        "sha256:83fca74a1e0537f085871a4638b6af6d0e422094149457ad9a0b908103a6d3eb"
    )
