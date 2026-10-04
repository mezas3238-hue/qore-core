from decimal import Decimal

from qore.infrastructure.cibo_t14_redeployment_sensor import (
    measure_t14_redeployment,
)


def _release(at: str, *, risk: str = "1", margin: str = "2") -> dict:
    return {
        "action": "REDUCE",
        "decision_at": at,
        "released_stop_risk_usd": risk,
        "released_margin_usd": margin,
        "outcome_used": False,
    }


def _opportunity(
    at: str,
    *,
    risk: str = "1",
    margin: str = "2",
    ev: str = "1",
    selected: bool = False,
    context: str = "ALLOW",
) -> dict:
    return {
        "market_decision_at": at,
        "expectation": {"expected_net_value_usd": ev},
        "context_quality": {"disposition": context},
        "cma": {
            "candidate_stop_risk_usd": risk,
            "candidate_margin_usd": margin,
        },
        "allocation": {
            "selected_by_cibo_policy": selected,
        },
    }


def test_t14_sensor_separates_natural_wait_from_allocator_wait() -> None:
    report = measure_t14_redeployment(
        t14_decisions=[
            _release("2026-10-04T10:00:00+00:00"),
        ],
        decision_trace={
            "opportunities": [
                _opportunity(
                    "2026-10-04T10:30:00+00:00",
                    selected=False,
                ),
                _opportunity(
                    "2026-10-04T10:45:00+00:00",
                    selected=True,
                ),
            ]
        },
    )

    assert report.changed_release_count == 1
    assert report.natural_opportunity_wait_median_minutes == Decimal("30.0")
    assert report.allocator_wait_median_minutes == Decimal("15.0")
    assert report.fitting_coverage == Decimal("1")
    assert report.first_fit_selected_immediately_rate == Decimal("0")


def test_t14_sensor_does_not_blame_allocator_when_no_future_fit_exists() -> None:
    report = measure_t14_redeployment(
        t14_decisions=[
            _release(
                "2026-10-04T10:00:00+00:00",
                risk="0.5",
                margin="1",
            ),
        ],
        decision_trace={
            "opportunities": [
                _opportunity(
                    "2026-10-04T10:30:00+00:00",
                    risk="2",
                    margin="5",
                    selected=True,
                ),
            ]
        },
    )

    assert report.no_later_fit_count == 1
    assert report.later_fitting_opportunity_count == 0
    assert report.allocator_wait_median_minutes == Decimal("0")
    assert report.fitting_coverage == Decimal("0")


def test_t14_sensor_immediate_first_fit_selection_is_full_allocator_efficiency() -> None:
    report = measure_t14_redeployment(
        t14_decisions=[
            _release("2026-10-04T10:00:00+00:00"),
            _release("2026-10-04T11:00:00+00:00"),
        ],
        decision_trace={
            "opportunities": [
                _opportunity(
                    "2026-10-04T10:05:00+00:00",
                    selected=True,
                ),
                _opportunity(
                    "2026-10-04T11:05:00+00:00",
                    selected=True,
                ),
            ]
        },
    )

    assert report.later_selected_fitting_count == 2
    assert report.first_fit_selected_immediately_rate == Decimal("1")
    assert report.allocator_wait_median_minutes == Decimal("0")
