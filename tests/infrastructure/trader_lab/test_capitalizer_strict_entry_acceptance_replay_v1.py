from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import CapitalizerM5Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_entry_acceptance_replay_v1 import (
    IDENTITY,
    _significant_displacement,
    _trace_conditions,
)


def _bar(
    index: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM5Bar:
    opened = datetime(2026, 1, 5, 14, 0, tzinfo=UTC) + timedelta(minutes=5 * index)
    return CapitalizerM5Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _accepted_long_bars() -> tuple[CapitalizerM5Bar, ...]:
    return (
        _bar(0, open_="100", high="101", low="99", close="100.5"),
        _bar(1, open_="100.5", high="101", low="98", close="99.5"),
        _bar(2, open_="99.5", high="101", low="99", close="100.5"),
        _bar(3, open_="100.5", high="103", low="100", close="102"),
        _bar(4, open_="102", high="102.2", low="99", close="100"),
        _bar(5, open_="100", high="100.5", low="97.5", close="99.5"),
        _bar(6, open_="99.5", high="104.5", low="99.3", close="104"),
        _bar(7, open_="104", high="104.5", low="103.5", close="104.2"),
        _bar(8, open_="104", high="104.2", low="102", close="102.8"),
        _bar(9, open_="102.8", high="105", low="102.5", close="104.5"),
        _bar(10, open_="102.7", high="104", low="102.4", close="103.5"),
    )


def test_significant_displacement_requires_directional_body_dominance() -> None:
    assert _significant_displacement(
        _bar(0, open_="100", high="104.5", low="99.8", close="104"),
        CapitalizerSide.LONG,
    )
    assert not _significant_displacement(
        _bar(0, open_="100", high="104.5", low="96", close="101"),
        CapitalizerSide.LONG,
    )


def test_full_m5_surrogate_sequence_reaches_acceptance() -> None:
    bars = _accepted_long_bars()
    trace = _trace_conditions(
        bars,
        confirmation_index=9,
        entry_index=10,
        side=CapitalizerSide.LONG,
    )

    assert trace.liquidity_reference is True
    assert trace.liquidity_raid is True
    assert trace.market_structure_shift is True
    assert trace.significant_displacement is True
    assert trace.fvg_in_displacement is True
    assert trace.retrace_into_fvg is True
    assert trace.anti_chase_entry_inside_fvg is True
    assert trace.ttrades_cisd_protected_swing is True
    assert trace.protected_swing_price == Decimal("102")
    assert trace.rejection_reason == "ACCEPTED_M5_SURROGATE"


def test_entry_open_outside_fvg_is_fail_closed_as_chase() -> None:
    bars = list(_accepted_long_bars())
    original = bars[10]
    bars[10] = CapitalizerM5Bar(
        symbol=original.symbol,
        opened_at=original.opened_at,
        closed_at=original.closed_at,
        open=Decimal("104"),
        high=Decimal("104.5"),
        low=Decimal("103.8"),
        close=Decimal("104.2"),
        volume=None,
        digits=5,
    )
    trace = _trace_conditions(
        tuple(bars),
        confirmation_index=9,
        entry_index=10,
        side=CapitalizerSide.LONG,
    )

    assert trace.retrace_into_fvg is True
    assert trace.anti_chase_entry_inside_fvg is False
    assert trace.ttrades_cisd_protected_swing is False
    assert trace.rejection_reason == "ENTRY_OPEN_OUTSIDE_FVG_CHASE"


def test_replay_identity_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_STRICT_ENTRY_ACCEPTANCE_REPLAY_V1"
