from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2o_btcusd_block_robustness import (
    BASE_SEED,
    BLOCK_LENGTHS,
    CANDIDATES,
    RESAMPLE_COUNT,
    _max_drawdown,
    _policy,
    _resample,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)


def test_r2o_candidate_and_block_families_are_frozen() -> None:
    assert CANDIDATES == (
        CandidateId.BTC_BEARISH,
        CandidateId.BTC_BODY_GE_050,
        CandidateId.BTC_REF2_PLUS,
    )
    assert BLOCK_LENGTHS == (2, 4, 8)
    assert RESAMPLE_COUNT == 5_000
    assert BASE_SEED == 20_260_923


def test_r2o_resampling_is_deterministic() -> None:
    values = (1.0, -1.0, 0.5, 2.0, -0.25, 0.75)
    policy = _policy(2)

    first = _resample(values, policy, 17)
    second = _resample(values, policy, 17)

    assert first == second
    assert len(first) == len(values)


def test_r2o_drawdown_uses_equity_path() -> None:
    assert _max_drawdown((1.0, -0.5, -1.0, 2.0)) == 1.5
