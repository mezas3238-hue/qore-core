from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_h1_context_state_v49 import (
    V49H1BiasSignal,
    V49H1StateEndReason,
    build_h1_context_states,
    state_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_one_h1_signal_persists_until_session_end_and_is_not_consumed() -> None:
    start = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=8)
    signal = V49H1BiasSignal(
        confirmed_at=start + timedelta(hours=1),
        direction=CapitalizerSourceDirection.BULLISH,
        basis_id="H1_C2",
    )
    states = build_h1_context_states(
        (signal,),
        session=CapitalizerSession.ASIA,
        session_start=start,
        session_end=end,
    )
    assert len(states) == 1
    state = states[0]
    assert state.active_until == end
    assert state.end_reason is V49H1StateEndReason.SESSION_END
    assert state.consumed_after_trade is False
    assert state_at(states, start + timedelta(hours=2)) is state
    assert state_at(states, start + timedelta(hours=6)) is state


def test_opposite_h1_signal_invalidates_prior_state_and_starts_new_state() -> None:
    start = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    end = start + timedelta(hours=8)
    bullish = V49H1BiasSignal(
        confirmed_at=start + timedelta(hours=1),
        direction=CapitalizerSourceDirection.BULLISH,
        basis_id="H1_BULL",
    )
    bearish = V49H1BiasSignal(
        confirmed_at=start + timedelta(hours=4),
        direction=CapitalizerSourceDirection.BEARISH,
        basis_id="H1_BEAR",
    )
    states = build_h1_context_states(
        (bullish, bearish),
        session=CapitalizerSession.LONDON,
        session_start=start,
        session_end=end,
    )
    assert len(states) == 2
    assert states[0].active_until == bearish.confirmed_at
    assert states[0].end_reason is V49H1StateEndReason.OPPOSITE_H1_SIGNAL
    assert states[1].active_until == end


def test_repeated_same_direction_signal_does_not_create_duplicate_state() -> None:
    start = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)
    end = start + timedelta(hours=7)
    signals = (
        V49H1BiasSignal(
            confirmed_at=start + timedelta(hours=1),
            direction=CapitalizerSourceDirection.BULLISH,
            basis_id="A",
        ),
        V49H1BiasSignal(
            confirmed_at=start + timedelta(hours=2),
            direction=CapitalizerSourceDirection.BULLISH,
            basis_id="B",
        ),
    )
    states = build_h1_context_states(
        signals,
        session=CapitalizerSession.NEW_YORK,
        session_start=start,
        session_end=end,
    )
    assert len(states) == 1
    assert states[0].established_by == "A"



def test_last_pre_session_h1_signal_is_inherited_without_future_leakage() -> None:
    start = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)
    end = start + timedelta(hours=7)
    prior = V49H1BiasSignal(
        confirmed_at=start - timedelta(hours=1),
        direction=CapitalizerSourceDirection.BEARISH,
        basis_id="PRE_SESSION_H1",
    )
    states = build_h1_context_states(
        (prior,),
        session=CapitalizerSession.NEW_YORK,
        session_start=start,
        session_end=end,
    )
    assert len(states) == 1
    assert states[0].active_from == start
    assert states[0].direction is CapitalizerSourceDirection.BEARISH
    assert states[0].established_by == "SESSION_INHERITED:PRE_SESSION_H1"
