"""M30→native-M3 execution geometry, temporal evidence and no hypothetical fills."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    analyze_setup,
    closed_source_window,
    earliest_clean_touch_per_market_day,
    eligible_owner_m30,
    gross_geometry,
    median_decimals,
    retest_entry_opportunity,
    same_ohlc,
    source_m30_reversal,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T = datetime(2026, 1, 14, 9, 0, tzinfo=UTC)
LONG = DemoTradingSetupSide.LONG


def candle(t, op, hi, lo, cl, minutes=3):
    return Vt08B01Bar(
        opened_at=t, closed_at=t+timedelta(minutes=minutes),
        open=Decimal(str(op)), high=Decimal(str(hi)),
        low=Decimal(str(lo)), close=Decimal(str(cl)),
    )


def fixture():
    t1 = T - timedelta(minutes=30)
    c1bars = [
        candle(t1 + timedelta(minutes=3*i), 100, 101, 99, 100)
        for i in range(10)
    ]
    c1bars[0] = candle(t1, 100, 110, 95, 100)
    t2 = T
    c2bars = [
        candle(t2 + timedelta(minutes=3*i), 104, 105, 103, 104)
        for i in range(10)
    ]
    c2bars[0] = candle(t2, 100, 101, 94, 96)
    c2bars[1] = candle(t2 + timedelta(minutes=3), 96, 105, 96, 104)
    c1 = aggregate(tuple(c1bars), period_minutes=30, member_minutes=3)
    c2 = aggregate(tuple(c2bars), period_minutes=30, member_minutes=3)
    t3 = c2.closed_at
    future = [
        candle(t3 + timedelta(minutes=3*i), 102, 103, 100, 101)
        for i in range(10)
    ]
    future[0] = candle(t3, 104, 105, 101, 101)
    future[1] = candle(t3+timedelta(minutes=3), 101, 103, 98, 100)
    return c1, c2, tuple(c2bars), tuple(future)


def test_m30_c2_single_sweep_and_m3_cisd_preconfirmed():
    c1,c2,ltf,future=fixture()
    assert source_m30_reversal(c1,c2) is LONG
    output=analyze_setup(
        market="EURJPY", c1=c1, c2=c2, c2_m3=ltf,
        c3_first_m3=future[0], c3_m3=future,
    )
    assert output["status"]=="M30_M3_SOURCE_GEOMETRY_ONLY"
    assert output["c2_m3_cisd_confirmed_at"] < output["c2_closed_at"]
    assert output["entry_positional_proposed_at"]==output["c2_closed_at"]
    assert output["entry_positional_open"]=="104"
    assert output["c2_m3_ps_price"]=="94"
    assert output["c2_m3_cisd_retest_level"]=="100"
    assert output["retest"]["status"]=="CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL"
    assert output["retest"]["observed_after_close"] > output["entry_positional_proposed_at"]
    retest_risk = Decimal(output["retest"]["gross_geometry"]["risk"])
    positional_risk = Decimal(output["positional"]["risk"])
    assert retest_risk < positional_risk
    assert output["orders_authorized"] is False


def test_risk_geometric_filter_is_causal():
    def geometry(price: str):
        return gross_geometry(
            side=LONG, entry=Decimal(price),
            stop=Decimal("94"), target=Decimal("110"),
        )

    assert geometry("104")["rr"] == "0.6"
    assert geometry("93") is None
    assert geometry("114") is None


def test_retest_in_same_m3_as_stop_cannot_be_asserted_clean():
    _,c2,_,c3=fixture()
    bad = list(c3)
    bad[1]=candle(c2.closed_at+timedelta(minutes=3), 101, 103, 93, 100)
    result=retest_entry_opportunity(
        side=LONG, first_open=Decimal("104"),
        stop=Decimal("94"), target=Decimal("110"),
        cisd_retest_level=Decimal("100"), following_m3=tuple(bad),at=c2.closed_at,
    )
    assert result["status"]=="SAME_BAR_ORDER_SEQUENCE_AMBIGUOUS"


def test_retest_after_target_was_already_reached_is_invalid():
    _,c2,_,c3=fixture()
    bad = list(c3)
    bad[0]=candle(c2.closed_at, 104, 111, 103, 109)
    result=retest_entry_opportunity(
        side=LONG, first_open=Decimal("104"),
        stop=Decimal("94"), target=Decimal("110"),
        cisd_retest_level=Decimal("100"), following_m3=tuple(bad),at=c2.closed_at,
    )
    assert result["status"]=="TARGET_REACHED_BEFORE_RETEST"


def test_no_favorable_limit_when_cisd_level_beyond_initial_price():
    _,c2,_,c3=fixture()
    result=retest_entry_opportunity(
        side=LONG, first_open=Decimal("104"),
        stop=Decimal("94"), target=Decimal("110"),
        cisd_retest_level=Decimal("106"), following_m3=c3,at=c2.closed_at,
    )
    assert result["status"]=="NO_FAVORABLE_PREDECLARED_CISD_LEVEL"


def test_source_m3_missing_or_unclosed_fails_30m():
    c1,_,ltf,_=fixture()
    assert c1.high==Decimal("110")
    with pytest.raises(ValueError,match="incomplete source aggregate"):
        aggregate(ltf[:-1],period_minutes=30,member_minutes=3)
    shifted=list(ltf)
    shifted[1]=candle(ltf[1].opened_at+timedelta(minutes=3),96,105,96,104)
    with pytest.raises(ValueError,match="missing/overlapping"):
        aggregate(tuple(shifted),period_minutes=30,member_minutes=3)


def test_cross_timeframe_m30_source_provenance_and_tampering():
    c1,_,ltf,_=fixture()
    source={x.opened_at:x for x in ltf}
    actual=closed_source_window(source,begin=ltf[0].opened_at,count=10,minutes=3)
    assert actual is not None
    left = aggregate(actual, period_minutes=30, member_minutes=3)
    right = aggregate(ltf, period_minutes=30, member_minutes=3)
    assert same_ohlc(left, right)
    altered=candle(c1.opened_at,c1.open,c1.high+Decimal("1"),c1.low,c1.close,30)
    assert not same_ohlc(c1,altered)


def test_c2_two_sided_sweep_rejected():
    c1,c2,_,_=fixture()
    both=candle(c2.opened_at,c2.open,111,94,c2.close,30)
    assert source_m30_reversal(c1,both) is None


def test_new_york_clock_owner_windows_no_13ny():
    from zoneinfo import ZoneInfo
    ny=ZoneInfo("America/New_York")
    for month in (1,7):
        for hour in (1,4,5,8,9,12):
            x=datetime(2026,month,14,hour,30,tzinfo=ny)
            assert eligible_owner_m30(x)
        assert not eligible_owner_m30(datetime(2026,month,14,13,0,tzinfo=ny))


def test_c3_m3_later_data_cannot_be_bought_at_c3_open():
    _,c2,_,c3=fixture()
    retest=retest_entry_opportunity(
        side=LONG,first_open=Decimal("104"),stop=Decimal("94"),
        target=Decimal("110"),cisd_retest_level=Decimal("100"),
        following_m3=c3,at=c2.closed_at,
    )
    assert retest["status"]=="CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL"
    assert datetime.fromisoformat(retest["observed_after_close"])>c2.closed_at


def test_one_event_per_ny_day_is_first_closed_touch_not_best_rr() -> None:
    t = datetime(2026, 1, 14, 14, 0, tzinfo=UTC)

    def receipt(origin: str, at_minutes: int, retest_rr: str):
        return {
            "origin_id": origin,
            "market_ny_date": "2026-01-14",
            "entry_positional_proposed_at": t.isoformat(),
            "positional": {"risk": "10", "rr": "0.6"},
            "retest": {
                "status": "CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL",
                "observed_after_close": (
                    t + timedelta(minutes=at_minutes)
                ).isoformat(),
                "gross_geometry": {"risk": "5", "rr": retest_rr},
            },
        }

    first = receipt("event-lower-rr", 3, "1.1")
    later = receipt("event-higher-rr", 6, "3.8")
    selected = earliest_clean_touch_per_market_day([later, first])
    assert len(selected) == 1
    assert selected[0]["origin_id"] == "event-lower-rr"
    assert selected[0]["risk_reduction_percent_gross"] == "50.0"
    assert selected[0]["trade_authorized"] is False


def test_absent_retest_does_not_promote_or_count_as_order() -> None:
    record = {
        "origin_id": "unfilled",
        "market_ny_date": "2026-01-14",
        "entry_positional_proposed_at": T.isoformat(),
        "positional": {"risk": "10", "rr": "1.0"},
        "retest": {"status": "NO_CISD_LEVEL_RETEST_IN_C3"},
    }
    assert earliest_clean_touch_per_market_day([record]) == []
    assert median_decimals([]) is None
    assert median_decimals([Decimal("2"), Decimal("4")]) == "3"
