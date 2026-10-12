"""Cross-sectional reversal synthetic 33-way clock, no original price files."""
from datetime import date, timedelta

import pytest

from qore.research.alpha2_intermarket import MARKETS
from qore.research.alpha2_tsmom_daily_weekly import Day
from qore.research.alpha2_xsrev5_common_calendar import panel, replay


def fake_universe(n=35, *, drop_one=False, same_close=False):
    start=date(2020,1,1)
    dates=[]
    d=start
    while len(dates)<n:
        if d.weekday()<5:
            dates.append(d)
        d+=timedelta(days=1)
    out={}
    for k, sym in enumerate(MARKETS):
        rows=[]
        for i,day in enumerate(dates):
            if drop_one and sym=="XAGUSD" and i==12:
                continue
            close=(100.0 if same_close else 100+(.01+.001*k)*i)
            rows.append(Day(day,close+.07,close,35))
        out[sym]=rows
    return out


def test_always_all33_and_quintile7_each_side():
    r=replay(fake_universe())
    assert r["all33_common_eligible_days"]==35
    assert r["count_events"]>0
    for e in r["events"]:
        assert len(e["bottom7_long"])==7
        assert len(e["top7_short"])==7
        assert not set(e["bottom7_long"])&set(e["top7_short"])
        assert len(e["gross_by_selected_symbol_reference_bps"])==14
        assert e["assumed_1bp_each_side_total_bps"]==2.0
        assert e["gross_minus_assumed_cost_proxy_bps"]==pytest.approx(
            e["gross_reference_bps"]-2.0
        )
        assert e["broker_NET_not_proven"]


def test_all_equal_returns_lexical_tiebreak_is_stable():
    out=replay(fake_universe(same_close=True))
    assert out["events"]
    first=out["events"][0]
    names=sorted(MARKETS)
    assert first["bottom7_long"]==names[:7]
    assert first["top7_short"]==names[-7:]


def test_current_day_price_poisoning_cannot_change_preentry_ranking():
    originals=fake_universe()
    a=replay(originals)
    day=date.fromisoformat(a["events"][0]["reference_entry_day"])
    for s in MARKETS:
        n=[]
        for v in originals[s]:
            n.append(Day(v.utc_day,1,999999,35) if v.utc_day==day else v)
        originals[s]=n
    b=replay(originals)
    assert b["events"][0]["bottom7_long"]==a["events"][0]["bottom7_long"]
    assert b["events"][0]["top7_short"]==a["events"][0]["top7_short"]


def test_missing_single_market_day_drops_common_day_for_all33():
    a=replay(fake_universe())
    b=replay(fake_universe(drop_one=True))
    assert a["all33_common_eligible_days"]==35
    assert b["all33_common_eligible_days"]==34


def test_sealed_33_universe_and_empty_market_fail_closed():
    x=fake_universe()
    x.pop("NZDUSD")
    with pytest.raises(ValueError,match="NEEDS_EACH_OF_33"):
        replay(x)
    x=fake_universe()
    x["XAUUSD"]=[]
    with pytest.raises(ValueError,match="HAS_NO_DAYS"):
        replay(x)


def test_inconclusive_weekly_proxy_does_not_approve_broker_net():
    x=fake_universe()
    r=replay(x)
    data=panel(r,{s:len(v) for s,v in x.items()})
    assert data["status"]=="INCONCLUSIVE_UNDERPOWERED"
    assert data["original_selected_weeks"]>0
    assert data["all33_exact_original_sources"]==33
    assert data["UTC001_certified"] is False
    assert data["raw_market_daily_OHLC_published"] is False
    assert data["COST_HYPOTHESIS_ONLY_NOT_REAL_BROKER_NET"] is True
    assert data["orders"]==0


def test_short_history_never_creates_imputed_data():
    x=fake_universe(n=6)
    r=replay(x)
    assert r["count_events"]==0
    assert r["all33_common_eligible_days"]==6
