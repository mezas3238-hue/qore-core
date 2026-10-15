"""Qualitative original source-Cognition scenarios: NOT a return backtest."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import VERSION
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    FROZEN_G3_COG_GIT_BLOB,
    london_fixture,
    original_cog_scenario_dossier,
    source_fingerprint,
)


def test_actual_g3_original_cog_not_an_alternate_research_producer():
    report = original_cog_scenario_dossier()
    assert report["source_engine"] == (
        "ORIGINAL_VT31_ICT_CLEANROOM_G3_COG_V1"
    )
    assert report["source_engine_version"] == VERSION
    assert report["original_cog_directly_invoked"] is True
    assert report["original_source_hash"]["git_blob_sha1"] == (
        FROZEN_G3_COG_GIT_BLOB
    )
    assert len(report["original_source_hash"]["source_sha256"]) == 64
    assert source_fingerprint() == report["original_source_hash"]


def test_actual_cognition_and_justified_abstention_are_distinct_judgments():
    rows = original_cog_scenario_dossier()["cases"]
    assert [(x["name"], x["observed"]["action"]) for x in rows] == [
        ("LONDON_SOURCE_LONG", "LONG"),
        ("LONDON_HOLD_SAME_ASOF", "LONG"),
        ("NO_PREVIOUS_CASH_POOL", "WAIT"),
        ("MSS_NOT_YET_CONFIRMED", "WAIT"),
        ("HTF_CONTEXT_MISSING", "WAIT"),
        ("AFTER_DOL_CONSUMED", "WAIT"),
        ("AFTER_PIVOT_REVERSAL", "WAIT"),
        ("FUTURE_RETRO_ASOF", "REJECT"),
        ("G3_MSS_ANCHOR", "LONG"),
        ("LONDON_NOT_TTRADES_PROFILE", "LONG"),
    ]
    assert all(
        x["observed"]["trade_authorized"] is False
        and x["observed"]["research_only"] is True
        and x["author_method_certified"] is False
        and x["human_independent_review"] is False
        for x in rows
    )
    assert rows[0]["observed"]["decision"]["draw_family"] == (
        "PRIOR_NY_CASH_SESSION_HIGH"
    )
    assert rows[0]["observed"]["decision"]["mss_structure_level"] == "105"
    assert rows[0]["observed"]["decision"]["draw_target"] == "150"
    assert rows[8]["observed"]["decision"]["mss_anchor_close"] == "107"


def test_good_abstention_never_replaced_by_trade_or_false_reward():
    rows = original_cog_scenario_dossier()["cases"]
    abstentions = [x for x in rows if x["observed"]["action"] == "WAIT"]
    assert len(abstentions) == 5
    for item in abstentions:
        assert item["observed"]["decision"] is None
        assert item["observed"]["trade_authorized"] is False
        assert item["qualitative_adjudication"].startswith("EXPECTED_ABSTENTION")


def test_no_auto_certification_from_tests_or_fixture():
    evidence = original_cog_scenario_dossier()
    assert evidence["methodology_status"].startswith("PENDING_")
    assert evidence["cognitive_status"].startswith("PENDING_")
    assert evidence["financial_results"] is None
    assert evidence["human_cog_ops_signature_proven"] is False
    assert evidence["fresh_holdout_used"] is False
    assert evidence["orders_executed"] == 0
    assert evidence["trader_sizing_actions"] == 0
    assert evidence["trader_certified"] is False
    assert evidence["live_authorized"] is False
    assert len(london_fixture()[0]) == 576


def test_london_ict_is_not_ttrades_am_author_fidelity():
    evidence = original_cog_scenario_dossier()
    scope = evidence["cases"][-1]
    assert scope["qualitative_adjudication"] == (
        "ICT_GENERAL_LONDON_IS_NOT_TTRADES_NYAM_AUTHOR_ATTESTATION"
    )
    assert scope["author_method_certified"] is False
    assert scope["profile"] == "ICT_GENERAL_2023_LONDON_QORE_COG_PROXY"


def test_faulty_g3_blob_claim_never_passes():
    assert source_fingerprint()["git_blob_sha1"] == FROZEN_G3_COG_GIT_BLOB
    with pytest.raises(ValueError, match="ORIGINAL_G3_COG_SOURCE_MUTATED"):
        from scripts import vt31_original_g3_cog_qualitative_court_20261014 as module

        original = module.FROZEN_G3_COG_GIT_BLOB
        try:
            module.FROZEN_G3_COG_GIT_BLOB = "0" * 40
            module.source_fingerprint()
        finally:
            module.FROZEN_G3_COG_GIT_BLOB = original


def test_scenario_asof_is_own_authentic_closed_bar_not_baseline_time():
    rows = original_cog_scenario_dossier()["cases"]
    baseline = datetime.fromisoformat(rows[0]["as_of"])
    early = next(x for x in rows if x["name"] == "MSS_NOT_YET_CONFIRMED")
    swept = next(x for x in rows if x["name"] == "AFTER_DOL_CONSUMED")
    revoked = next(x for x in rows if x["name"] == "AFTER_PIVOT_REVERSAL")
    assert datetime.fromisoformat(early["as_of"]) == baseline - timedelta(minutes=1)
    assert datetime.fromisoformat(swept["as_of"]) == baseline + timedelta(minutes=1)
    assert datetime.fromisoformat(revoked["as_of"]) == baseline + timedelta(minutes=1)
    assert all(
        x["as_of"] == x["observed"]["evaluated_as_of"]
        for x in rows if x["name"] != "FUTURE_RETRO_ASOF"
    )
