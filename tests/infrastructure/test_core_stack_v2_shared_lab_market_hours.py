import pytest

from qore.infrastructure.core_stack_v2.shared_lab_market_hours import SessionState, assess_market_hours


@pytest.mark.parametrize("state", [SessionState.CLOSED, SessionState.HOLIDAY, SessionState.WEEKEND, SessionState.SESSION_BREAK, SessionState.EARLY_CLOSE])
def test_closed_states_reject_provider_open(state: SessionState) -> None:
    assert not assess_market_hours("X", state, True).passed


@pytest.mark.parametrize("state", [SessionState.OPEN, SessionState.PARTIAL, SessionState.OVERNIGHT])
def test_open_states_accept_provider_open(state: SessionState) -> None:
    assert assess_market_hours("X", state, True).passed
