from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2y_btcusd_final_fresh import (
    BINDING,
    CHALLENGER,
    END,
    FAMILY,
    FOLD,
    PRIMARY,
    START,
    Candidate,
)


def test_r2y_primary_and_challenger_are_frozen() -> None:
    assert FAMILY == (
        Candidate.BTC_REF2_PLUS_PRIMARY,
        Candidate.BTC_BEARISH_CHALLENGER,
    )
    assert PRIMARY is Candidate.BTC_REF2_PLUS_PRIMARY
    assert CHALLENGER is Candidate.BTC_BEARISH_CHALLENGER
    assert BINDING[PRIMARY] is CandidateId.BTC_REF2_PLUS
    assert BINDING[CHALLENGER] is CandidateId.BTC_BEARISH


def test_r2y_fresh_window_is_preserved_one_year() -> None:
    assert START.isoformat() == "2017-09-21T00:00:00+00:00"
    assert FOLD.isoformat() == "2018-03-21T00:00:00+00:00"
    assert END.isoformat() == "2018-09-21T00:00:00+00:00"
    assert START < FOLD < END
