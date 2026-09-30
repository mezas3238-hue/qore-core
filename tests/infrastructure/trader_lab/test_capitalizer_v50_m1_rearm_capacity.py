from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_capacity import (
    V50RearmAttempt,
    _capacity_breakdown,
    _portfolio_ready,
    _thesis_intact_until,
)


def test_rearm_attempt_is_pre_economic_and_does_not_consume_slot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    attempt = V50RearmAttempt(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price=str(Decimal("99")),
        trigger_confirmed_at=(at + timedelta(minutes=5)).isoformat(),
        trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
        attempt_index=2,
        geometry_decision="READY",
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_ready=True,
        cognitive_geometry_ready=True,
    )
    assert attempt.attempt_index == 2
    assert attempt.slot_consumed_during_wait is False
    assert attempt.stop_relaxed is False
    assert attempt.outcome_used is False
    assert attempt.economics_used is False
    assert attempt.fresh_holdout_used is False


def test_v49_opportunity_contract_remains_pre_economic_for_rearm_payload() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    row = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=(at + timedelta(minutes=5)).isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    assert row.outcome_used is False
    assert row.economics_used is False
    assert row.daily_used is False
    assert row.h4_used is False


def _m1_bar(
    minute: int,
    *,
    high: str,
    low: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 12, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("100"),
        volume=1,
        digits=2,
    )


def test_rearm_requires_m15_thesis_to_remain_intact_through_trigger_close() -> None:
    bars = (
        _m1_bar(0, high="100.2", low="99.8"),
        _m1_bar(1, high="100.1", low="98.9"),
        _m1_bar(2, high="100.4", low="99.4"),
    )
    opened = tuple(item.opened_at for item in bars)
    assert _thesis_intact_until(
        bars,
        opened,
        setup_confirmed_at=bars[0].opened_at,
        trigger_confirmed_at=bars[-1].closed_at,
        protected_swing_price=Decimal("99"),
        direction=CapitalizerSourceDirection.BULLISH,
    ) is False


def test_rearm_allows_intact_m15_thesis() -> None:
    bars = (
        _m1_bar(0, high="100.2", low="99.8"),
        _m1_bar(1, high="100.1", low="99.2"),
        _m1_bar(2, high="100.4", low="99.4"),
    )
    opened = tuple(item.opened_at for item in bars)
    assert _thesis_intact_until(
        bars,
        opened,
        setup_confirmed_at=bars[0].opened_at,
        trigger_confirmed_at=bars[-1].closed_at,
        protected_swing_price=Decimal("99"),
        direction=CapitalizerSourceDirection.BULLISH,
    ) is True


def _ready_attempt(
    *,
    symbol: str,
    minute: int,
    attempt_index: int,
    cognitive_ready: bool = True,
    setup_minute: int = 0,
) -> V50RearmAttempt:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    setup_at = at + timedelta(minutes=setup_minute)
    return V50RearmAttempt(
        symbol=symbol,
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=setup_at.isoformat(),
        m15_protected_swing_price="99",
        trigger_confirmed_at=(at + timedelta(minutes=minute)).isoformat(),
        trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
        attempt_index=attempt_index,
        geometry_decision="READY",
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_ready=True,
        cognitive_geometry_ready=cognitive_ready,
    )


def test_rearm_portfolio_capacity_applies_max3_chronologically() -> None:
    rows = (
        _ready_attempt(
            symbol="EURUSD", minute=5, attempt_index=2, setup_minute=0
        ),
        _ready_attempt(
            symbol="GBPUSD", minute=6, attempt_index=1, setup_minute=1
        ),
        _ready_attempt(
            symbol="EURUSD", minute=7, attempt_index=1, setup_minute=2
        ),
        _ready_attempt(
            symbol="GBPUSD", minute=8, attempt_index=2, setup_minute=3
        ),
    )
    selected = _portfolio_ready(rows, cognitive=False)
    assert len(selected) == 3
    assert tuple(item.trigger_confirmed_at for item in selected) == tuple(
        item.trigger_confirmed_at for item in rows[:3]
    )
    breakdown = _capacity_breakdown(selected)
    assert breakdown["trades_after_max3"] == 3
    assert breakdown["recovered_after_rearm"] == 1
    assert breakdown["first_attempt_ready"] == 2


def test_cognitive_rearm_capacity_excludes_non_cognitive_ready_geometry() -> None:
    rows = (
        _ready_attempt(symbol="EURUSD", minute=5, attempt_index=1),
        _ready_attempt(
            symbol="GBPUSD",
            minute=6,
            attempt_index=2,
            cognitive_ready=False,
        ),
    )
    assert len(_portfolio_ready(rows, cognitive=False)) == 2
    cognitive = _portfolio_ready(rows, cognitive=True)
    assert len(cognitive) == 1
    assert cognitive[0].symbol == "EURUSD"


def test_geometry_portfolio_executes_parent_m15_setup_only_once() -> None:
    first_ready = _ready_attempt(
        symbol="GBPUSD",
        minute=5,
        attempt_index=1,
        cognitive_ready=False,
    )
    later_ready = _ready_attempt(
        symbol="GBPUSD",
        minute=9,
        attempt_index=2,
        cognitive_ready=True,
    )
    selected = _portfolio_ready((first_ready, later_ready), cognitive=False)
    assert selected == (first_ready,)
    breakdown = _capacity_breakdown(selected)
    assert breakdown["trades_after_max3"] == 1
    assert breakdown["first_attempt_ready"] == 1
    assert breakdown["recovered_after_rearm"] == 0


def test_cognition_blocked_geometry_never_enters_cognitive_portfolio() -> None:
    blocked = _ready_attempt(
        symbol="GBPUSD",
        minute=5,
        attempt_index=1,
        cognitive_ready=False,
    )
    recovered = _ready_attempt(
        symbol="GBPUSD",
        minute=9,
        attempt_index=2,
        cognitive_ready=True,
    )
    selected = _portfolio_ready((blocked, recovered), cognitive=True)
    assert selected == (recovered,)
    breakdown = _capacity_breakdown(selected)
    assert breakdown["trades_after_max3"] == 1
    assert breakdown["recovered_after_rearm"] == 1
    assert breakdown["first_attempt_ready"] == 0
