from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab_data_authority_firewall import inspect_authority_firewall


OWNED_MODULES = (
    "shared_lab_golden_traces.py",
    "shared_lab_data_reality.py",
    "shared_lab_temporal_harness.py",
    "shared_lab_sensor_harness.py",
    "shared_lab_provider_harness.py",
    "shared_lab_identity_harness.py",
    "shared_lab_market_hours.py",
    "shared_lab_data_l10.py",
    "shared_lab_data_pipeline.py",
    "shared_lab_provider_scenarios.py",
    "shared_lab_temporal_context.py",
    "shared_lab_data_assessment.py",
    "shared_lab_market_calendar.py",
    "shared_lab_data_exam.py",
    "shared_lab_data_provenance.py",
    "shared_lab_data_authority_firewall.py",
    "shared_lab_universe_completeness.py",
    "shared_lab_resilience.py",
    "shared_lab_data_tool_matrix.py",
)


def test_entire_data_reality_lane_has_no_productive_or_outcome_aware_import_path() -> None:
    root = Path("src/qore/infrastructure/core_stack_v2")
    violations = []
    for name in OWNED_MODULES:
        source = (root / name).read_text()
        violations.extend((name, item) for item in inspect_authority_firewall(source))
    assert violations == []


def test_firewall_detects_productive_authority_and_outcome_aware_shapes() -> None:
    bad = """
from qore.infrastructure.execution import Broker
future_pnl = 10
open_order()
"""
    violations = inspect_authority_firewall(bad)
    kinds = {item.kind for item in violations}
    assert "FORBIDDEN_IMPORT" in kinds
    assert "OUTCOME_AWARE_IDENTIFIER" in kinds
    assert "PRODUCTIVE_CALL" in kinds
