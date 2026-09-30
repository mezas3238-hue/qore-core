from qore.infrastructure.trader_lab.capitalizer_v49_holdout_contract import (
    V49_RESERVED_HOLDOUT_1Y,
)


def test_reserved_holdout_is_one_year_and_precedes_development() -> None:
    state = V49_RESERVED_HOLDOUT_1Y
    assert state.holdout_start.isoformat() == "2024-09-17T00:00:00+00:00"
    assert state.holdout_end.isoformat() == "2025-09-17T00:00:00+00:00"
    assert state.holdout_end == state.development_start


def test_reserved_holdout_does_not_open_fresh_or_allow_reuse_after_mutation() -> None:
    state = V49_RESERVED_HOLDOUT_1Y
    assert state.fresh_holdout_used is False
    assert state.methodology_mutation_after_result_allowed is False
    assert state.second_pass_same_holdout_after_mutation_allowed is False
    assert state.live_authorized is False
    assert state.real_capital_authorized is False
