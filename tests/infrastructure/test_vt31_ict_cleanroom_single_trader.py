"""Exactly one VT31 trader; London and New York are internal models."""
from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import (
    INSTRUMENT,
    TRADER_ID,
    SESSION_MODEL,
    VT31Trader,
)

NY = ZoneInfo("America/New_York")


def bar(opened: datetime) -> M1Bar:
    return M1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"), high=Decimal("101"),
        low=Decimal("99"), close=Decimal("100"),
    )


def test_single_trader_shares_one_cognition_across_london_and_new_york() -> None:
    market_cognition = VT31CleanroomCognition()
    trader = VT31Trader(cognition=market_cognition)
    assert trader.cognition is market_cognition
    local = datetime(2025, 7, 7, tzinfo=NY)
    observed = []
    for hour in (3, 10, 14):
        start = local.replace(hour=hour, minute=0).astimezone(UTC)
        for index in range(3):
            out = trader.on_closed_m1(
                bar(start + timedelta(minutes=index))
            )
            observed.append(out)
            assert out.trader_id == TRADER_ID == "VT31"
            assert out.instrument == INSTRUMENT == "NAS100"
            assert out.order_authorized is False
            assert out.position_authorized is False

    assert observed[0].session_window is SessionId.LONDON
    assert observed[0].session_model == "LONDON"
    assert observed[3].session_window is SessionId.NY_AM
    assert observed[3].session_model == "NEW_YORK"
    assert observed[6].session_window is SessionId.NY_PM
    assert observed[6].session_model == "NEW_YORK"
    state = trader.snapshot()
    assert state["trader_id"] == "VT31"
    assert state["registered_trader_count"] == 1
    assert state["session_models"] == ("LONDON", "NEW_YORK")
    assert state["ny_windows"] == ("VT31_NY_AM", "VT31_NY_PM")
    assert state["source_windows_seen"] == 3
    assert len(state["session_windows"]) == 3
    assert state["single_cognitive_memory"] is True
    assert state["certified"] is False
    assert state["live_authorized"] is False


def test_single_trader_carries_context_outside_both_sessions() -> None:
    trader = VT31Trader()
    outside = datetime(2025, 7, 7, 9, 0, tzinfo=UTC)
    out = trader.on_closed_m1(bar(outside))  # 05:00 NY
    assert out.session_model is None
    assert out.cognition is None
    assert trader.total_closed_m1 == 1
    assert trader.snapshot()["source_windows_seen"] == 0


def test_utc_dst_does_not_create_a_second_london_trader() -> None:
    for local in (
        datetime(2026, 3, 3, tzinfo=NY),
        datetime(2026, 3, 17, tzinfo=NY),
        datetime(2026, 10, 27, tzinfo=NY),
    ):
        t = VT31Trader()
        london = t.on_closed_m1(
            bar(local.replace(hour=3).astimezone(UTC))
        )
        assert london.session_model == "LONDON"
        assert london.trader_id == "VT31"
        assert t.snapshot()["registered_trader_count"] == 1


def test_cannot_initialize_in_the_middle_of_source_window() -> None:
    t = VT31Trader()
    local = datetime(2025, 7, 7, 3, 12, tzinfo=NY)
    with pytest.raises(ValueError, match="partial Silver Bullet window"):
        t.on_closed_m1(bar(local.astimezone(UTC)))


def test_session_mapping_has_one_new_york_model_not_two_traders() -> None:
    assert set(SESSION_MODEL.values()) == {"LONDON", "NEW_YORK"}
    assert SESSION_MODEL[SessionId.NY_AM] == SESSION_MODEL[SessionId.NY_PM]
    src = (
        Path(__file__).resolve().parents[2]
        / "src/qore/infrastructure/traders/vt31_ict_cleanroom/trader.py"
    )
    syntax = ast.parse(src.read_text(encoding="utf-8"))
    for node in ast.walk(syntax):
        if isinstance(node, ast.ImportFrom):
            name = (node.module or "").lower()
            assert "vt31_nas100_" not in name
            assert "vt31_silver_bullet_" not in name
            assert "ttrades" not in name
