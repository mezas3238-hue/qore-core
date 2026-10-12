"""Posthoc E2 231 gross outcomes minus ONE user's spot spread: no net inference."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_e2_231_one_spot_spread_stress_v1 as s

SNAP=Path(__file__).resolve().parents[3]/"docs/research/data/QORE_NATIVE_USER_BIDASK_SCREENSHOTS_33_SPOT_TRANSCRIPTION_2026-10-12.json"


def inputs(gross:float=100)->tuple[dict,dict]:
    cells=[]
    for key in s.parent.CELLS:
        method,symbol=key.split("__",1)
        cells.append({
            "cell_id":key, "method_id":method,"symbol":symbol,
            "gross_mean_bps":gross,"control_gross_mean_bps":1.0,
            "paired_delta_mean_bps":gross-1.0,"net_broker_certification":False,
        })
    return {
        "development":{"cells":copy.deepcopy(cells)},
        "temporal_diagnostic":{"cells":copy.deepcopy(cells)},
    },json.loads(SNAP.read_text(encoding="utf-8"))


def test_231_kept_but_exact_21_blocked(monkeypatch:pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s.source_e2,"analyze",lambda _:None)
    e2,q=inputs(100.0)
    data=s.stress(e2,q)
    assert data["counts"]=={
        "total":231,
        "blocked_contract_or_zero_spread_cells":21,
        "eligible_only_for_nonhistorical_spot_comparison":210,
        "dev_above_current_spot_spread":210,
        "diag_above_current_spot_spread":210,
        "both_above_current_spot_spread":210,
    }
    assert data["G1_certified"] is False
    assert data["history_based_spread_calibration"] is False
    assert data["real_net_PF_sharpe_sortino_DD_measured"] is False
    assert all(x["screen_usable_as_trade_authorization"] is False for x in data["rows"])
    assert len(data["rows"])==231


def test_invalid_symbol_costs_never_promoted_even_large_gross(monkeypatch:pytest.MonkeyPatch)->None:
    monkeypatch.setattr(s.source_e2,"analyze",lambda _:None)
    e2,q=inputs(100000.0)
    x=s.stress(e2,q)
    blocked=[row for row in x["rows"] if row["symbol"] in s.BLOCKED]
    assert len(blocked)==21
    assert all(row["above_one_spot_spread_in_both_periods_NOT_EDGE"] is None for row in blocked)
    assert all(row["development"]["one_spot_spread_subtracted_from_gross_NOT_NET_bps"] is None
               for row in blocked)


def test_paired_delta_IS_NOT_subtracted_twice_for_matched_control(monkeypatch:pytest.MonkeyPatch)->None:
    monkeypatch.setattr(s.source_e2,"analyze",lambda _:None)
    e2,q=inputs(0.3)
    v=s.stress(e2,q)
    cell=next(x for x in v["rows"] if x["symbol"]=="EURUSD")
    assert cell["development"]["historic_paired_delta_bps_UNCHANGED"]==-.7
    assert cell["development"]["one_spot_spread_subtracted_from_gross_NOT_NET_bps"]<.3
    assert cell["development"]["screenshot_quote_not_time_aligned"]


def test_real_parent_signed_invariants_cannot_be_bypassed() -> None:
    # The implementation requires original E2 signed JSON SHA and recomputes
    # its Holm inference in source_e2.analyze before performing any join.
    content=Path(s.__file__).read_text(encoding="utf-8")
    assert "source_e2.analyze(e2)" in content
    assert "source_e2.load_signed(" in content
    assert "net_trade_or_live_approved" in content
    assert s.NOT_EXECUTABLE=="SPOT_QUOTE_NOT_HISTORICAL_E2_ENTRY_EXIT_CONTRACT"


def test_no_original_ohlc_market_data_or_live_order_execution() -> None:
    content=Path(s.__file__).read_text(encoding="utf-8")
    for forbidden in ("ProtoOANewOrderReq","place_order(",'["open_relative"]',
                      '["close_relative"]',"live_execution_client"):
        assert forbidden not in content
