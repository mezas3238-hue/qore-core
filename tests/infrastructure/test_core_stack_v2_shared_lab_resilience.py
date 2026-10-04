from qore.infrastructure.core_stack_v2.shared_lab_data_reality import DegradationClass
from qore.infrastructure.core_stack_v2.shared_lab_resilience import assess_resilience


def test_noncritical_failure_continues_with_higher_uncertainty_and_dependency_notice() -> None:
    receipt = assess_resilience(
        required_sensor_count=2,
        available_required_sensor_count=1,
        alternative_sensor_count=2,
        observability_ratio=0.9,
        base_uncertainty=0.1,
        affected_dependencies=("representation.microstructure",),
    )
    assert receipt.classification is DegradationClass.DEGRADED_BUT_USABLE
    assert receipt.data_plane_continues
    assert receipt.resulting_uncertainty > receipt.base_uncertainty
    assert receipt.affected_dependencies
    assert receipt.passed


def test_critical_total_loss_requires_abstention_and_no_invented_continuation() -> None:
    receipt = assess_resilience(
        required_sensor_count=1,
        available_required_sensor_count=0,
        alternative_sensor_count=0,
        observability_ratio=0.0,
        base_uncertainty=0.1,
        affected_dependencies=("representation.price", "cognition.regime"),
    )
    assert receipt.classification is DegradationClass.ABSTENTION_REQUIRED
    assert receipt.abstention_required
    assert not receipt.data_plane_continues
    assert receipt.passed
