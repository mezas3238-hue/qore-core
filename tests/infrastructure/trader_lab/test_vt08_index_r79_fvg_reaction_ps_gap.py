from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r79_fvg_reaction_ps_gap as r79,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
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


def test_r79_detects_bullish_three_candle_fvg() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(start, high="100", low="99"),
        _bar(start + timedelta(minutes=15), high="102", low="100"),
        _bar(start + timedelta(minutes=30), high="104", low="101"),
    )
    fvgs = r79._directional_fvgs(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    )
    assert fvgs == (
        r79.DirectionalFvg(
            low=Decimal("100"),
            high=Decimal("101"),
            formed_index=2,
        ),
    )


def test_r79_requires_strictly_later_retest() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    fvg = r79.DirectionalFvg(
        low=Decimal("100"),
        high=Decimal("101"),
        formed_index=2,
    )
    bars = (
        _bar(start, high="100", low="99"),
        _bar(start + timedelta(minutes=15), high="102", low="100"),
        _bar(start + timedelta(minutes=30), high="104", low="101"),
        _bar(start + timedelta(minutes=45), high="102", low="100.5"),
    )
    assert r79._first_later_retest(bars, fvg=fvg) == 3


def test_r79_no_retest_when_later_bars_do_not_overlap() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    fvg = r79.DirectionalFvg(
        low=Decimal("100"),
        high=Decimal("101"),
        formed_index=2,
    )
    bars = (
        _bar(start, high="100", low="99"),
        _bar(start + timedelta(minutes=15), high="102", low="100"),
        _bar(start + timedelta(minutes=30), high="104", low="101"),
        _bar(start + timedelta(minutes=45), high="105", low="102"),
    )
    assert r79._first_later_retest(bars, fvg=fvg) is None


def test_r79_source_r78_evidence_is_pinned() -> None:
    assert r79.SOURCE_R78_RUN_ID == 35515878213
    assert r79.SOURCE_R78_ARTIFACT_ID == 10606817895
    assert r79.SOURCE_R78_ARTIFACT_DIGEST.startswith("sha256:")
