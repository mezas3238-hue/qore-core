from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    ENTRY_IDENTITY,
    WINDOW_END,
    WINDOW_START,
    _candidate_setup,
    _fvg_fill_price,
    _is_directional_raid,
    _significant_displacement,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=datetime(2026, 1, 1, 12, minute, tzinfo=UTC),
        closed_at=datetime(2026, 1, 1, 12, minute, tzinfo=UTC)
        + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def test_contract_window_and_identity_are_frozen() -> None:
    assert WINDOW_START.isoformat() == "2025-09-17T00:00:00+00:00"
    assert WINDOW_END.isoformat() == "2026-09-17T00:00:00+00:00"
    assert ENTRY_IDENTITY == "ICT_2022_RAID_MSS_DISPLACEMENT_FVG_FIRST_RETRACE"


def test_directional_raid_requires_rejection_not_acceptance() -> None:
    long_raid = {
        "side": "LONG",
        "event_labels": ["LOW_RAID_REJECTION"],
    }
    long_acceptance = {
        "side": "LONG",
        "event_labels": ["HIGH_ACCEPTANCE"],
    }
    assert _is_directional_raid(long_raid) is True
    assert _is_directional_raid(long_acceptance) is False


def test_significant_displacement_requires_direction_and_body_dominance() -> None:
    strong = _bar(
        2,
        open_="1.1000",
        high="1.1040",
        low="1.0995",
        close="1.1035",
    )
    weak = _bar(
        3,
        open_="1.1000",
        high="1.1040",
        low="1.0995",
        close="1.1010",
    )
    assert _significant_displacement(strong, side=CapitalizerSide.LONG) is True
    assert _significant_displacement(weak, side=CapitalizerSide.LONG) is False


def test_ict_setup_needs_mss_displacement_and_fvg_but_not_order_block() -> None:
    bars = (
        _bar(0, open_="1.0990", high="1.1000", low="1.0980", close="1.0995"),
        _bar(1, open_="1.0995", high="1.1010", low="1.0990", close="1.1000"),
        _bar(2, open_="1.1000", high="1.1005", low="1.0992", close="1.0996"),
        _bar(3, open_="1.0996", high="1.1030", low="1.0995", close="1.1028"),
        _bar(4, open_="1.1028", high="1.1040", low="1.1012", close="1.1035"),
    )
    setup = _candidate_setup(
        bars,
        displacement_index=3,
        side=CapitalizerSide.LONG,
    )
    assert setup is not None
    assert setup.mss_level == Decimal("1.1010")
    assert setup.fvg_low == Decimal("1.1005")
    assert setup.fvg_high == Decimal("1.1012")


def test_first_fvg_retrace_fills_at_proximal_edge() -> None:
    bars = (
        _bar(0, open_="1.0990", high="1.1000", low="1.0980", close="1.0995"),
        _bar(1, open_="1.0995", high="1.1010", low="1.0990", close="1.1000"),
        _bar(2, open_="1.1000", high="1.1005", low="1.0992", close="1.0996"),
        _bar(3, open_="1.0996", high="1.1030", low="1.0995", close="1.1028"),
        _bar(4, open_="1.1028", high="1.1040", low="1.1012", close="1.1035"),
    )
    setup = _candidate_setup(
        bars,
        displacement_index=3,
        side=CapitalizerSide.LONG,
    )
    assert setup is not None
    retrace = _bar(
        5,
        open_="1.1030",
        high="1.1032",
        low="1.1008",
        close="1.1015",
    )
    assert _fvg_fill_price(
        retrace,
        setup=setup,
        side=CapitalizerSide.LONG,
    ) == Decimal("1.1012")
