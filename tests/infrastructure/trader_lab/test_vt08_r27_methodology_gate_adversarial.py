"""Adversarial VT08 R27 methodology gate tests (no source signoff fabricated)."""
import pytest

from qore.infrastructure.trader_lab.vt08_r27_methodology_gate import (
    REQUIRED,
    adjudicate,
)


def packet():
    return {
        "case_id_sha256": "case",
        "market": "EURJPY",
        "source_sha256": "source",
        "decision_as_of_utc": "2026-10-01T12:30:00+00:00",
        "rule_evidence": {},
        "independent_reviews": [],
        "unresolved_disagreements": [],
    }


def test_missing_source_blocks():
    result = adjudicate(packet())
    assert result["methodology_gate"] == "BLOCKED"
    assert "reference_swing" in result["blocked_reasons"]
    assert "independent_A_B_signoffs" in result["blocked_reasons"]
    assert result["trade_authorized"] is False


def test_future_cisd_blocks():
    p = packet()
    p["rule_evidence"]["causal_cisd"] = {
        "verdict": "AUTHOR_SOURCE_VALIDATED",
        "primary_author_url": "https://ttrades.com/article",
        "author_section": "CISD",
        "source_bar_ids": ["M3bar"],
        "available_at_utc": "2026-10-01T10:31:00-02:00",
    }
    assert "causal_cisd" in adjudicate(p)["blocked_reasons"]


def test_source_domain_spoof_blocks():
    p = packet()
    p["rule_evidence"]["reference_swing"] = {
        "verdict": "AUTHOR_SOURCE_VALIDATED",
        "primary_author_url": "https://ttrades.com.attacker.invalid/page",
        "author_section": "Swing",
        "source_bar_ids": ["M30bar"],
        "available_at_utc": "2026-10-01T12:29:00Z",
    }
    assert "reference_swing" in adjudicate(p)["blocked_reasons"]


def test_invalid_clock_rejected():
    p = packet()
    p["decision_as_of_utc"] = "not-a-time"
    with pytest.raises(ValueError):
        adjudicate(p)


def test_all_methodological_fields_are_required():
    assert len(REQUIRED) == 8
