from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2s_audusd_historical_validation import (
    BINDING,
    END,
    FAMILY,
    FOLD,
    START,
    Candidate,
)


def test_r2s_family_is_frozen() -> None:
    assert FAMILY == (Candidate.CONTROL, Candidate.AUD_G1)
    assert BINDING[Candidate.AUD_G1] is CandidateId.AUD_G1


def test_r2s_window_is_frozen() -> None:
    assert START == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
    assert FOLD == datetime(2021, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
