from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r3a_btcusd_chronological import (
    BINDING,
    CANDIDATE_IDENTITY,
    END,
    MIN_PF,
    MIN_TRADES,
    START,
    YEAR_BOUNDARIES,
)


def test_r3a_candidate_is_exact_frozen_ref2_plus() -> None:
    assert CANDIDATE_IDENTITY == "VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001"
    assert BINDING is CandidateId.BTC_REF2_PLUS


def test_r3a_window_and_gate_are_frozen() -> None:
    assert START.isoformat() == "2017-09-21T00:00:00+00:00"
    assert END.isoformat() == "2026-09-21T00:00:00+00:00"
    assert len(YEAR_BOUNDARIES) == 10
    assert MIN_TRADES == 250
    assert MIN_PF == 1.40
