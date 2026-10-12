"""E2 all 231 outcomes: Holm, common weeks, no cherry-picking."""
from __future__ import annotations

from pathlib import Path
import pytest

from qore.infrastructure.trader_lab import qore_native_e2_33x7_holm_synchronized_weeks_v1 as m


def empty() -> dict[str,list[dict]]:
    return {symbol:[
        {"method_id":method,"paired_events":[]}
        for method in m.METHODS
    ] for symbol in m.SYMBOLS}


def test_all_231_even_with_zero_trades_nulls_are_not_excluded() -> None:
    d=m.analyze_period(empty(),"development")
    assert len(d["cells"])==231
    assert d["comparison_count_Holm"]==231
    assert d["n_no_event"]==231
    assert d["n_sample_gate_pass"]==0
    assert all(c["delta_bootstrap_p_two_sided_exploratory"]==1.0 for c in d["cells"])
    assert all(c["net_broker_certification"] is False for c in d["cells"])


def test_holm_correction_all_comparisons_including_dependencies() -> None:
    p=[0.001,0.02,0.2,0.02,1.0]
    z=m.holm_adjusted(p)
    assert len(z)==len(p)
    assert z[0]==pytest.approx(0.005)
    assert z[1]==pytest.approx(0.08)
    assert z[3]==pytest.approx(0.08)
    assert z[2]==pytest.approx(0.4)
    assert z[4]==pytest.approx(1.0)


def test_single_candidate_cannot_pass_with_few_calendar_weeks() -> None:
    r=empty()
    cell=r["EURUSD"][0]
    for i in range(5):
        cell["paired_events"].append({
            "reference_entry_utc":f"2020-01-{i+6:02d}T16:00:00+00:00",
            "iso_week":f"2020-W0{i+2}",
            "strategy_gross_bps":2.0,
            "baseline_gross_bps":-1.0,
            "paired_delta_bps":3.0,
        })
    p=m.analyze_period(r,"development")
    match=next(c for c in p["cells"] if c["cell_id"]=="REVERSAL_12H__EURUSD")
    assert match["n_paired_days"]==5
    assert match["sample_gate"] is False
    assert match["p_Holm_FWER_231_exploratory"]==1.0


def test_missing_source_witnesses_fail_closed(tmp_path:Path) ->None:
    with pytest.raises(ValueError,match="exactly 33"):
        m.load_signed_observations(tmp_path)


def test_methods_order_frozen_and_same_for_all_assets() ->None:
    assert len(m.METHODS)==7 and len(m.SYMBOLS)==33
    assert len(m.CELLS)==231
    assert len(set(m.CELLS))==231
    assert m.B==20000 and m.SEED==20261012
    assert m.MIN["development"]==(150,52)
    assert m.MIN["temporal_diagnostic"]==(50,26)


def test_no_original_market_source_prices_or_live_orders_read_in_aggregator() ->None:
    content=Path(m.__file__).read_text(encoding="utf-8")
    for unsafe in ('row["close_relative"]','row["open_relative"]',
                   "place_order(","ctrader_open_api_client","ProtoOANewOrderReq"):
        assert unsafe not in content
