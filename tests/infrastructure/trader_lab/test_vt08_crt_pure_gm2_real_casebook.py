"""Safety checks for the G-M2 real-case selection process (not source proof)."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_gm2_real_casebook import (
    _bucket,
    create_blind_casebook,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection as Direction,
)


BASE = datetime(2025, 3, 3, 12, tzinfo=UTC)


def c1() -> M15Bar:
    return M15Bar(BASE, 100, 110, 90, 104)


def c2(high: int, low: int, close: int) -> M15Bar:
    return M15Bar(BASE + timedelta(minutes=15), 100, high, low, close)


@pytest.mark.parametrize(
    ("high", "low", "close", "expected"),
    (
        (108, 94, 103, "NO_SWEEP"),
        (115, 85, 103, "TWO_SIDED_SWEEP"),
        (108, 80, 80, "ONE_SIDED_OUTSIDE_CLOSE"),
        (108, 85, 102, "ALIGNED_C2_CONTEXT"),
        (115, 94, 102, "OPPOSITE_C2_CONTEXT"),
    ),
)
def test_c2_bucket_uses_closed_c1_c2_only(
    high: int, low: int, close: int, expected: str
) -> None:
    bucket, _ = _bucket(c1(), c2(high, low, close), Direction.BULLISH, ())
    assert bucket == expected


def test_known_previous_opposite_is_separate_review_stratum() -> None:
    bucket, direction = _bucket(
        c1(),
        c2(108, 85, 102),
        Direction.BULLISH,
        (Direction.BEARISH,),
    )
    assert bucket == "PRIOR_OPPOSITE_C2_CONTEXT"
    assert direction is Direction.BULLISH


def test_disconnected_m15_pair_is_not_rebranded_as_c2_event() -> None:
    disconnected = M15Bar(BASE + timedelta(minutes=30), 100, 108, 85, 102)
    bucket, direction = _bucket(
        c1(), disconnected, Direction.BULLISH, ()
    )
    assert bucket == "INVALID_NONCONTIGUOUS_OR_BAD_REFERENCE"
    assert direction is None


def test_market_freeze_and_empty_data_fail_closed() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        create_blind_casebook(CrtPureMarket.BTCUSD, ())
    with pytest.raises(ValueError, match="per_bucket"):
        create_blind_casebook(CrtPureMarket.AUDUSD, (), per_bucket=0)
