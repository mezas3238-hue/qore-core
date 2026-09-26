from qore.infrastructure.trader_lab import (
    capitalizer_dual_head_severe_descent_control_v26 as v26,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)


def _decision(
    index: int,
    realized_r: str,
) -> v18.InvalidationDecision:
    minute = index + 1
    return v18.InvalidationDecision(
        period="P",
        policy="SURFACE_CONTROL",
        symbol=f"S{index}",
        session="ASIA",
        operating_date="2026-01-01",
        entry_at=f"2026-01-01T00:{minute:02d}:00+00:00",
        current_drawdown_r="0",
        base_multiplier="1",
        surface_mode="ORIGINAL",
        trigger_name=None,
        trigger_available=False,
        activation_allowed=False,
        invalidation_applied=False,
        final_exit_at=f"2026-01-01T01:{minute:02d}:00+00:00",
        normalized_realized_r=realized_r,
    )


def test_severe_descent_labels_peak_to_trough_only() -> None:
    rows = (
        _decision(0, "1"),
        _decision(1, "-2"),
        _decision(2, "-2"),
        _decision(3, "-1"),
        _decision(4, "3"),
        _decision(5, "3"),
    )
    decisions = {(row.symbol, row.entry_at): row for row in rows}
    labels, episodes = v26._severe_descent_labels(decisions)
    assert episodes == 1
    assert labels[(rows[0].symbol, rows[0].entry_at)] is False
    assert labels[(rows[1].symbol, rows[1].entry_at)] is True
    assert labels[(rows[2].symbol, rows[2].entry_at)] is True
    assert labels[(rows[3].symbol, rows[3].entry_at)] is True
    assert labels[(rows[4].symbol, rows[4].entry_at)] is False
    assert labels[(rows[5].symbol, rows[5].entry_at)] is False


def test_scaled_control_r_uses_multiplier() -> None:
    row = _decision(0, "-0.5")
    row = v18.InvalidationDecision(
        **{
            **row.__dict__,
            "base_multiplier": "0.5",
        }
    )
    assert v26._scaled_control_r(row) == v26.Decimal("-0.25")


def test_v26_frozen_contract() -> None:
    assert v26.POLICY == "INVALIDATING_POSBOTH_SEVEREBOTH_P2"
    assert v26.SEVERE_DD_R == v26.Decimal("4")
    assert v26.SEVERE_CLASS_BOUNDARY == 0.50
    assert v26.PERSISTENCE_REQUIRED == 2
