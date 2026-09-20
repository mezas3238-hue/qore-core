from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r89_execution_path_coverage as r89,
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


def test_r89_retest_is_alternate_after_valid_continuation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99.5", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100.4",
            close="101.8",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="101.8",
            high="102.2",
            low="100.8",
            close="101.4",
        ),
    )
    index = r89._retest_fill_index(
        bars,
        continuation_index=1,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_open=Decimal("100"),
    )
    assert index == 2


def test_r89_retest_fails_if_protected_swing_invalidates_first() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99.5", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100.4",
            close="101.8",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="101.8",
            high="102.2",
            low="98.8",
            close="101.4",
        ),
    )
    assert r89._retest_fill_index(
        bars,
        continuation_index=1,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_open=Decimal("100"),
    ) is None


def test_r89_protected_swing_survival_is_pre_boundary_only() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99.5", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="101.2",
            low="99.2",
            close="100.7",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="100.7",
            high="101.2",
            low="98.8",
            close="99.5",
        ),
    )
    assert r89._ps_survives_until(
        bars,
        confirmed_at=t0,
        boundary=t0 + timedelta(minutes=30),
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    )


def test_r89_owner_anchor_constraints_remain_frozen() -> None:
    assert 14 not in tuple(r89.r4.V7_ANCHORS)
    assert 18 not in tuple(r89.r4.V7_ANCHORS)
    assert tuple(r89.r4.V7_ANCHORS) == (22, 2, 6, 10)


def test_r89_predecessor_runs_are_pinned() -> None:
    assert r89.SOURCE_R85_RUN_ID == 35525680874
    assert r89.SOURCE_R88_RUN_ID == 35526661105
