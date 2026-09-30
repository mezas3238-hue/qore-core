from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_two_route_population_v47_s2d as s2d,
)


def _row(
    *,
    stream: str,
    route: str,
    symbol: str,
    entry_at: str,
) -> s2d.S2DPopulationRow:
    return s2d.S2DPopulationRow(
        identity=s2d.IDENTITY,
        source_stream=stream,
        source_identity="SRC",
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
        target_kind="HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE",
        source_run_id=1,
        source_sha="a" * 40,
    )


def test_exact_cross_route_collision_fails_closed() -> None:
    rows = (
        _row(
            stream="FRACTAL",
            route="FRACTAL_SCALP_CONTINUATION",
            symbol="EURUSD",
            entry_at="2026-01-05T08:00:00+00:00",
        ),
        _row(
            stream="FTM",
            route="FAILURE_TO_MANIPULATE_CONTINUATION",
            symbol="EURUSD",
            entry_at="2026-01-05T08:00:00+00:00",
        ),
        _row(
            stream="FTM",
            route="FAILURE_TO_MANIPULATE_CONTINUATION",
            symbol="GBPUSD",
            entry_at="2026-01-05T08:01:00+00:00",
        ),
    )

    surviving, collisions = s2d.fail_closed_route_collisions(rows)

    assert len(collisions) == 2
    assert len(surviving) == 1
    assert surviving[0].symbol == "GBPUSD"


def test_combined_max3_happens_after_route_union() -> None:
    rows = (
        _row(
            stream="FTM",
            route="FAILURE_TO_MANIPULATE_CONTINUATION",
            symbol="GBPUSD",
            entry_at="2026-01-05T08:04:00+00:00",
        ),
        _row(
            stream="FRACTAL",
            route="FRACTAL_SCALP_CONTINUATION",
            symbol="EURUSD",
            entry_at="2026-01-05T08:01:00+00:00",
        ),
        _row(
            stream="FTM",
            route="FAILURE_TO_MANIPULATE_CONTINUATION",
            symbol="EURUSD",
            entry_at="2026-01-05T08:02:00+00:00",
        ),
        _row(
            stream="FRACTAL",
            route="FRACTAL_SCALP_CONTINUATION",
            symbol="GBPUSD",
            entry_at="2026-01-05T08:03:00+00:00",
        ),
    )

    selected = s2d.select_combined_max3(rows)

    assert len(selected) == 3
    assert [row.entry_at for row in selected] == [
        "2026-01-05T08:01:00+00:00",
        "2026-01-05T08:02:00+00:00",
        "2026-01-05T08:03:00+00:00",
    ]
    assert {row.source_stream for row in selected} == {"FRACTAL", "FTM"}
