"""VT08 R29 source-first triage adversarial checks."""
import pytest

from qore.infrastructure.trader_lab.vt08_r29_methodological_triage import (
    audit_review_readiness,
)


def sample():
    cid = "a" * 64
    return {
        "schema": "qore.vt08.r28.frozen_r19_methodology_queue.v1",
        "market": "EURJPY",
        "source_sample_count": 1,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "verdict": "VT08_METHOD_NOT_CERTIFIED",
        "original_r19_sha256": "b" * 64,
        "methodology_cases": [{
            "case_id_sha256": cid, "market": "EURJPY",
            "gate": {"methodology_gate": "BLOCKED", "trade_authorized": False},
            "review_state": "WAIT_FOR_INDEPENDENT_METHOD_AUTHOR_ADJUDICATION",
            "questions": {
                "reference_swing": "swing?",
                "significant_poi": "poi?",
                "protected_swing": "protected?",
            },
            "candidate_h1_fvg": {"type": "BULLISH"},
        }],
    }


def test_geometric_fvg_is_not_methodology_approval():
    result = audit_review_readiness(sample())
    assert result["poi_screening_counts"] == {
        "GEOMETRIC_FVG_PRESENT_NOT_AUTHOR_SELECTED": 1
    }
    assert result["author_certified"] == 0
    assert result["review_cases"][0]["methodological_admission"] is False
    assert result["trade_authorized"] is False


def test_rejects_forged_admission():
    data = sample()
    data["methodology_cases"][0]["gate"]["methodology_gate"] = "PASS"
    with pytest.raises(ValueError, match="unverified methodological authority"):
        audit_review_readiness(data)


def test_rejects_duplicate_source_case():
    data = sample()
    data["methodology_cases"].append(dict(data["methodology_cases"][0]))
    data["source_sample_count"] = 2
    with pytest.raises(ValueError, match="duplicate source identity"):
        audit_review_readiness(data)
