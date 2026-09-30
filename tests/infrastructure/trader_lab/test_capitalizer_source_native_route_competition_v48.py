from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_source_native_route_competition_v48 import (
    V48AdmittedRouteOpportunity,
    compete_session_day,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def _row(index: int, route: V48RouteId) -> V48AdmittedRouteOpportunity:
    return V48AdmittedRouteOpportunity(
        opportunity_id=f"o{index}",
        route_id=route,
        symbol=("EURUSD", "GBPUSD", "USDJPY", "AUDJPY")[index],
        session="LONDON",
        operating_date="2026-01-02",
        admitted_at=datetime(2026, 1, 2, 8, tzinfo=UTC) + timedelta(minutes=index),
    )


def test_first_three_source_complete_routes_win_max3_chronologically() -> None:
    rows = (
        _row(0, V48RouteId.TTRADES_LONDON_DAILY_4H_15M),
        _row(1, V48RouteId.TTRADES_FAILURE_TO_MANIPULATE),
        _row(2, V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1),
        _row(3, V48RouteId.TTRADES_FAILURE_TO_MANIPULATE),
    )

    result = compete_session_day(rows)
    assert tuple(item.opportunity_id for item in result.selected) == ("o0", "o1", "o2")
    assert tuple(item.opportunity_id for item in result.displaced_by_max3) == ("o3",)
    assert result.outcome_used is False
    assert result.route_preference_used is False
    assert result.numeric_score_used is False


def test_input_order_cannot_change_chronological_selection() -> None:
    rows = (
        _row(3, V48RouteId.TTRADES_FAILURE_TO_MANIPULATE),
        _row(1, V48RouteId.TTRADES_FAILURE_TO_MANIPULATE),
        _row(0, V48RouteId.TTRADES_LONDON_DAILY_4H_15M),
        _row(2, V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1),
    )
    result = compete_session_day(rows)
    assert tuple(item.opportunity_id for item in result.selected) == ("o0", "o1", "o2")


def test_mixed_session_day_bucket_fails_closed() -> None:
    row = _row(0, V48RouteId.TTRADES_LONDON_DAILY_4H_15M)
    other = V48AdmittedRouteOpportunity(
        opportunity_id="other",
        route_id=V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-02",
        admitted_at=datetime(2026, 1, 2, 14, 30, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="one session/day"):
        compete_session_day((row, other))
