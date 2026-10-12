"""G2 signed W3 opportunity timestamps vs source windows: no PnL or tick prices."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_w3_quote_window_coverage import (
    in_same_quote_window,
    inspect_events,
)

T = datetime(2023,9,19,13,5,tzinfo=UTC)
START = T-timedelta(minutes=5)
END = T+timedelta(hours=4)


def event(*, symbol="EURCHF",exit_at=None,paired=True,day="2023-09-19"):
    closed=exit_at or T+timedelta(minutes=4)
    arm={
        "status":"COMPLETE_GROSS_PROXY",
        "entry_utc":T.isoformat(),
        "exit_utc":closed.isoformat(),
        "gross_bps":-999999,
        "gross_R":-999999,
    }
    return {
        "symbol":symbol, "utc_day":day, "era":"DIAGNOSTIC",
        "paired":paired,
        "plan":{
            "decision_utc":START.isoformat(),
            "entry_utc":T.isoformat(),
            "exit_deadline_utc":END.isoformat(),
        },
        "strategy":dict(arm),
        "control":dict(arm),
    }


def test_one_evaluable_entry_and_both_exits_inside_10minute_original_source():
    x=inspect_events("EURCHF",[event()],has_source=True)
    assert x["counts"]=={
        "original_signals":1,
        "original_paired":1,
        "entry_in_quote_window":1,
        "strategy_entry_and_exit_same_window":1,
        "control_entry_and_exit_same_window":1,
        "both_arms_entry_and_exit_same_window":1,
    }
    assert x["executable_broker_net_paths"]==0
    assert x["by_era"]["DIAGNOSTIC"]["original_signals"]==1


def test_4h_expiry_cannot_use_10minute_bidask_snapshot_as_complete_path():
    x=inspect_events("EURCHF",[event(exit_at=T+timedelta(minutes=20))],
                     has_source=True)
    assert x["counts"]["entry_in_quote_window"]==1
    assert x["counts"]["both_arms_entry_and_exit_same_window"]==0


def test_missing_four_symbols_never_map_into_29_source_by_alias():
    x=inspect_events("NAS100",[event(symbol="NAS100")],
                     has_source=False)
    assert x["counts"]["original_signals"]==1
    assert x["counts"]["entry_in_quote_window"]==0
    assert x["data_source_classification"]=="OUTSIDE_29_SOURCE_SCOPE"


def test_both_arms_must_be_completed_before_a_paired_source_claim():
    x=event(paired=False)
    x["control"]={"status":"EXPIRY_OPEN_MISSING"}
    report=inspect_events("EURCHF",[x],has_source=True)
    assert report["counts"]["original_paired"]==0
    assert report["counts"]["control_entry_and_exit_same_window"]==0
    assert report["counts"]["strategy_entry_and_exit_same_window"]==1


def test_pair_status_invalid_claim_fails_closed():
    with pytest.raises(ValueError,match="paired status drift"):
        inspect_events("EURCHF",[event(paired=False)],has_source=True)


def test_post_embargo_path_rejected():
    e=event()
    e["plan"]["exit_deadline_utc"]=datetime(
        2026,9,17,tzinfo=UTC).isoformat()
    with pytest.raises(ValueError,match="holdout"):
        inspect_events("EURCHF",[e],has_source=True)


def test_duplicate_day_and_bad_market_fail_closed():
    with pytest.raises(ValueError,match="duplicate"):
        inspect_events("EURCHF",[event(),event()],has_source=True)
    with pytest.raises(ValueError,match="symbol"):
        inspect_events("EURCHF",[event(symbol="NAS100")],has_source=True)


def test_exact_end_boundary_is_not_inside_window():
    end=datetime(2023,9,19,13,10,tzinfo=UTC)
    assert in_same_quote_window(T,end,has_source=True)==(True,False)
    assert in_same_quote_window(end,end,has_source=True)==(False,False)
    assert in_same_quote_window(T,T,has_source=False)==(False,False)


def test_w3_mock_gross_loss_outcome_has_no_impact_on_source_coverage():
    a=event()
    b=event()
    b["strategy"]["gross_bps"]=999999
    b["strategy"]["gross_R"]=999999
    b["control"]["gross_R"]=999999
    assert inspect_events("EURCHF",[a],has_source=True)==inspect_events(
        "EURCHF",[b],has_source=True
    )
