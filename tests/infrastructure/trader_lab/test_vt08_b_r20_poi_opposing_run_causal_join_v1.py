"""B R20 adversarial physical POI-to-opposing-M3-run causal test cases."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_b_r20_poi_opposing_run_causal_join_v1 import (
    M3,
    classify_physical_poi_into_series,
)

START = datetime(2026, 1, 5, 12, tzinfo=UTC)
BARS = [
    ("104", "106", "103", "105"),
    ("105", "105", "102", "103"),
    ("103", "104", "97", "100"),
    ("100", "101", "95", "96"),
    ("96", "108", "96", "107"),
    ("110", "114", "110", "113"),
    ("113", "114", "112", "113"),
    ("113", "114", "112", "113"),
    ("113", "114", "112", "113"),
    ("113", "114", "112", "113"),
]


def bars() -> list[tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal], str]]:
    return [
        (
            START+i*M3,
            tuple(Decimal(x) for x in price),
            hashlib.sha256(str(i).encode()).hexdigest(),
        )
        for i, price in enumerate(BARS)
    ]


def make_zone(
    source: list, *, low: str, high: str,
) -> dict[str, object]:
    minimum, maximum = Decimal(low), Decimal(high)
    matched = [
        x for x in source
        if x[1][2] <= maximum and x[1][1] >= minimum
    ]
    first = matched[0] if matched else None
    cisd = START+5*M3
    if first is None:
        phase = "NOT_TOUCHED_DURING_C2"
    elif first[0]+M3 < cisd:
        phase = "TOUCHED_BEFORE_CISD_BAR"
    elif first[0]+M3 == cisd:
        phase = "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"
    else:
        phase = "TOUCHED_AFTER_CISD_CLOSE"
    return {
        "type": "BULLISH_H1_3BAR_FVG_GEOMETRY",
        "lower": low, "upper": high,
        "first_touch_phase": phase,
        "first_touch_bar_opened_at_utc": first[0].isoformat() if first else None,
        "first_touch_m3_source_bar_id": first[2] if first else None,
    }


def evaluate(source, zone):
    return classify_physical_poi_into_series(
        zone, verified_bars=source, series_open=START+M3,
        cisd_close=START+5*M3, c1_low=Decimal("99"),
    )


def test_first_touch_during_actual_bearish_run_and_sweep_both_in_same_m3() -> None:
    source=bars()
    result=evaluate(source,make_zone(source,low="96",high="99"))
    assert result["physical_first_touch_relative_to_run"] == "WITHIN_BEARISH_OPPOSING_SERIES"
    assert result["bearish_series_touched_fvg"] is True
    assert result["bearish_series_swept_c1_low"] is True
    assert result["same_bar_fvg_touch_and_liquidity_sweep"] is True
    assert result["author_poi_significance_certified"] is False


def test_first_touch_before_opposing_bearish_series_is_not_during() -> None:
    source=bars()
    when, (op,hi,_,cl), bid=source[0]
    source[0]=(when,(op,hi,Decimal("98"),cl),bid)
    r=evaluate(source,make_zone(source,low="96",high="99"))
    assert r["physical_first_touch_relative_to_run"] == "BEFORE_BEARISH_OPPOSING_SERIES"
    assert r["bearish_series_touched_fvg"] is True


def test_first_touch_in_cisd_bar_not_prior() -> None:
    source=bars()
    result=evaluate(source,make_zone(source,low="106.5",high="107.5"))
    assert result["physical_first_touch_relative_to_run"] == "IN_CISD_CONFIRMATION_BAR_INTRABAR_UNKNOWN"
    assert result["bearish_series_touched_fvg"] is False


def test_first_touch_after_cisd_cannot_confirm_poi() -> None:
    source=bars()
    result=evaluate(source,make_zone(source,low="111",high="111.5"))
    assert result["physical_first_touch_relative_to_run"] == "AFTER_CISD_CLOSE"
    assert result["bearish_series_touched_fvg"] is False


def test_original_zone_no_touch_does_not_invent_event() -> None:
    source=bars()
    result=evaluate(source,make_zone(source,low="120",high="121"))
    assert result["physical_first_touch_relative_to_run"] == "NOT_TOUCHED_DURING_C2"
    assert result["bearish_series_touched_fvg"] is False


def test_no_h1_fvg_cannot_promote_source() -> None:
    result=evaluate(bars(),None)
    assert result["physical_first_touch_relative_to_run"]=="NO_H1_THREE_BAR_FVG"
    assert result["author_poi_significance_certified"] is False


def test_forged_first_touch_raw_bar_id_rejected() -> None:
    source=bars()
    zone=make_zone(source,low="96",high="99")
    zone["first_touch_m3_source_bar_id"]="f"*64
    with pytest.raises(ValueError,match="disagrees"):
        evaluate(source,zone)


def test_forged_first_touch_phase_rejected() -> None:
    source=bars()
    zone=make_zone(source,low="96",high="99")
    zone["first_touch_phase"]="TOUCHED_AFTER_CISD_CLOSE"
    with pytest.raises(ValueError,match="classification disagrees"):
        evaluate(source,zone)


def test_forged_first_touch_timestamp_rejected() -> None:
    source=bars()
    zone=make_zone(source,low="96",high="99")
    zone["first_touch_bar_opened_at_utc"]=(START+6*M3).isoformat()
    with pytest.raises(ValueError,match="disagrees"):
        evaluate(source,zone)


def test_missing_native_m3_bar_rejected() -> None:
    source=bars()
    source.pop(2)
    with pytest.raises(ValueError,match="discontinuous"):
        evaluate(source,None)


def test_fake_bearish_series_must_be_all_down_closes() -> None:
    source=bars()
    when,(op,high,low,_),bid=source[2]
    source[2]=(when,(op,high,low,op),bid)
    zone=make_zone(source,low="96",high="99")
    with pytest.raises(ValueError,match="not down-closes"):
        evaluate(source,zone)


def test_empty_source_rejected() -> None:
    with pytest.raises(ValueError,match="missing physical"):
        evaluate([],None)


def test_inverted_price_zone_rejected() -> None:
    source=bars()
    zone=make_zone(source,low="96",high="99")
    zone["lower"]="101"
    zone["upper"]="100"
    with pytest.raises(ValueError,match="price zone"):
        evaluate(source,zone)


def test_series_origin_outside_bars_rejected() -> None:
    with pytest.raises(ValueError,match="outside native"):
        classify_physical_poi_into_series(
            None, verified_bars=bars(),
            series_open=START-timedelta(minutes=3),
            cisd_close=START+5*M3, c1_low=Decimal("99"),
        )
