from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_route_feasibility_ledger_v48 import (
    V48FeasibilityStatus,
    V48RouteOpportunity,
    build_route_feasibility_report,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def test_feasibility_ledger_counts_only_source_complete_population() -> None:
    rows = (
        V48RouteOpportunity(
            "a",
            V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
            "EURUSD",
            "LONDON",
            datetime(2025, 1, 2, 10, tzinfo=UTC),
            V48FeasibilityStatus.SOURCE_COMPLETE,
        ),
        V48RouteOpportunity(
            "b",
            V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
            "GBPUSD",
            "LONDON",
            datetime(2025, 1, 2, 11, tzinfo=UTC),
            V48FeasibilityStatus.SOURCE_INCOMPLETE,
            ("CONTINUATION_STRUCTURE_CONFIRMED",),
        ),
    )

    report = build_route_feasibility_report(rows)
    assert report.opportunities_seen == 2
    assert report.source_complete == 1
    assert report.source_incomplete == 1
    assert report.by_market == (("EURUSD", 1),)
    assert report.by_year == ((2025, 1),)
    assert report.missing_facts == (("CONTINUATION_STRUCTURE_CONFIRMED", 1),)
    assert report.outcome_used is False
    assert report.fresh_holdout_used is False
    assert report.density_gate_applied is False
    assert report.economics_calculated is False
