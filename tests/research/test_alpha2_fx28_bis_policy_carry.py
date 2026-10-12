"""Synthetic adversarial tests only, no original BIS numbers or broker prices."""
from __future__ import annotations

import csv
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from qore.research.alpha2_fx28_bis_policy_carry import (
    BIS_CCY_AREA,
    bis_policy_rates,
    evaluate,
    previous_month,
)
from qore.research.alpha2_fx28_carry_one_test import FX28
from qore.research.alpha2_tsmom_daily_weekly import Day


def make_bis_zip(folder: Path, *, omitted: str | None = None) -> Path:
    output=folder/"BIS_SYNTHETIC_ONLY.zip"
    import io

    w=io.StringIO()
    c=csv.DictWriter(w,fieldnames=[
        "FREQ:Frequency","REF_AREA:Reference area",
        "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value",
        "SOURCE_REF:Publication Source","COMPILATION:Compilation",
    ])
    c.writeheader()
    for i,(currency,area) in enumerate(sorted(BIS_CCY_AREA.items())):
        if currency==omitted:
            continue
        for month in ("2018-01","2018-02","2021-12","2022-01"):
            c.writerow({
                "FREQ:Frequency":"M: Monthly",
                "REF_AREA:Reference area":area+": Fictional country",
                "TIME_PERIOD:Time period or range":month,
                "OBS_VALUE:Observation Value":1.2+i*.2,
                "SOURCE_REF:Publication Source":"SYNTHETIC_ONLY",
                "COMPILATION:Compilation":"SYNTHETIC_RATE_NOT_REAL",
            })
    with zipfile.ZipFile(output,"w") as z:
        z.writestr("WS_CBPOL_csv_flat.csv",w.getvalue())
    return output


def fake_days() -> dict[str, dict[date,Day]]:
    # February16 -> March15, 2018 and late 2022, no venue mapping.
    begin=date(2018,2,1)
    end=date(2022,3,17)
    all28={}
    for i,sym in enumerate(FX28):
        days={}
        d=begin
        while d<end:
            if d.weekday()<5 and (
                (d.year==2018 and d.month in (2,3))
                or (d.year==2022 and d.month in (1,2,3))
            ):
                value=100+i+d.day*.007
                days[d]=Day(d,value,value+.013,200)
            d+=timedelta(days=1)
        all28[sym]=days
    return all28


def test_frozen_eight_country_bis_area_and_previous_month_clock():
    assert BIS_CCY_AREA["EUR"]=="XM"
    assert set(BIS_CCY_AREA)=={"AUD","CAD","CHF","EUR","GBP","JPY","NZD","USD"}
    assert previous_month(2022,1)=="2021-12"
    assert previous_month(2018,2)=="2018-01"


def test_synthetic_bis_flat_ingest_8_m_and_no_source_rate_upload(tmp_path:Path):
    r,info=bis_policy_rates(make_bis_zip(tmp_path))
    assert len(r)==8
    assert all("2018-01" in months for months in r.values())
    assert info["rates_raw_not_published"]
    assert len(info["source_zip_sha256"])==64
    assert all(row["n_months"]==4 for row in info["coverage"].values())


def test_28_exact_reversal_rank_and_hypothetical_interest_vs_spot_are_distinct(tmp_path:Path):
    rates,_=bis_policy_rates(make_bis_zip(tmp_path))
    outcome=evaluate(rates,fake_days())
    assert outcome["candidate_months"]>=2
    assert len(outcome["28_fx_exact_roster"])==28
    assert outcome["account_NET_computed"] is False
    assert outcome["policy_accrual_is_hypothetical_NOT_realized_swap"]
    assert not outcome["UTC001_certified"]
    for e in outcome["weekly_monthly"]:
        assert len(e["long6"])==6 and len(e["short6"])==6
        assert not set(e["long6"])&set(e["short6"])
        assert e["entry_reference_utc_day"][8:10]>="16"
        assert e["assumed_2bps_each_side_portfolio_bps"]==4.0
        assert e["model_gross_proxy_bps"]==pytest.approx(
            e["spot_reference_bps"]+e["hypothetical_policy_accrual_bps"]
        )
        assert e["model_gross_minus_assumed_cost_bps"]==pytest.approx(
            e["model_gross_proxy_bps"]-4
        )
        assert sum(e["currency_net_exposures"].values())==pytest.approx(0.0)
    assert outcome["status"]=="POLICY28_UNDERPOWERED"


def test_missing_any_of_eight_policy_factors_rejects_entire_portfolio(tmp_path:Path):
    rates,_=bis_policy_rates(make_bis_zip(tmp_path,omitted="CHF"))
    out=evaluate(rates,fake_days())
    assert out["candidate_months"]==0
    assert out["status"]=="POLICY28_NOT_IDENTIFIABLE_MISSING_RATES_OR_PRICE"
    assert (
        "MISSING_PREVIOUS_MONTH_POLICY_RATE_ONE_OF_EIGHT"
        in out["censored_candidate_month_counts"]
    )


def test_missing_fx_pair_rejects_entire_all28_not_reweight(tmp_path:Path):
    rates,_=bis_policy_rates(make_bis_zip(tmp_path))
    days=fake_days()
    days.pop("AUDJPY")
    with pytest.raises(ValueError,match="EXACT28"):
        evaluate(rates,days)


def test_source_future_month_cannot_influence_2018_rank(tmp_path:Path):
    rates,_=bis_policy_rates(make_bis_zip(tmp_path))
    days=fake_days()
    first=evaluate(rates,days)
    rates["CHF"]["2022-01"]=20.0
    second=evaluate(rates,days)
    rowa=[x for x in first["weekly_monthly"] if x["calendar_month"]=="2018-02"][0]
    rowb=[x for x in second["weekly_monthly"] if x["calendar_month"]=="2018-02"][0]
    assert rowa["long6"]==rowb["long6"]
    assert rowa["short6"]==rowb["short6"]
