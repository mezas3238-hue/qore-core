from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    _metrics,
    _replay,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveDisposition,
)


def _bar(minute: int, high: str, low: str, close: str) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 12, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def _opportunity() -> V49Opportunity:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price="98",
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )


def test_v50_g_target_hit_uses_execution_stop_risk_unit() -> None:
    trade = _replay(
        policy="GEOMETRY_ONLY",
        opportunity=_opportunity(),
        bars=(
            _bar(0, "100.5", "99.8", "100.3"),
            _bar(1, "101.1", "99.9", "101"),
        ),
        stop=Decimal("99.5"),
        target=Decimal("101"),
        disposition=V50CognitiveDisposition.REFINE_TARGET_LADDER,
    )
    assert trade is not None
    assert trade.exit_reason == "TARGET"
    assert Decimal(trade.realized_gross_r) == Decimal("2")
    assert Decimal(trade.planned_reward_r) == Decimal("2")


def test_v50_g_same_bar_stop_target_fails_closed() -> None:
    trade = _replay(
        policy="COGNITIVE_GEOMETRY",
        opportunity=_opportunity(),
        bars=(_bar(0, "101.1", "99.4", "100"),),
        stop=Decimal("99.5"),
        target=Decimal("101"),
        disposition=V50CognitiveDisposition.PASS_TO_COMPETITION,
    )
    assert trade is not None
    assert trade.exit_reason == "STOP"
    assert trade.same_bar_stop_target_ambiguity is True
    assert Decimal(trade.realized_gross_r) == Decimal("-1")


def test_v50_g_cost_stress_is_explicit_r_subtraction() -> None:
    trade = _replay(
        policy="GEOMETRY_ONLY",
        opportunity=_opportunity(),
        bars=(_bar(0, "101.1", "99.8", "101"),),
        stop=Decimal("99.5"),
        target=Decimal("101"),
        disposition=V50CognitiveDisposition.PASS_TO_COMPETITION,
    )
    assert trade is not None
    gross = _metrics((trade,))
    stressed = _metrics((trade,), cost_r=Decimal("0.05"))
    assert Decimal(gross["total_r"]) == Decimal("2")
    assert Decimal(stressed["total_r"]) == Decimal("1.95")
