from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_cibo_complete_ledgers import (
    LEDGER_NAMES,
    _cross_index_ledger,
    _day_behavior,
    _penetration_fraction,
    _sync_classification,
    _touch_payload,
)
from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import Bar
from qore.infrastructure.trader_lab.vt08_index_reaction_structure_atlas import StructureZone


def _bar(
    minute: int,
    *,
    opened: str,
    high: str,
    low: str,
    closed: str,
) -> Bar:
    start = datetime(2024, 1, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal(opened),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(closed),
    )


def _trade(
    symbol: str,
    signal_minute: int,
    *,
    side: str = "long",
    half_r_minute: int | None = 30,
    exit_reason: str = "target",
) -> dict[str, object]:
    signal = datetime(2024, 1, 2, 12, 0, tzinfo=UTC) + timedelta(
        minutes=signal_minute
    )
    half_at = (
        signal + timedelta(minutes=half_r_minute)
        if half_r_minute is not None
        else None
    )
    return {
        "symbol": symbol,
        "signal_at": signal.isoformat(),
        "side": side,
        "anchor_hour_new_york": 6,
        "relative_strength_rank": 1,
        "peer_alignment_count": 2,
        "exit_reason": exit_reason,
        "time_to_favorable_levels": {
            "0.5": {
                "hit": half_at is not None,
                "minutes": half_r_minute,
                "at": half_at.isoformat() if half_at else None,
            },
            "1": {
                "hit": True,
                "minutes": 60,
                "at": (signal + timedelta(minutes=60)).isoformat(),
            },
            "2": {
                "hit": True,
                "minutes": 120,
                "at": (signal + timedelta(minutes=120)).isoformat(),
            },
            "3": {"hit": False, "minutes": None, "at": None},
            "5": {"hit": False, "minutes": None, "at": None},
        },
    }


def test_structure_touch_penetration_and_dwell_are_mechanical() -> None:
    zone = StructureZone(
        kind="order-block",
        side="bullish",
        formed_at=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
        confirmed_at=datetime(2024, 1, 2, 9, 30, tzinfo=UTC),
        low=Decimal("9"),
        high=Decimal("10"),
        definition="synthetic",
    )
    bars = (
        _bar(0, opened="10.2", high="10.3", low="9.7", closed="10.1"),
        _bar(15, opened="10.1", high="10.2", low="9.4", closed="9.9"),
    )
    assert _penetration_fraction(zone, bars[0]) == Decimal("0.3")
    payload = _touch_payload(zone, bars, bars[-1].closed_at + timedelta(minutes=1))
    assert payload is not None
    assert payload["touch_count"] == 2
    assert payload["dwell_minutes"] == 30
    assert payload["max_penetration_fraction"] == "0.6"


def test_cross_index_ledger_identifies_signal_and_departure_leaders() -> None:
    rows = _cross_index_ledger(
        (
            _trade("NAS100", 0, half_r_minute=45),
            _trade("SP500", 15, half_r_minute=15),
            _trade("US30", 30, half_r_minute=30),
        )
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["signal_leader"] == "NAS100"
    assert row["departure_leader_0_5r"] == "SP500"
    assert row["side_agreement"] is True


def test_daily_path_labels_clear_directional_expansion() -> None:
    bars = (
        _bar(0, opened="10", high="10.2", low="9.9", closed="10.1"),
        _bar(15, opened="10.1", high="10.8", low="10", closed="10.7"),
        _bar(30, opened="10.7", high="11.5", low="10.6", closed="11.4"),
    )
    assert _day_behavior(bars)["descriptor"] == "directional-expansion-like"


def test_sync_class_distinguishes_stop_before_later_expansion() -> None:
    trade = _trade("NAS100", 0, exit_reason="stop")
    assert _sync_classification(trade) == "STOPPED_BEFORE_LATER_2R_EXPANSION"
    assert len(LEDGER_NAMES) == 8
