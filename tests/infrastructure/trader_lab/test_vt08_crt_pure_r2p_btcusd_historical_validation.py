from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2p_btcusd_historical_validation import (
    CANDIDATE_FAMILY,
    MAX_DD_R,
    MIN_PF,
    MIN_TRADES,
    R2J_BINDING,
    VALIDATION_END,
    VALIDATION_FOLD,
    VALIDATION_START,
    ValidationCandidate,
)


def test_r2p_candidate_family_is_frozen() -> None:
    assert CANDIDATE_FAMILY == (
        ValidationCandidate.CONTROL,
        ValidationCandidate.BTC_BEARISH,
        ValidationCandidate.BTC_BODY_GE_050,
        ValidationCandidate.BTC_REF2_PLUS,
    )
    assert R2J_BINDING[ValidationCandidate.BTC_BEARISH] is CandidateId.BTC_BEARISH
    assert (
        R2J_BINDING[ValidationCandidate.BTC_BODY_GE_050]
        is CandidateId.BTC_BODY_GE_050
    )
    assert (
        R2J_BINDING[ValidationCandidate.BTC_REF2_PLUS]
        is CandidateId.BTC_REF2_PLUS
    )


def test_r2p_window_is_earlier_and_frozen() -> None:
    assert VALIDATION_START == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
    assert VALIDATION_FOLD == datetime(2021, 9, 21, 0, 0, tzinfo=UTC)
    assert VALIDATION_END == datetime(2022, 9, 21, 0, 0, tzinfo=UTC)


def test_r2p_reuses_r2j_gate() -> None:
    assert MIN_TRADES == 24
    assert MIN_PF == 1.05
    assert MAX_DD_R == 12.0
