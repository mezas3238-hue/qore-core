from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r87_dynamic_liquidity_rearm as r87,
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


def test_r87_short_term_swing_is_causal_three_bar_pivot() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="101", high="102", low="100", close="101"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="101",
            high="101.5",
            low="99",
            close="100",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="100",
            high="102",
            low="100",
            close="101.5",
        ),
    )
    swings = r84._short_term_swings(
        bars,
        side=DemoTradingSetupSide.LONG,
    )
    assert swings == ((1, Decimal("99"), 2),)


def test_r87_dynamic_liquidity_rearm_requires_post_cursor_sweep() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="101", high="102", low="100", close="101"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="101",
            high="101.5",
            low="99",
            close="100",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="100",
            high="102",
            low="100",
            close="101.5",
        ),
        _bar(
            t0 + timedelta(minutes=45),
            open_="100.5",
            high="101",
            low="98.5",
            close="99",
        ),
        _bar(
            t0 + timedelta(minutes=60),
            open_="99",
            high="101",
            low="98.8",
            close="100.8",
        ),
        _bar(
            t0 + timedelta(minutes=75),
            open_="100.8",
            high="102",
            low="100.5",
            close="101.8",
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
    rows = r87._dynamic_liquidity_rearms_after(
        inside=bars,
        h4_bar=h4,
        side=DemoTradingSetupSide.LONG,
        model_kind=v6.H4ModelKind.SAME_C2,
        after_continuation_index=2,
    )
    assert rows
    assert all(row.continuation_index > 2 for row in rows)


def test_r87_r85_evidence_is_pinned() -> None:
    assert r87.SOURCE_R85_RUN_ID == 35525680874
    assert r87.SOURCE_R85_ARTIFACT_ID == 10609721617
    assert r87.SOURCE_R85_ARTIFACT_DIGEST.startswith("sha256:")
