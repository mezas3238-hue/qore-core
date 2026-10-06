from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch2_t16_fresh_oos_utility import (
    FROZEN_AT,
    MINIMUM_OOS_OBSERVATIONS,
    T16UtilityObservation,
    evaluate_t16_fresh_oos_utility,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _rows(*, target: Decimal, hedge: Decimal):
    return tuple(
        T16UtilityObservation(
            market_at=FROZEN_AT + timedelta(minutes=index + 1),
            target_return=target,
            hedge_return=hedge,
        )
        for index in range(MINIMUM_OOS_OBSERVATIONS)
    )


def test_t16_utility_requires_strict_net_protection_in_all_four_folds() -> None:
    result = evaluate_t16_fresh_oos_utility(
        hedge_symbol="US500",
        observations=_rows(
            target=Decimal("-0.002"),
            hedge=Decimal("-0.0008"),
        ),
        conservative_round_trip_cost_bps=Decimal("0"),
    )
    assert len(result.fold_results) == 4
    assert result.four_of_four_pass is True
    assert result.net_economic_benefit_proven is True
    assert result.fresh_oos_utility_proven is True
    assert result.productive_authority is False


def test_t16_utility_has_no_pooled_rescue() -> None:
    rows = list(
        _rows(
            target=Decimal("-0.002"),
            hedge=Decimal("-0.0008"),
        )
    )
    for index in range(8):
        rows[index] = T16UtilityObservation(
            market_at=rows[index].market_at,
            target_return=Decimal("-0.001"),
            hedge_return=Decimal("0.001"),
        )
    result = evaluate_t16_fresh_oos_utility(
        hedge_symbol="US500",
        observations=tuple(rows),
        conservative_round_trip_cost_bps=Decimal("0"),
    )
    assert result.fold_results[0].pass_gate is False
    assert result.four_of_four_pass is False
    assert result.t16_candidate_pass is False


def test_t16_utility_rejects_pre_freeze_rows() -> None:
    with pytest.raises(CiboCapitalManagementError, match="postdate"):
        T16UtilityObservation(
            market_at=FROZEN_AT,
            target_return=Decimal("0.001"),
            hedge_return=Decimal("0.001"),
        )


def test_t16_utility_rejects_unregistered_candidate() -> None:
    with pytest.raises(CiboCapitalManagementError, match="outside"):
        evaluate_t16_fresh_oos_utility(
            hedge_symbol="OTHER",
            observations=_rows(
                target=Decimal("-0.002"),
                hedge=Decimal("-0.0008"),
            ),
            conservative_round_trip_cost_bps=Decimal("1"),
        )
