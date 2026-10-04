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


def test_registry_has_broad_cross_layer_tool_catalog():
    registry = default_shared_lab_registry()
    families = {spec.family for spec in registry.list_tools()}
    assert len(families) >= 45
    assert ToolFamily.COUNTERFACTUAL_WORLD in families
    assert ToolFamily.MONTE_CARLO in families
    assert ToolFamily.WALK_FORWARD in families
    assert ToolFamily.AUTHORITY_ISOLATION in families
    assert ToolFamily.REDUNDANCY_RESILIENCE in families


def test_parameterized_family_can_generate_thousands_of_probes():
    registry = default_shared_lab_registry()
    cases = registry.expand(
        "timestamp-perturbation",
        {
            "sensor": tuple(f"S{index:03d}" for index in range(10)),
            "asset": ("EURUSD", "NAS100", "XAUUSD", "BTCUSD", "USDCAD"),
            "offset": ("+1ms", "+10ms", "+1s", "+30s", "DST_BOUNDARY"),
            "regime": ("CALM", "TREND", "SHOCK", "TRANSITION"),
        },
    )
    assert len(cases) == 1000
    assert len({case.case_id for case in cases}) == 1000
