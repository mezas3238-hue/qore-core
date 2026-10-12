"""Posthoc FDR audit requires original 231 fixed cells, refuses fabricated NET."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_e2_posthoc_bh_sensitivity_v1 as m


def parent_fixture() -> dict:
    periods = {}
    for period in m.PERIODS:
        cells = []
        for key in m.e2.CELLS:
            method, symbol = key.split("__")
            cells.append({
                "cell_id": key,
                "method_id": method,
                "symbol": symbol,
                "preexisting_result": m.e2.registry.cell_prior(method, symbol)["status"],
                "n_paired_days": 200,
                "n_iso_weeks": 60,
                "sample_gate": True,
                "gross_mean_bps": 0.0,
                "paired_delta_mean_bps": 0.0,
                "delta_bootstrap_p_two_sided_exploratory": 1.0,
                "p_Holm_FWER_231_exploratory": 1.0,
                "net_broker_certification": False,
            })
        periods[period] = {
            "cells": cells, "comparison_count_Holm": 231,
            "one_shared_synced_week_calendar": True,
            "bootstrap_draws": 20000, "net_certified": False,
        }
    return {
        "identity": m.e2.IDENTITY,
        "status": "E2_231_GROSS_RESEARCH_ONLY_NOT_NET_NOT_OOS_VIRGIN",
        "original_g0_source_sha256": m.e2.e1.SOURCE_33_SHA,
        "markets": 33, "methods": 7, "all_fixed_cells": 231,
        "2024_09_17_onward_prices_embargoed": True,
        "traders_certified": 0,
        "g1_historical_bidask_not_measured": True,
        "macro_news_known_asof_not_filtered": True,
        "production_untouched": True,
        **periods,
    }


def test_bh_monotone_with_duplicates_and_known_result() -> None:
    q = m.bh([0.001, 0.02, 0.2, 0.02, 1.0])
    assert q == pytest.approx([0.005, 1/30, 0.25, 1/30, 1.0])
    assert m.bh([1.0] * 231) == [1.0] * 231
    for bad in ([], [float("nan")], [-.1], [1.1]):
        with pytest.raises(ValueError):
            m.bh(bad)


def test_all_231_not_cherry_picked_or_recast_confirmatory() -> None:
    report = m.analyze(parent_fixture())
    assert report["status"] == "POSTHOC_EXPLORATORY_SENSITIVITY_NOT_PREREG_CONFIRMED"
    assert report["posthoc_after_Holm_result_known"] is True
    assert report["BH_guarantee_under_arbitrary_signed_market_dependence"] is False
    assert report["not_certified_regardless_of_q"] is True
    assert report["traders_certified"] == 0
    for p in m.PERIODS:
        d = report["outcomes_by_period"][p]
        assert d["n_all_cells"] == 231
        assert len(d["all_cells_qvalues_including_nulls"]) == 231
        assert d["n_nominal_5pct_any_sign"] == 0
        assert d["BH_FDR_thresholds"]["0.1"]["n_any_sign"] == 0


def test_no_laundered_Net_or_missing_market_or_prior_test() -> None:
    base = parent_fixture()
    a = copy.deepcopy(base)
    a["development"]["cells"].pop()
    b = copy.deepcopy(base)
    b["development"]["cells"][0]["preexisting_result"] = "BRAND_NEW_CONFIRMED"
    c = copy.deepcopy(base)
    c["temporal_diagnostic"]["cells"][0]["net_broker_certification"] = True
    d = copy.deepcopy(base)
    d["traders_certified"] = 1
    e = copy.deepcopy(base)
    e["temporal_diagnostic"]["cells"][0]["p_Holm_FWER_231_exploratory"] = 0.01
    for fake in (a, b, c, d, e):
        with pytest.raises(ValueError):
            m.analyze(fake)


def test_original_sha_required_even_if_data_exists(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        m.load_signed(tmp_path)


def test_posthoc_has_no_broker_orders_or_original_ohlc_price_reads() -> None:
    content = Path(m.__file__).read_text(encoding="utf-8")
    for forbidden in ("ProtoOANewOrderReq", "place_order(", '["open_relative"]',
                      '["close_relative"]', "market_data_api_client"):
        assert forbidden not in content
