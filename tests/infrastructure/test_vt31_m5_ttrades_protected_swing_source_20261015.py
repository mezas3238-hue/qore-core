"""TTrades protected swing SOURCE witness (not executable stop / certification)."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from scripts.vt31_m5_ttrades_protected_swing_source_20261015 import (
    make_fixture,
    qualitative_protected_swing_court,
    source_protected_swing,
)


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("month,offset", [(1, "-05:00"), (7, "-04:00")])
def test_actual_source_series_close_confirms_protected_swing_no_broker_sl(
    side, month, offset,
):
    nine, ten, series = make_fixture(side=side, month=month)
    checked = source_protected_swing(
        side=side, nine=nine, ten=ten, opposing_series=series,
        as_of=ten[-1].closed_at,
    )
    assert checked.status == "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED"
    assert checked.protected_source_extreme == Decimal(
        "89" if side == "LONG" else "111"
    )
    assert checked.second_return_m1_wick_proxy == Decimal(
        "93" if side == "LONG" else "109"
    )
    assert checked.protected_source_extreme != checked.second_return_m1_wick_proxy
    assert checked.confirmed_at == ten[-1].closed_at
    assert checked.first_raid_at == ten[1].closed_at
    assert checked.record()["as_of_ny"].endswith(offset)
    assert checked.displacement_causing_swing_author_final_identified is False
    assert checked.framework_g3_c2_is_not_proven_same_swing is True
    assert checked.broker_stop_tick_price_certified is False
    assert checked.method_certified is False
    assert checked.cognition_certified is False


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_closing_beyond_opposing_series_is_required_not_a_wick_only(side):
    nine, ten, series = make_fixture(side=side, month=1)
    # Confirmation wick unchanged, only close changes to an unconfirmed body.
    x = replace(ten[-1], close=Decimal("95" if side == "LONG" else "105"))
    checked = source_protected_swing(
        side=side, nine=nine, ten=ten[:-1]+(x,),
        opposing_series=series, as_of=ten[-1].closed_at,
    )
    assert checked.status == "PROTECTED_SWING_NOT_CONFIRMED_WAIT"
    assert checked.protected_source_extreme is None
    assert checked.confirmed_at is None


def test_no_opposing_series_or_wrong_candle_color_cannot_certify():
    nine, ten, series = make_fixture(side="LONG", month=1)
    no_series = source_protected_swing(
        side="LONG", nine=nine, ten=ten, opposing_series=(),
        as_of=ten[-1].closed_at,
    )
    assert no_series.status == "PROTECTED_SWING_NOT_CONFIRMED_WAIT"
    wrong = replace(series[1], open=Decimal("94"), close=Decimal("95"))
    wrong_series = source_protected_swing(
        side="LONG", nine=nine, ten=ten,
        opposing_series=(series[0], wrong),
        as_of=ten[-1].closed_at,
    )
    assert wrong_series.status == "SOURCE_INPUT_REJECTED" or (
        wrong_series.status == "PROTECTED_SWING_NOT_CONFIRMED_WAIT"
    )


def test_missing_h1_source_does_not_mint_swing():
    nine, ten, series = make_fixture(side="SHORT", month=1)
    bad = source_protected_swing(
        side="SHORT", nine=nine[:-1], ten=ten,
        opposing_series=series, as_of=ten[-1].closed_at,
    )
    assert bad.status == "SOURCE_CONTEXT_UNKNOWN"


def test_same_m1_sweeps_both_h1_sides_is_intrabar_unknown():
    nine, ten, series = make_fixture(side="LONG", month=7)
    dual = replace(ten[1], high=Decimal("111"))
    checked = source_protected_swing(
        side="LONG", nine=nine, ten=ten[:1] + (dual,) + ten[2:],
        opposing_series=series, as_of=ten[-1].closed_at,
    )
    assert checked.status == "SOURCE_CONTEXT_UNKNOWN"
    assert "BOTH_H1_SIDES_SAME_M1_UNKNOWN_INTRABAR" in checked.reasons


def test_future_closed_m1_cannot_certify_old_asof():
    nine, ten, series = make_fixture(side="LONG", month=1)
    checked = source_protected_swing(
        side="LONG", nine=nine, ten=ten,
        opposing_series=series, as_of=ten[-1].closed_at-timedelta(minutes=1),
    )
    assert checked.status == "SOURCE_INPUT_REJECTED"
    assert checked.protected_source_extreme is None


def test_pending_context_without_displacement_m1_is_wait_not_backfilled():
    nine, ten, series = make_fixture(side="LONG", month=7)
    checked = source_protected_swing(
        side="LONG", nine=nine, ten=ten[:3],
        opposing_series=series, as_of=ten[2].closed_at,
    )
    assert checked.status == "PROTECTED_SWING_NOT_CONFIRMED_WAIT"


def test_full_court_only_establishes_4_source_witnesses_4_justified_wait():
    report = qualitative_protected_swing_court()
    assert len(report["cases"]) == 8
    assert sum(
        c["status"] == "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED"
        for c in report["cases"]
    ) == 4
    assert sum(
        c["status"] == "PROTECTED_SWING_NOT_CONFIRMED_WAIT"
        for c in report["cases"]
    ) == 4
    assert report["author_full_displacement_causing_swing_identified"] is False
    assert report["g3_c2_stop_equivalence_claimed"] is False
    assert report["human_method_review_completed"] is False
    assert report["methodology_certified"] is False
    assert report["cognition_certified"] is False
    assert report["pnl_or_return_evidence"] is None
    assert report["broker_orders"] == report["lot_sizing"] == 0
    assert report["live_authorized"] is False
