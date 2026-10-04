from qore.infrastructure.core_stack_v2.shared_lab_data_tool_matrix import build_data_tool_matrix
from qore.infrastructure.core_stack_v2.shared_lab_tools import ToolFamily, default_shared_lab_registry


def test_all_four_data_reality_tool_families_are_materialized_from_shared_registry() -> None:
    matrix = build_data_tool_matrix(
        default_shared_lab_registry(),
        sensors=("price", "spread", "volume"),
        assets=("EURUSD", "XAUUSD", "NAS100", "BTCUSD"),
        regimes=("normal", "stress", "closed"),
    )
    assert set(matrix.covered_families) == {
        ToolFamily.TIMESTAMP_PERTURBATION,
        ToolFamily.SENSOR_FAILURE_INJECTOR,
        ToolFamily.PROVIDER_DEGRADATION,
        ToolFamily.IDENTITY_MUTATION,
    }
    assert matrix.total_cases > 300
    assert matrix.timestamp_cases
    assert matrix.sensor_cases
    assert matrix.provider_cases
    assert matrix.identity_cases
