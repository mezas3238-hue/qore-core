from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_winner_preservation_adjudicator_v47 as preservation,
)


def _trade(trade_id: str, r: str) -> preservation.PreservationTrade:
    return preservation.PreservationTrade(
        trade_id=trade_id,
        realized_r=Decimal(r),
    )


def test_winner_preservation_passes_only_when_both_utc_gates_pass() -> None:
    baseline = (
        _trade("w1", "2"),
        _trade("w2", "3"),
        _trade("w3", "1"),
        _trade("w4", "4"),
        _trade("w5", "2"),
        _trade("l1", "-1"),
        _trade("l2", "-1"),
    )
    report = preservation.adjudicate_winner_preservation(
        baseline,
        frozenset({"w1", "w2", "w3", "w4", "w5", "l1"}),
    )
    assert report.winner_count_preservation == Decimal("1")
    assert report.winner_r_preservation == Decimal("1")
    assert report.passed is True


def test_winner_count_below_eighty_percent_fails() -> None:
    baseline = tuple(
        [_trade(f"w{i}", "1") for i in range(5)]
        + [_trade("l1", "-1")]
    )
    report = preservation.adjudicate_winner_preservation(
        baseline,
        frozenset({"w0", "w1", "w2", "l1"}),
    )
    assert report.winner_count_preservation == Decimal("0.6")
    assert report.winner_count_gate_passed is False
    assert report.passed is False


def test_selected_ids_must_be_subset_of_frozen_baseline() -> None:
    with pytest.raises(ValueError, match="outside baseline"):
        preservation.adjudicate_winner_preservation(
            (_trade("w1", "1"),),
            frozenset({"unknown"}),
        )
