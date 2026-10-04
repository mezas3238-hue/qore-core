from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.second_order_blindspot_cognition import (
    SharedBlindspotClass,
    SharedBlindspotEvidence,
    assess_second_order_blindspot,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)

NOW = datetime(2026, 9, 30, 16, 30, tzinfo=UTC)


def _evidence() -> SharedBlindspotEvidence:
    return SharedBlindspotEvidence(
        evidence_id="blindspot-001",
        observed_at=NOW,
        evidence_cutoff_at=NOW,
        domain="CROSS_ASSET_TRANSITION",
        prediction_error_bps=8_500,
        uncertainty_bps=8_000,
        data_health_bps=9_900,
        known_sensor_coverage_bps=2_000,
        ontology_fit_bps=2_500,
        recurrence_count=5,
        downstream_importance_bps=7_500,
        provenance_refs=("x12:test-source",),
    )


def test_recurrent_uninstrumented_surprise_becomes_second_order_candidate() -> None:
    result = assess_second_order_blindspot(_evidence())
    assert result.blindspot_class is SharedBlindspotClass.SECOND_ORDER_UNKNOWN_UNKNOWN
    assert result.research_priority_bps > 0
    assert result.sensor_acquisition_authority is False
    assert result.ontology_mutation_authority is False
    assert result.execution_authority is False
    assert len(result.fingerprint()) == 64


def test_data_corruption_is_not_mislabeled_unknown_unknown() -> None:
    result = assess_second_order_blindspot(
        replace(_evidence(), data_health_bps=7_000)
    )
    assert result.blindspot_class is SharedBlindspotClass.DATA_CORRUPTION
    assert result.research_priority_bps == 0


def test_known_gap_remains_distinct_from_unknown_unknown() -> None:
    result = assess_second_order_blindspot(
        replace(
            _evidence(),
            prediction_error_bps=4_000,
            uncertainty_bps=4_000,
            recurrence_count=1,
        )
    )
    assert result.blindspot_class is SharedBlindspotClass.KNOWN_OBSERVABILITY_GAP


def test_future_evidence_is_rejected() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="future evidence",
    ):
        replace(_evidence(), evidence_cutoff_at=NOW + timedelta(seconds=1))
