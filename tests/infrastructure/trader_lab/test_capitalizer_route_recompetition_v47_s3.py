from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_route_recompetition_v47_s3 as s3,
)


def _row(
    symbol: str,
    route: str,
    entry_at: str,
    *,
    identity: str | None = None,
) -> s3.RouteCandidate:
    return s3.RouteCandidate(
        source_identity=identity or route,
        period="development",
        symbol=symbol,
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        route=route,
        entry_at=entry_at,
        entry_price="100",
        stop_price="99",
        target_price="103",
        entry_mode="FVG_CE_50",
        exact_provider_tick_fill=True,
        official_v46_adapter_passed=True,
    )


def test_max3_recompetes_routes_by_time_not_route_priority() -> None:
    rows = (
        _row(
            "GBPUSD",
            "FRACTAL_SCALP_CONTINUATION",
            "2026-01-05T08:04:00+00:00",
        ),
        _row(
            "EURUSD",
            "FAILURE_TO_MANIPULATE_CONTINUATION",
            "2026-01-05T08:01:00+00:00",
        ),
        _row(
            "GBPUSD",
            "FAILURE_TO_MANIPULATE_CONTINUATION",
            "2026-01-05T08:03:00+00:00",
        ),
        _row(
            "EURUSD",
            "FRACTAL_SCALP_CONTINUATION",
            "2026-01-05T08:02:00+00:00",
        ),
    )

    result = s3.select_max3_across_routes(rows)

    assert [row.entry_at for row in result.selected] == [
        "2026-01-05T08:01:00+00:00",
        "2026-01-05T08:02:00+00:00",
        "2026-01-05T08:03:00+00:00",
    ]
    assert result.route_priority_used is False
    assert result.outcome_used_for_selection is False


def test_exact_duplicate_recompact_does_not_merge_cross_route_candidates() -> None:
    fractal = _row(
        "EURUSD",
        "FRACTAL_SCALP_CONTINUATION",
        "2026-01-05T08:01:00+00:00",
    )
    ftm = _row(
        "EURUSD",
        "FAILURE_TO_MANIPULATE_CONTINUATION",
        "2026-01-05T08:01:00+00:00",
    )

    compacted = s3.recompact_exact_duplicates((fractal, fractal, ftm))

    assert len(compacted) == 2
    assert {row.route for row in compacted} == {
        "FRACTAL_SCALP_CONTINUATION",
        "FAILURE_TO_MANIPULATE_CONTINUATION",
    }


def test_route_counts_are_explicit() -> None:
    rows = (
        _row(
            "EURUSD",
            "FRACTAL_SCALP_CONTINUATION",
            "2026-01-05T08:01:00+00:00",
        ),
        _row(
            "GBPUSD",
            "FAILURE_TO_MANIPULATE_CONTINUATION",
            "2026-01-05T08:02:00+00:00",
        ),
    )
    assert s3.entrant_counts_by_route(rows) == {
        "FRACTAL_SCALP_CONTINUATION": 1,
        "FAILURE_TO_MANIPULATE_CONTINUATION": 1,
    }
