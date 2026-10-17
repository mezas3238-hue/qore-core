from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2r_btcusd_earlier_validation import (
    BINDING,
    END,
    FAMILY,
    FOLD,
    START,
    Candidate,
)


def test_r2r_family_is_frozen_to_two_survivors_plus_control() -> None:
    assert FAMILY == (
        Candidate.CONTROL,
        Candidate.BTC_BEARISH,
        Candidate.BTC_REF2_PLUS,
    )
    assert BINDING[Candidate.BTC_BEARISH] is CandidateId.BTC_BEARISH
    assert BINDING[Candidate.BTC_REF2_PLUS] is CandidateId.BTC_REF2_PLUS


def test_r2r_window_preserves_2017_2018() -> None:
    assert START == datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
    assert FOLD == datetime(2019, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
