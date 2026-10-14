"""Author stop swing vs QORE C2 proxy: no trade/author certification tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_l1_m5_stop_source_conflict_20261014 import (
    classify_c2_against_extreme,
    observe_stop_conflict,
)
from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
    first_fvg_and_source_path,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")


def bar(
    t, o="100", h="102", l="98", c="101",
):
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(l), Decimal(c),
    )


def fixture(side=Side.LONG, month=7, c2_level=None):
    start9 = datetime(2025, month, 15, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, 15, 10, tzinfo=NY).astimezone(UTC)
    nine = [bar(start9 + timedelta(minutes=i)) for i in range(60)]
    if side is Side.LONG:
        nine[10] = bar(nine[10].opened_at, h="130")
        nine[20] = bar(nine[20].opened_at, l="90")
        nine[57] = bar(nine[57].opened_at, h="104")
        lvl = str(c2_level) if c2_level is not None else "93"
        ten = (
            bar(start10, c="100"),
            bar(start10 + timedelta(minutes=1), "96", "99", "89", "95"),
            bar(start10 + timedelta(minutes=2), "94", "106", lvl, "105"),
            bar(start10 + timedelta(minutes=3), "105", "108", "104", "107"),
        )
    else:
        nine[10] = bar(nine[10].opened_at, h="110")
        nine[20] = bar(nine[20].opened_at, l="70")
        nine[57] = bar(nine[57].opened_at, l="96")
        lvl = str(c2_level) if c2_level is not None else "107"
        ten = (
            bar(start10, c="100"),
            bar(start10 + timedelta(minutes=1), "104", "111", "103", "105"),
            bar(start10 + timedelta(minutes=2), "106", lvl, "94", "95"),
            bar(start10 + timedelta(minutes=3), "95", "96", "91", "92"),
        )
    nine = tuple(nine)
    response = propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=nine + ten[:3],
    )
    assert response.decision is not None, response.record()
    witness = first_fvg_and_source_path(
        nine=nine, ten=ten, cognition=response.decision,
    )
    assert witness.state == "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE", witness
    return nine, ten, witness.record()


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("month", [1, 7])
def test_both_sides_dst_and_observed_inside_reference_not_author_stop(side, month):
    nine, ten, m4 = fixture(side, month)
    report = observe_stop_conflict(nine=nine, ten=ten, m4=m4)
    assert report["c2_vs_pre_mss_extreme"] == "C2_INSIDE_PRE_MSS_EXTREME"
    assert report["c2_vs_raid_extreme"] == "C2_INSIDE_FIRST_RAID_EXTREME"
    assert report["c2_ce_geometry"] == "C2_REFERENCE_ON_RISK_SIDE_OF_CE"
    assert report["author_swing_identified"] is False
    assert report["ttrades_author_stop_certified"] is False
    assert report["g3_c2_equals_author_stop"] is False
    assert report["executable_stop_produced"] is False
    assert report["filled"] is False
    assert report["c2_to_first_raid_extreme_abs_points"] == "4"


@pytest.mark.parametrize("side,match,outside", [
    (Side.LONG, "89", "88"),
    (Side.SHORT, "111", "112"),
])
def test_c2_can_match_or_extend_beyond_first_raid_not_prove_author_swing(
    side, match, outside,
):
    for value, name in ((match, "MATCHES"), (outside, "OUTSIDE")):
        nine, ten, m4 = fixture(side=side, c2_level=value)
        result = observe_stop_conflict(nine=nine, ten=ten, m4=m4)
        assert result["c2_vs_pre_mss_extreme"] == (
            f"C2_{name}_PRE_MSS_EXTREME"
        )
        assert result["ttrades_author_stop_certified"] is False


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_classification_edge_cases_and_wrong_side(side):
    original = Decimal("100")
    if side == "LONG":
        assert classify_c2_against_extreme(
            side=side, c2=original + 1, extreme=original,
        ).startswith("C2_INSIDE")
        assert classify_c2_against_extreme(
            side=side, c2=original - 1, extreme=original,
        ).startswith("C2_OUTSIDE")
    else:
        assert classify_c2_against_extreme(
            side=side, c2=original - 1, extreme=original,
        ).startswith("C2_INSIDE")
        assert classify_c2_against_extreme(
            side=side, c2=original + 1, extreme=original,
        ).startswith("C2_OUTSIDE")
    with pytest.raises(ValueError, match="COG_SIDE"):
        classify_c2_against_extreme(
            side="WRONG", c2=original, extreme=original,
        )


def test_missing_correct_c3_close_blocks_future_candle_use():
    nine, ten, m4 = fixture()
    later = bar(ten[-1].closed_at, "107", "110", "100", "108")
    with pytest.raises(ValueError, match="LOOKAHEAD_OR_STALE"):
        observe_stop_conflict(nine=nine, ten=ten + (later,), m4=m4)


def test_corrupted_c2_price_fails_and_does_not_rewrite_stop():
    nine, ten, m4 = fixture()
    bad = {**m4, "c2_full_wick_reference": "89"}
    with pytest.raises(ValueError, match="C2_MUST_EQUAL"):
        observe_stop_conflict(nine=nine, ten=ten, m4=bad)


def test_corrupted_fvg_geometry_rejected_before_comparison():
    nine, ten, m4 = fixture()
    bad = {**m4, "fvg_lower": "50"}
    with pytest.raises(ValueError, match="ORIGINAL_M4_FVG"):
        observe_stop_conflict(nine=nine, ten=ten, m4=bad)


def test_disagreeing_H1_target_or_side_never_certifies_stop():
    nine, ten, m4 = fixture()
    for item in (
        {**m4, "target_dol": "200"},
        {**m4, "side": "SHORT"},
    ):
        with pytest.raises(ValueError):
            observe_stop_conflict(nine=nine, ten=ten, m4=item)


def test_mss_anchor_mutated_rejected():
    nine, ten, m4 = fixture()
    with pytest.raises(ValueError, match="MSS_ANCHOR"):
        observe_stop_conflict(
            nine=nine, ten=ten, m4={**m4, "mss_anchor": "700"},
        )


def test_mss_timestamp_mutated_rejected():
    nine, ten, m4 = fixture()
    mutated = {
        **m4, "cognitive_mss_at": ten[1].closed_at.isoformat(),
    }
    with pytest.raises(ValueError, match="MSS_NOT_AFTER|FIRST_RETURN"):
        observe_stop_conflict(nine=nine, ten=ten, m4=mutated)


def test_source_H1_missing_hour_rejected():
    nine, ten, m4 = fixture()
    with pytest.raises(ValueError, match="H1_09_SOURCE_INCOMPLETE"):
        observe_stop_conflict(nine=nine[:59], ten=ten, m4=m4)


def test_source_not_formed_rejected():
    nine, ten, m4 = fixture()
    with pytest.raises(ValueError, match="NO_FVG"):
        observe_stop_conflict(
            nine=nine, ten=ten,
            m4={**m4, "state": "NO_ELIGIBLE_FVG"},
        )
