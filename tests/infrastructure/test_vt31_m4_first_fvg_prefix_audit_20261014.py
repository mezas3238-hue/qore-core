"""Frozen M4 128-event first-FVG causal-prefix forensic QA, source-only."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m4_first_fvg_prefix_audit_20261014 import prefix_parity
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)
from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
    first_fvg_and_source_path,
)

NY = ZoneInfo("America/New_York")


def _b(t, o="100", h="102", lo="98", c="101"):
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def _source(
    side: Side = Side.LONG, *,
    later: str = "NONE",
):
    s9 = datetime(2025, 7, 15, 9, tzinfo=NY).astimezone(UTC)
    s10 = datetime(2025, 7, 15, 10, tzinfo=NY).astimezone(UTC)
    nine = [_b(s9+timedelta(minutes=i)) for i in range(60)]
    if side is Side.LONG:
        nine[10] = _b(s9+timedelta(minutes=10), h="130")
        nine[20] = _b(s9+timedelta(minutes=20), lo="90")
        nine[57] = _b(s9+timedelta(minutes=57), h="104")
        ten = [
            _b(s10, c="100"),
            _b(s10+timedelta(minutes=1), "96", "99", "89", "95"),
            _b(s10+timedelta(minutes=2), "94", "106", "93", "105"),
            _b(s10+timedelta(minutes=3), "105", "108", "104", "107"),
            _b(s10+timedelta(minutes=4), "108", "112", "107", "111"),
        ]
        if later == "TOUCH":
            ten[4] = _b(ten[4].opened_at, "107", "110", "101", "108")
        if later == "AMBIGUOUS":
            ten[4] = _b(ten[4].opened_at, "107", "110", "96", "97")
    else:
        nine[10] = _b(s9+timedelta(minutes=10), h="110")
        nine[20] = _b(s9+timedelta(minutes=20), lo="70")
        nine[57] = _b(s9+timedelta(minutes=57), lo="96")
        ten = [
            _b(s10, c="100"),
            _b(s10+timedelta(minutes=1), "104", "111", "103", "105"),
            _b(s10+timedelta(minutes=2), "106", "107", "94", "95"),
            _b(s10+timedelta(minutes=3), "95", "96", "91", "92"),
            _b(s10+timedelta(minutes=4), "91", "93", "88", "90"),
        ]
    nine, ten = tuple(nine), tuple(ten)
    cog = propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=nine + ten[:3],
    )
    assert cog.decision is not None, cog.record()
    return nine, ten, cog.decision


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_exact_first_fvg_c3_ce_c2_persist_over_all_closed_prefixes(side):
    nine, ten, cog = _source(side)
    result = prefix_parity(nine=nine, ten=ten, cognition=cog)
    assert result["prefixes_checked"] == 3
    assert result["first_fvg_at"] == ten[3].closed_at.isoformat()
    assert result["final_m4_state"] == "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE"
    assert result["causal_first_fvg_and_C2_immutable"]
    assert result["source_ohlc_touch_not_broker_fill"]


@pytest.mark.parametrize("later,path", [
    ("TOUCH", "TOUCH_NOT_FILL"),
    ("AMBIGUOUS", "AMBIGUOUS_M1_SEQUENCE_NO_FILL"),
])
def test_final_first_M5_terminal_event_never_uses_early_future(later, path):
    nine, ten, cog = _source(later=later)
    result = prefix_parity(nine=nine, ten=ten, cognition=cog)
    assert result["final_m5_source_path"] == path
    assert result["earliest_terminal_path"]["state"] == path
    assert result["earliest_terminal_path"]["time"] == ten[-1].closed_at.isoformat()


def test_no_eligible_fvg_not_misreported_as_entry():
    nine, ten, cog = _source()
    early = ten[:3]
    result = prefix_parity(nine=nine, ten=early, cognition=cog)
    assert result["first_fvg_at"] is None
    assert result["final_m4_state"] == "NO_ELIGIBLE_FVG"
    assert result["earliest_terminal_path"] is None


def test_original_first_C3_not_selected_before_its_close():
    nine, ten, cog = _source()
    before = first_fvg_and_source_path(
        nine=nine, ten=ten[:3], cognition=cog,
    )
    after = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=cog,
    )
    assert before.first_fvg_confirmed_at is None
    assert after.first_fvg_confirmed_at == ten[3].closed_at
    assert not after.filled and not after.execution_authorized


def test_audit_never_calls_broker_order_or_sizing():
    from inspect import getsource
    from scripts import vt31_m4_first_fvg_prefix_audit_20261014 as mod

    body = getsource(mod.prefix_parity) + getsource(mod.audit_groups)
    assert "order_send" not in body
    assert "ProtoOANewOrderReq" not in body
    assert "lot_size" not in body
    assert "take_profit" not in body
    assert "first_fvg_and_source_path" in body
