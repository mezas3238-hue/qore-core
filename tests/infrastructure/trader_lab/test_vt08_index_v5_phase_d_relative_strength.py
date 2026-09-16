from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_v5_phase_d_relative_strength import (
    _max_drawdown,
    _metrics,
    _retain_d1,
)


def _row(*, same: int, opposite: int, r: str = "1") -> dict[str, str]:
    return {
        "cross_index_simultaneous_same_side_signals": str(same),
        "cross_index_simultaneous_opposite_side_signals": str(opposite),
        "outcome_r": r,
    }


def test_d1_predicate_is_exact_and_fail_closed() -> None:
    assert _retain_d1(_row(same=2, opposite=0))
    assert not _retain_d1(_row(same=1, opposite=0))
    assert not _retain_d1(_row(same=3, opposite=0))
    assert not _retain_d1(_row(same=2, opposite=1))


def test_metrics_apply_friction_and_drawdown() -> None:
    rows = [
        _row(same=2, opposite=0, r="1"),
        _row(same=2, opposite=0, r="-1"),
        _row(same=2, opposite=0, r="2"),
    ]
    result = _metrics(rows, Decimal("0.05"))
    assert result["n"] == 3
    assert result["wins"] == 2
    assert result["losses"] == 1
    assert Decimal(result["total_r"]) == Decimal("1.85")
    assert Decimal(result["max_drawdown_r"]) == Decimal("1.05")


def test_max_drawdown_uses_running_equity_peak() -> None:
    values = [Decimal("1"), Decimal("-0.5"), Decimal("-1"), Decimal("2")]
    assert _max_drawdown(values) == Decimal("1.5")
