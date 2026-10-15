"""B R9 adversarial tests: source causality, equal touch, no promotion to trade."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import vt08_b_r9_h1_target_independent_v1 as b

START = datetime(2025, 5, 15, 10, tzinfo=UTC)
SHA = "a" * 64


def fixture():
    raw = {}
    for i in range(8):
        opened = START + i * timedelta(minutes=15)
        # First completed H1 has high 120; second H1 high 119.
        high = "120" if i == 0 else "119"
        raw[opened] = {
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(minutes=15)).isoformat(),
            "open": "110", "high": high, "low": "100", "close": "110",
        }
    c2 = START + timedelta(hours=1, minutes=30)
    decision = c2 + timedelta(minutes=30)
    levels = b.independently_reconstruct(raw, SHA, [(c2, decision)])[0]
    assert len(levels) == 2
    for x in levels:
        x["higher_than_c2_close_proxy"] = True
    identity = {
        "market": "EURJPY", "c2_opened_at_utc": c2.isoformat(),
        "decision_at_utc": decision.isoformat(),
    }
    r6 = {
        "schema": b.TARGET_SCHEMA, "market": "EURJPY",
        "input_m15_source_sha256": SHA,
        "frozen_source_events": 1,
        "source_complete_entries": 0, "broker_fills": 0, "profit_factor": None,
        "witnesses": [{
            **identity, "witness_count": 2, "c2_close_price_source_proxy": "110",
            "untouched_h1_high_candidates": levels, "author_target_selected": False,
        }],
    }
    r7 = {
        "schema": b.JOIN_SCHEMA, "market": "EURJPY",
        "frozen_event_count": 1,
        "source_complete_entries": 0, "broker_fills": 0, "profit_factor": None,
        "signed_A_B_manifest": None, "certified": False,
        "all_source_only_cases": [{
            **identity, "source_unconsumed_h1_highs": deepcopy(levels),
            "target_cardinality": 2, "source_author_target_selected": False,
        }],
    }
    return raw, r6, r7, c2, decision


def test_independent_two_h1_sources_pre_and_during_c2(monkeypatch):
    raw, r6, r7, _, _ = fixture()
    monkeypatch.setattr(b, "_raw_bars", lambda *_: (SHA, raw))
    result = b.audit_a_r6_r7_native(
        r6, r7, market="EURJPY", m15_file=Path("fixture.json"),
    )
    assert result["all_cases_reconstructed"] == 1
    assert result["candidate_levels_known_before_c2"] == 1
    assert result["candidate_levels_newly_known_during_c2"] == 1
    assert result["a_r6_r7_native_identical"] is True
    assert result["ttrades_target_relevance_certified"] is False
    assert result["broker_fills"] == 0


def test_high_equal_to_level_is_consumed():
    raw, _, _, c2, d = fixture()
    # Touch first H1 high with a later 11:xx bar.
    raw[START + timedelta(hours=1, minutes=15)]["high"] = "120"
    result = b.independently_reconstruct(raw, SHA, [(c2, d)])
    # New H1 now has high 120, old H1 was invalidated on touch.
    assert len(result[0]) == 1
    assert result[0][0]["origin_h1_available_at_utc"] == d.isoformat()


def test_future_bar_never_read():
    raw, _, _, c2, d = fixture()
    future = d
    raw[future] = {
        "opened_at": future.isoformat(),
        "closed_at": (future + timedelta(minutes=15)).isoformat(),
        "open": "110", "high": "999", "low": "100", "close": "110",
    }
    original = fixture()[0]
    assert (
        b.independently_reconstruct(raw, SHA, [(c2, d)])
        == b.independently_reconstruct(original, SHA, [(c2, d)])
    )


def test_mutated_high_with_rehashed_report_still_fails(monkeypatch):
    raw, r6, r7, _, _ = fixture()
    monkeypatch.setattr(b, "_raw_bars", lambda *_: (SHA, raw))
    r6["witnesses"][0]["untouched_h1_high_candidates"][0]["high"] = "999"
    r7["all_source_only_cases"][0]["source_unconsumed_h1_highs"][0]["high"] = "999"
    with pytest.raises(ValueError, match="native target high differs"):
        b.audit_a_r6_r7_native(r6, r7, market="EURJPY", m15_file=Path("."))


def test_origin_bar_id_tamper_rejected(monkeypatch):
    raw, r6, r7, _, _ = fixture()
    monkeypatch.setattr(b, "_raw_bars", lambda *_: (SHA, raw))
    for levels in (
        r6["witnesses"][0]["untouched_h1_high_candidates"],
        r7["all_source_only_cases"][0]["source_unconsumed_h1_highs"],
    ):
        levels[0]["origin_source_m15_bar_ids"][0] = "not-a-real-bar"
    with pytest.raises(ValueError, match="origin_source_m15_bar_ids"):
        b.audit_a_r6_r7_native(r6, r7, market="EURJPY", m15_file=Path("."))


def test_discordant_r6_r7_and_fake_trades_rejected(monkeypatch):
    raw, r6, r7, _, _ = fixture()
    monkeypatch.setattr(b, "_raw_bars", lambda *_: (SHA, raw))
    r7["all_source_only_cases"][0]["source_unconsumed_h1_highs"].pop()
    with pytest.raises(ValueError, match="cardinality"):
        b.audit_a_r6_r7_native(r6, r7, market="EURJPY", m15_file=Path("."))
    _, r6, r7, _, _ = fixture()
    r7["broker_fills"] = 1
    with pytest.raises(ValueError, match="manufactured"):
        b.audit_a_r6_r7_native(r6, r7, market="EURJPY", m15_file=Path("."))


def test_source_gap_resets_untouched_proof():
    raw, _, _, c2, decision = fixture()
    raw.pop(START + timedelta(minutes=45))
    assert b.independently_reconstruct(raw, SHA, [(c2, decision)])[0]
    # First H1 no longer exists, second remains independently formed.
    result = b.independently_reconstruct(raw, SHA, [(c2, decision)])[0]
    assert len(result) == 1
    assert result[0][0]["origin_h1_available_at_utc"] == decision.isoformat()
