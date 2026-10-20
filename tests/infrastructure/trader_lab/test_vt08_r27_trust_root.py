"""VT08 R27 methodological gate: reviewer trust-root regression tests."""
from qore.infrastructure.trader_lab.vt08_r27_methodology_gate import adjudicate


def test_absent_trust_root_blocks():
    packet = {
        "case_id_sha256": "id",
        "market": "EURJPY",
        "source_sha256": "source",
        "decision_as_of_utc": "2026-10-01T12:30:00Z",
        "rule_evidence": {},
        "independent_reviews": [
            {"reviewer_id": "A", "signed_evidence": "fakeA", "verdict": "PASS"},
            {"reviewer_id": "B", "signed_evidence": "fakeB", "verdict": "PASS"},
        ],
        "unresolved_disagreements": [],
    }
    result = adjudicate(packet)
    assert "trusted_reviewer_roster_missing" in result["blocked_reasons"]
    assert "independent_A_B_signoffs" in result["blocked_reasons"]
    result = adjudicate(packet, trusted_reviewers=frozenset({"A"}))
    assert "independent_A_B_signoffs" in result["blocked_reasons"]
    assert result["trade_authorized"] is False
