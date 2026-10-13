"""All synthetic fixtures: NO real BIS / QORE FX market prices in these tests."""
from __future__ import annotations

import csv
import io
import math
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from qore.research.alpha2_fx28_carry_one_test import CCYS, FX28
from qore.research.alpha2_fx28_policy_vol20_final import (
    DEV_END,
    GLOBAL_ANNUAL_VOL_TARGET,
    HISTORY_END_EXCLUSIVE,
    RETAINED_HOLDOUT_START,
    evaluate,
    official_rate_history,
    original_native_daily,
    realized_vol_pre_entry,
)
from qore.research.alpha2_intermarket import Bar
from qore.research.alpha2_tsmom_daily_weekly import Day


def synthetic_market(start=date(2023, 10, 1), stop=date(2026, 9, 17)):
    days={}
    d=start
    i=0
    while d<stop:
        if d.weekday()<5:
            days[d]=i
            i+=1
        d+=timedelta(days=1)
    result={}
    for k,symbol in enumerate(FX28):
        data={}
        for d,j in days.items():
            # not real currency prices. Deterministic volatile wave prior to entry.
            v=100 + 0.008*j*(1+0.03*k) + 0.15*math.sin(j*.6+k)
            data[d]=Day(d,v-.02,v,40)
        result[symbol]=data
    return result


def synthetic_rates(start=(2023, 9), end=(2026, 9)):
    y,m=start
    rates={c:{} for c in CCYS}
    while (y,m)<end:
        label=f"{y:04d}-{m:02d}"
        for i,c in enumerate(sorted(CCYS)):
            rates[c][label]=0.8+i*.7
        y,m=(y+1,1) if m==12 else (y,m+1)
    return rates


def test_pre_entry_fx_vol20_uses_only_previous_21_common_closes():
    data=synthetic_market(stop=date(2024, 5, 1))
    common=sorted(set.intersection(*(set(v) for v in data.values())))
    i=30
    original=realized_vol_pre_entry(data,common,i)
    day=common[i]
    for s in FX28:
        x=data[s][day]
        data[s][day]=Day(day,x.open*10,x.close*10,40)
    assert realized_vol_pre_entry(data,common,i)==pytest.approx(original)
    assert original>0
    assert GLOBAL_ANNUAL_VOL_TARGET==.10
    with pytest.raises(ValueError, match="PRIOR_21_SESSIONS"):
        realized_vol_pre_entry(data,common,20)


def test_full28_monthly_one_filter_and_paired_benchmark_costs():
    data=synthetic_market()
    rates=synthetic_rates()
    output=evaluate(rates,data)
    assert output["FX_pair_count"]==28
    assert output["FX_currency_count"]==8
    assert output["orders"]==0
    assert output["status"]=="POLICY_VOL20_INCONCLUSIVE_MISSING_HOLDOUT"  # no DEV source
    assert output["active_traded_months"]>20
    for r in output["month_contributions_hypothetical"]:
        scale=r["pre_entry_notional_risk_scale"]
        assert 0<scale<=1
        assert r["scaled_assumed_cost_2bps_each_side_bps"]==pytest.approx(4*scale)
        assert len(r["long6"])==len(r["short6"])==6
        assert not set(r["long6"])&set(r["short6"])
        assert r["filtered_gross_minus_assumed_cost_bps"]==pytest.approx(
            scale*r["unfiltered_assumed_cost_proxy_bps"]
        )
        assert r["paired_filtered_minus_pure_bps"]==pytest.approx(
            (scale-1)*r["unfiltered_assumed_cost_proxy_bps"]
        )
        assert abs(sum(r["currency_exposure_by_base_and_quote"].values()))<1e-9
        assert r["real_broker_NET_not_computed"] is True
    assert output["eras"]["DIAGNOSTIC"]["sample_gate"]
    assert output["eras"]["PREVIOUSLY_EMBARGOED_2024_2026"]["sample_gate"]
    assert all(date.fromisoformat(r["exit_day_UTC_reference_not_fill"])<
               HISTORY_END_EXCLUSIVE for r in output["month_contributions_hypothetical"])
    assert all(
        r["previously_embargoed_for_Alpha2"] ==
        (date.fromisoformat(r["entry_day_UTC_reference_not_fill"])>=RETAINED_HOLDOUT_START)
        for r in output["month_contributions_hypothetical"]
    )


def test_absent_one_currency_rate_censors_month_without_rank_substitution():
    data=synthetic_market()
    rates=synthetic_rates()
    for val in rates["CHF"]:
        if val>="2025-01":
            rates["CHF"][val]=None
            break
    # A missing value disqualifies the complete 28-pair month.
    result=evaluate(rates,data)
    assert result["censor_counts"]["EIGHT_POLICY_PRIOR_EOM_MISSING"]>=1


def test_original_native_m5_rolls_weekdays_only_and_respects_future_contract():
    start=datetime(2025,1,3,tzinfo=UTC)
    bars=[]
    for k in range(24):
        t=start+timedelta(minutes=5*k)
        bars.append(Bar(at=t,open=100,high=105,low=95,close=101))
    out,census=original_native_daily(iter(bars))
    assert len(out)==1 and out[0].native_m5_bars==24
    assert census["original_native_m5_pre_20260917_rows"]==24
    illegal=Bar(at=datetime(2026,9,17,tzinfo=UTC),
                open=100,high=101,low=99,close=100)
    with pytest.raises(ValueError,match="NEW_EMBARGO"):
        original_native_daily(iter([illegal]))


def test_bis_2026_months_only_with_explicit_authoritative_schema(tmp_path:Path):
    f=tmp_path/"bis_fake.zip"
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=[
        "FREQ:Frequency","REF_AREA:Reference area",
        "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value",
        "SOURCE_REF:Publication Source","COMPILATION:Compilation",
    ])
    writer.writeheader()
    for c in sorted(CCYS):
        area={"AUD":"AU","CAD":"CA","CHF":"CH","EUR":"XM",
              "GBP":"GB","JPY":"JP","NZD":"NZ","USD":"US"}[c]
        for m in ("2024-09","2025-01","2026-08"):
            writer.writerow({"FREQ:Frequency":"M: Monthly",
                "REF_AREA:Reference area":area+": synthetic",
                "TIME_PERIOD:Time period or range":m,
                "OBS_VALUE:Observation Value":2.5,
                "SOURCE_REF:Publication Source":"SYNTHETIC_ONLY",
                "COMPILATION:Compilation":"SYNTHETIC",
            })
    with zipfile.ZipFile(f,"w") as z:
        z.writestr("WS_CBPOL_csv_flat.csv",buffer.getvalue())
    vals,proof=official_rate_history(f)
    assert all("2026-08" in vals[c] for c in CCYS)
    assert proof["monthly_rates_not_published"] is True
    assert proof["authentic_vintages_not_verified"] is True
    assert len(proof["official_source_zip_sha256"])==64


def test_locked_boundary_and_expected_era_split():
    assert DEV_END==date(2022,1,1)
    assert RETAINED_HOLDOUT_START==date(2024,9,17)
    assert HISTORY_END_EXCLUSIVE==date(2026,9,17)
