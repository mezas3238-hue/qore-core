from qore.infrastructure.core_stack_v2.shared_lab_resilience import (
    DependencyFailureReceipt,
    ResilienceDisposition,
    assess_resilience,
)


def test_noncritical_dependency_can_be_reconstructed():
    receipt = DependencyFailureReceipt(
        "MC18",
        "SENSOR_A",
        False,
        ("SENSOR_B", "SENSOR_C"),
        0.97,
        True,
        True,
        ResilienceDisposition.FULLY_RECONSTRUCTED,
    )
    assert receipt.passed is True


def test_hidden_single_point_of_failure_is_detected():
    receipt = DependencyFailureReceipt(
        "MC18",
        "UNKNOWN_DEPENDENCY",
        False,
        (),
        0.0,
        True,
        True,
        ResilienceDisposition.FAIL_CLOSED,
    )
    result = assess_resilience((receipt,))
    assert result.resilience_proven is False
