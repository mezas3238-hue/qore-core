from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.core_broker_blindspot_cognition import (
    ExternalObservabilityEvidence,
    SystemBlindspotState,
    build_core_broker_blindspot_situation,
)
from qore.infrastructure.core_stack_v2.second_order_blindspot_cognition import (
    SharedBlindspotEvidence,
    assess_second_order_blindspot,
)


def _external(**overrides):
    values = {
        "source_run_id": 36763268609,
        "artifact_id": 11119388121,
        "core_observability_contract_validated": True,
        "broker_observability_contract_validated": True,
        "sensor_blindspot_contract_validated": True,
        "unknown_world_contract_validated": True,
        "runtime_core_broker_replication_complete": False,
        "second_order_inventory_complete": False,
        "known_gap_refs": (
            "gap:agricultural-provider-candidates-zero",
            "gap:calendar-comparability-unresolved",
            "gap:canonical-identity-unresolved",
        ),
    }
    values.update(overrides)
    return ExternalObservabilityEvidence(**values)


def _cognition():
    now = datetime(2026, 9, 30, 19, 30, tzinfo=UTC)
    evidence = SharedBlindspotEvidence(
        evidence_id="mc28-canary",
        observed_at=now,
        evidence_cutoff_at=now,
        domain="CORE_BROKER_SENSOR_FIELD",
        prediction_error_bps=8000,
        uncertainty_bps=8000,
        data_health_bps=9800,
        known_sensor_coverage_bps=2000,
        ontology_fit_bps=2000,
        recurrence_count=4,
        downstream_importance_bps=8000,
        provenance_refs=("mc28:test",),
    )
    return assess_second_order_blindspot(evidence)


def test_open_runtime_replication_keeps_mc28_incomplete() -> None:
    situation = build_core_broker_blindspot_situation(_external(), _cognition())
    assert situation.state is SystemBlindspotState.OBSERVABILITY_INCOMPLETE
    assert situation.broker_mutation_authority is False
    assert situation.execution_authority is False


def test_second_order_priority_only_after_source_completeness() -> None:
    external = _external(
        runtime_core_broker_replication_complete=True,
        second_order_inventory_complete=True,
    )
    situation = build_core_broker_blindspot_situation(external, _cognition())
    assert situation.state is SystemBlindspotState.SECOND_ORDER_RESEARCH_PRIORITY
