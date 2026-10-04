from qore.infrastructure.core_stack_v2.shared_lab import LabFault
from qore.infrastructure.core_stack_v2.shared_lab_tools import (
    ToolFamily,
    default_shared_lab_registry,
    registry_fingerprint,
    validate_l10_tool_coverage,
)


def test_registry_expands_one_family_into_many_probes():
    registry = default_shared_lab_registry()
    cases = registry.expand(
        "timestamp-perturbation",
        {
            "sensor": ("S001", "S002"),
            "asset": ("EURUSD", "NAS100"),
            "offset": ("+1ms", "+1s", "DST_BOUNDARY"),
            "regime": ("CALM", "SHOCK"),
        },
    )
    assert len(cases) == 24
    assert len({case.case_id for case in cases}) == 24


def test_l10_fault_classes_have_tool_family_coverage():
    registry = default_shared_lab_registry()
    assert validate_l10_tool_coverage(registry) == ()
    assert set(LabFault)


def test_registry_contains_cross_layer_failure_families():
    families = {spec.family for spec in default_shared_lab_registry().list_tools()}
    assert ToolFamily.TIMESTAMP_PERTURBATION in families
    assert ToolFamily.SENSOR_FAILURE_INJECTOR in families
    assert ToolFamily.CABLE_LINEAGE_BREAK in families
    assert ToolFamily.LEAKAGE_INJECTION in families
    assert ToolFamily.COGNITIVE_MUTATION in families


def test_registry_fingerprint_is_deterministic():
    first = registry_fingerprint(default_shared_lab_registry())
    second = registry_fingerprint(default_shared_lab_registry())
    assert first == second
    assert len(first) == 64
