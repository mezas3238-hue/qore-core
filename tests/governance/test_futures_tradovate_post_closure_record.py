from __future__ import annotations

from pathlib import Path

import qore.infrastructure.futures_tradovate_candidate as tradovate

_ADDENDUM = Path(
    "docs/missions/"
    "FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM-POST-CLOSURE-ADDENDUM.md"
)
_CANDIDATE_DOC = Path(
    "docs/architecture/QORE-FUTURES-TRADOVATE-CANDIDATE-001.md"
)
_HISTORICAL_CLOSURE = Path(
    "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM-CLOSURE.md"
)


def test_post_closure_addendum_records_optional_candidate_without_rewriting_history() -> None:
    addendum = _ADDENDUM.read_text(encoding="utf-8")
    closure = _HISTORICAL_CLOSURE.read_text(encoding="utf-8")

    assert "POST-CLOSURE RECORD — NON-PRODUCTION ONLY" in addendum
    assert "QORE-FUTURES-TRADOVATE-CANDIDATE-001" in addendum
    assert "PR #233" in addendum
    assert "historical closure remains valid" in addendum
    assert "Delivery 13 is explicitly optional" in closure


def test_optional_candidate_remains_offline_and_does_not_change_mandatory_set() -> None:
    addendum = _ADDENDUM.read_text(encoding="utf-8")
    candidate_doc = _CANDIDATE_DOC.read_text(encoding="utf-8")
    assessment = tradovate.evaluate_tradovate_candidate()

    assert "TradeStation\nIBKR\ntastytrade" in addendum
    assert "optional fourth candidate" in addendum
    assert assessment.status is (
        tradovate.TradovateCandidateStatus.OPERATIONAL_EVIDENCE_REQUIRED
    )
    assert not assessment.authenticated_operational_evidence
    assert not assessment.network_io_performed
    assert not assessment.production_authorized
    assert "Production                                = CLOSED" in candidate_doc


def test_post_closure_record_preserves_oanda_blocker_and_authority_boundaries() -> None:
    addendum = _ADDENDUM.read_text(encoding="utf-8")

    assert "#146" in addendum
    assert "OPEN/BLOCKED" in addendum
    assert "NO CORE DECISION -> NO NEW TRADING ACTION" in addendum
    assert "NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION" in addendum
    assert "Production                        = CLOSED" in addendum
    assert "Real capital                      = CLOSED" in addendum
