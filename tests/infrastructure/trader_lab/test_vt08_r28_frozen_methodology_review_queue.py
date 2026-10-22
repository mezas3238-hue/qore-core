"""VT08 R28: frozen methodological sample integrity and WAIT behavior."""
import pytest

from qore.infrastructure.trader_lab.vt08_r28_frozen_methodology_review_queue import (
    build_methodology_queue,
)


def test_rejects_non_frozen_blind_sample():
    with pytest.raises(ValueError, match="integrity drift"):
        build_methodology_queue(
            {"market": "EURJPY", "review_packets": []},
            market="EURJPY",
        )


def test_rejects_unauthorized_market():
    with pytest.raises(ValueError, match="unauthorized market"):
        build_methodology_queue({}, market="BTCUSD")


def test_category_census_must_match(monkeypatch):
    import qore.infrastructure.trader_lab.vt08_r28_frozen_methodology_review_queue as mod
    monkeypatch.setattr(mod, "digest", lambda _: "pinned")
    monkeypatch.setitem(mod.PINNED_R19_REPORT_DIGESTS, "EURJPY", "pinned")
    count, source = mod.MARKET_EXPECTED["EURJPY"]
    blind = {
        "schema": mod.R19_SCHEMA, "seed": mod.R19_SEED,
        "market": "EURJPY", "original_r18_sha256": source,
        "original_r18_cases": count, "rater_A_signed": 0,
        "rater_B_signed": 0, "source_complete_entries": 0,
        "cognitive_admissions": 0, "broker_fills": 0,
        "holdout_7y_accessed": False, "sizing_used": False,
        "selected_source_only_cases": 1,
        "selected_category_counts": {"EXPECTED": 1},
        "review_packets": [{
            "case_id_sha256": "a" * 64, "market": "EURJPY",
            "category": "UNEXPECTED", "c3_opened_at_utc": "2026-10-01T12:30:00Z",
            "source_complete": False, "cognitive_ready": False,
            "orders_authorized": False, "human_rater_A_source_signoff": None,
            "human_rater_B_independent_signoff": None,
            "selection_rank_sha256": "b" * 64,
            "candidate_h1_fvg": None, "candidate_h1_prior_lows": [],
        }],
    }
    with pytest.raises(ValueError, match="category census drift"):
        mod.build_methodology_queue(blind, market="EURJPY")
