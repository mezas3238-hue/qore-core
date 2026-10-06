from qore.infrastructure.cibo_portfolio_competition_surface_sensor import (
    measure_portfolio_competition_surface,
)


def _row(
    *,
    epoch: str,
    fp: str,
    at: str,
    ev: str = "1",
    selected: bool = False,
    deployed: str | None = None,
    released: str | None = None,
) -> dict:
    return {
        "decision_epoch_id": epoch,
        "signal_fingerprint": fp,
        "market_decision_at": at,
        "expectation": {"expected_net_value_usd": ev},
        "context_quality": {"disposition": "ALLOW"},
        "allocation": {"selected_by_cibo_policy": selected},
        "settlement": (
            {
                "capital_deployed_at": deployed,
                "capital_released_at": released,
            }
            if deployed and released
            else None
        ),
    }


def test_portfolio_surface_detects_open_position_competition() -> None:
    trace = {
        "opportunities": [
            _row(
                epoch="e0",
                fp="open-position",
                at="2026-10-04T10:00:00+00:00",
                selected=True,
                deployed="2026-10-04T10:00:00+00:00",
                released="2026-10-04T11:00:00+00:00",
            ),
            _row(
                epoch="e1",
                fp="new-a",
                at="2026-10-04T10:30:00+00:00",
            ),
        ]
    }

    report = measure_portfolio_competition_surface(trace)

    assert report.positive_context_allowed_count == 2
    assert report.open_position_competition_count == 1
    assert report.same_epoch_competition_count == 0
    assert report.maximum_open_positions_at_decision == 1


def test_portfolio_surface_detects_same_epoch_competition() -> None:
    trace = {
        "opportunities": [
            _row(
                epoch="e1",
                fp="a",
                at="2026-10-04T10:30:00+00:00",
            ),
            _row(
                epoch="e1",
                fp="b",
                at="2026-10-04T10:30:00+00:00",
            ),
        ]
    }

    report = measure_portfolio_competition_surface(trace)

    assert report.positive_context_allowed_count == 2
    assert report.same_epoch_competition_count == 2
    assert report.any_competition_rate == 1
    assert report.maximum_simultaneous_new_opportunities == 2
