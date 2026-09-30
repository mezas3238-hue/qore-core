from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_b_sensor_blindspot_engine import (
    SharedBBlindspotKind,
    SharedBObservationRequirement,
    SharedBSensorCoverageFact,
    detect_sensor_blindspots,
)

NOW=datetime(2026,9,30,18,0,tzinfo=UTC)


def _req(
    requirement_id: str,
    family: str,
    horizon: str,
) -> SharedBObservationRequirement:
    return SharedBObservationRequirement(
        requirement_id=requirement_id,
        sensor_family=family,
        horizon=horizon,
        identity_required=True,
        market_hours_required=True,
        data_health_required=True,
        relation_comparability_required=True,
        provenance_refs=(f"req:{requirement_id}",),
    )


def _fact(**overrides: object) -> SharedBSensorCoverageFact:
    values:dict[str,object]={
        "sensor_family":"EQUITY_BREADTH_PROXY",
        "horizon":"M1",
        "observed_at":NOW,
        "evidence_cutoff_at":NOW,
        "sensor_ids":("CTRADER_DEMO:US2000:10012",),
        "provider_available":True,
        "identity_resolved":True,
        "market_hours_resolved":True,
        "data_health_observed":True,
        "relation_comparability_known":True,
        "provenance_refs":("coverage:us2000",),
    }
    values.update(overrides)
    return SharedBSensorCoverageFact(**values)  # type: ignore[arg-type]


def test_complete_coverage_has_no_blindspot() -> None:
    report=detect_sensor_blindspots(
        requirements=(_req("R01","EQUITY_BREADTH_PROXY","M1"),),
        coverage=(_fact(),),
        as_of=NOW,
        coverage_inventory_complete=True,
    )
    assert report.blindspots==()
    assert report.second_order_blindspot_possible is False


def test_absent_family_and_horizon_are_distinct() -> None:
    report=detect_sensor_blindspots(
        requirements=(
            _req("R01","EQUITY_BREADTH_PROXY","M1"),
            _req("R02","EQUITY_BREADTH_PROXY","H1"),
            _req("R03","AGRICULTURE","M1"),
        ),
        coverage=(_fact(),),
        as_of=NOW,
        coverage_inventory_complete=True,
    )
    kinds={x.requirement_id:x.kind for x in report.blindspots}
    assert kinds["R02"] is SharedBBlindspotKind.TIME_HORIZON_ABSENT
    assert kinds["R03"] is SharedBBlindspotKind.SENSOR_FAMILY_ABSENT


def test_known_coverage_defects_materialize_specific_blindspots() -> None:
    report=detect_sensor_blindspots(
        requirements=(_req("R01","EQUITY_BREADTH_PROXY","M1"),),
        coverage=(
            _fact(
                provider_available=False,
                identity_resolved=False,
                market_hours_resolved=False,
                data_health_observed=False,
                relation_comparability_known=False,
            ),
        ),
        as_of=NOW,
        coverage_inventory_complete=True,
    )
    assert {x.kind for x in report.blindspots} == {
        SharedBBlindspotKind.PROVIDER_UNAVAILABLE,
        SharedBBlindspotKind.IDENTITY_UNRESOLVED,
        SharedBBlindspotKind.MARKET_HOURS_UNRESOLVED,
        SharedBBlindspotKind.DATA_HEALTH_NOT_OBSERVED,
        SharedBBlindspotKind.RELATION_COMPARABILITY_UNKNOWN,
    }


def test_incomplete_inventory_preserves_second_order_blindspot() -> None:
    report=detect_sensor_blindspots(
        requirements=(_req("R01","AGRICULTURE","M1"),),
        coverage=(),
        as_of=NOW,
        coverage_inventory_complete=False,
    )
    assert report.second_order_blindspot_possible is True
    assert any(
        item.kind is SharedBBlindspotKind.COVERAGE_INVENTORY_INCOMPLETE
        and item.known_missing is False
        for item in report.blindspots
    )
    missing=next(
        item for item in report.blindspots
        if item.requirement_id=="R01"
    )
    assert missing.second_order_possible is True
    assert missing.known_missing is False


def test_blindspot_report_never_gains_authority() -> None:
    report=detect_sensor_blindspots(
        requirements=(_req("R01","AGRICULTURE","M1"),),
        coverage=(),
        as_of=NOW,
        coverage_inventory_complete=True,
    )
    assert report.productive_authority is False
    assert report.sensor_admission_authority is False
    assert report.relation_authority is False
