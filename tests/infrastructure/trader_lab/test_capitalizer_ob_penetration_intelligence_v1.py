from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_ob_penetration_intelligence_v1 import (
    M1Bar,
    _PenetrationState,
    _classify,
    _fx_pip_size,
    _overshoot_price,
    _update_state,
)


def _state() -> _PenetrationState:
    return _PenetrationState(
        row_index=0,
        entry_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        session_end=datetime(2026, 1, 1, 16, 0, tzinfo=UTC),
        side="LONG",
        entry=Decimal("99"),
        target=Decimal("110"),
        ob_low=Decimal("96"),
        ob_high=Decimal("99"),
        baseline_risk=Decimal("5"),
        deepest_adverse_price=Decimal("99"),
        max_close_adverse_price=Decimal("99"),
    )


def _bar(
    minute: int,
    *,
    high: str,
    low: str,
    close: str,
) -> M1Bar:
    return M1Bar(
        symbol="NAS100",
        opened_at=datetime(2026, 1, 1, 13, minute, tzinfo=UTC),
        open=Decimal("99"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        digits=2,
    )


def test_overshoot_then_later_target_is_breathing_evidence() -> None:
    state = _state()
    _update_state(state, _bar(0, high="100", low="95.80", close="98"))
    assert _overshoot_price(state) == Decimal("0.20")
    assert state.same_bar_overshoot_target_ambiguity is False
    _update_state(state, _bar(1, high="111", low="98", close="110"))
    assert _classify(state) == "OB_OVERSHOOT_THEN_TARGET"
    assert state.target_reached_at is not None
    assert state.provider_increment == Decimal("0.01")


def test_same_bar_overshoot_and_target_is_ambiguous_not_breathing_proof() -> None:
    state = _state()
    _update_state(state, _bar(0, high="111", low="95.80", close="100"))
    assert state.same_bar_overshoot_target_ambiguity is True
    assert _classify(state) == "OB_OVERSHOOT_TARGET_SAME_BAR_AMBIGUOUS"


def test_ob_break_without_target_does_not_authorize_widening() -> None:
    state = _state()
    _update_state(state, _bar(0, high="100", low="95.50", close="95.75"))
    assert _classify(state) == "OB_BREAK_NO_TARGET"
    assert _overshoot_price(state) == Decimal("0.50")


def test_fx_pip_size_is_only_applied_to_fx() -> None:
    assert _fx_pip_size("EURUSD") == Decimal("0.0001")
    assert _fx_pip_size("USDJPY") == Decimal("0.01")
    assert _fx_pip_size("NAS100") is None
    assert _fx_pip_size("XAUUSD") is None
