"""No new price data; validate joint-week resampling and 231 descriptive outputs."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path

import numpy as np
import pytest

from qore.infrastructure.trader_lab import qore_native_e3_multiblock_method_shrinkage_v1 as e3


def make_docs(value:float=0.3) -> dict:
    docs = {}
    for symbol in e3.parent.SYMBOLS:
        sections = []
        for method in e3.parent.METHODS:
            events = []
            for year in (2020, 2023):
                for week in range(5):
                    d = datetime(year, 1, 6 if year == 2020 else 2, 16, tzinfo=UTC) + timedelta(weeks=week)
                    iso=d.date().isocalendar()
                    events.append({
                        "reference_entry_utc":d.isoformat(),
                        "utc_date":d.date().isoformat(),
                        "iso_week":f"{iso.year}-W{iso.week:02d}",
                        "strategy_gross_bps": value,
                        "baseline_gross_bps":0.0,
                        "paired_delta_bps":value,
                    })
            sections.append({"method_id":method,"paired_events":events})
        docs[symbol]=sections
    return docs


def test_bootstrap_same_week_draw_for_entire_cross_asset_matrix() -> None:
    a=e3.circular_block_week_counts(17,4,15,20261012)
    b=e3.circular_block_week_counts(17,4,15,20261012)
    assert a.shape==(15,17)
    assert np.array_equal(a,b)
    assert np.all(a.sum(axis=1)==17)
    assert np.all(a>=0)
    assert np.any(a>1)


def test_block_guard_rejects_invalid_lengths_and_trials() -> None:
    for args in ((0,1,10,1),(3,4,10,1),(3,0,10,1),(3,1,0,1)):
        with pytest.raises(ValueError):
            e3.circular_block_week_counts(*args)


def test_equal_market_mean_does_not_silently_drop_missing_symbol() -> None:
    a=np.array([[1.0,2.0,3.0],[1.0,float("nan"),3.0]])
    m=e3.panel_mean(a,[0,1,2])
    assert m[0]==2
    assert np.isnan(m[1])


def test_seven_methods_and_28_strata_with_all_231_cells() -> None:
    r=e3.analyze_period(make_docs(), "development", replicates=18)
    assert r["markets"]==33 and r["methods"]==7 and r["cell_count"]==231
    assert r["calendar_week_count"]==5
    assert len(r["all_231_market_shrinkage_descriptors"])==231
    for length in ("1","2","4"):
        block=r["block_sensitivities"][length]
        assert len(block["seven_methods"])==7
        assert len(block["four_families_by_method_descriptive"])==28
        assert all(x["n_paired_events_sum_not_independent"]==165 for x in block["seven_methods"])
        assert all(x["gross_equal_market_bps"]==pytest.approx(.3) for x in block["seven_methods"])
        assert all(x["paired_delta_equal_market_bps"]==pytest.approx(.3) for x in block["seven_methods"])
        assert all(not x["BH_positive_at_10pct_not_certified"] for x in block["seven_methods"])
        # Artificially constant weekly data has degenerate variance and MUST NOT appear significant.\n        assert all(not x["passed_bootstrap_data_gate"] for x in block["seven_methods"])\n        assert all(x["p_two_sided_null_centered_exploratory"] == 1.0 for x in block["seven_methods"])


def test_two_period_screen_is_descriptive_even_if_everything_positive(monkeypatch:pytest.MonkeyPatch) ->None:
    monkeypatch.setattr(e3,"BOOTSTRAP",18)
    # Analyze docs instead of signed GH loader; each of two periods has 5 calendar weeks.
    monkeypatch.setattr(e3,"original_event_witnesses",lambda _: make_docs(.3))
    r=e3.analyze(Path("/does-not-download-price-data"))
    assert len(r["cross_period_seven_method_descriptive_screen"])==7
    assert all(x["positive_gross_and_delta_both_periods_all_L"] for x in
               r["cross_period_seven_method_descriptive_screen"])
    assert all(x["edge_certified"] is False for x in
               r["cross_period_seven_method_descriptive_screen"])
    assert r["traders_certified"]==0
    assert r["source_33_signed_market_witnesses"]==33
    assert r["original_2024_plus_OHLC_unopened"]


def test_moments_shrinkage_is_descriptor_not_independent_evidence() -> None:
    effects=np.array([float(i)/100 for i in range(33)])
    se=np.array([.15]*33)
    meta,rows=e3.shrinkage_by_method("REVERSAL_12H",effects,se)
    assert len(rows)==33
    assert 0<=rows[0]["shrink_weight"]<=1
    assert all(row["score_not_independent_out_of_sample"] for row in rows)
    assert meta["same_currency_factor_correlation_not_removed"]
    assert "DESCRIPTIVE" in meta["status"]


def test_original_artifact_must_be_present_and_signed(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="33 exact"):
        e3.original_event_witnesses(tmp_path)


def test_no_price_field_or_order_triggers_in_analysis() -> None:
    text=Path(e3.__file__).read_text(encoding="utf-8")
    for forbidden in ('row["open_relative"]','row["close_relative"]',
                      "ProtoOANewOrderReq","place_order(", "new_order("):
        assert forbidden not in text
