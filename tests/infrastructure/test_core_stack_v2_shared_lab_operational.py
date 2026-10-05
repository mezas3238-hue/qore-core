from qore.infrastructure.core_stack_v2.shared_lab_operational import (
    DegradedDisposition,
    DegradedModeReceipt,
    InformationValueReceipt,
    ResourceLatencyReceipt,
    assess_operational_reality,
)


def test_slow_cognition_fails_deadline_even_if_logically_correct():
    latency = ResourceLatencyReceipt(
        "MC18",
        latency_p50_ms=50,
        latency_p95_ms=500,
        latency_p99_ms=25000,
        decision_deadline_ms=1000,
        peak_memory_mb=100,
        cpu_time_ms=500,
        io_bytes=1000,
    )
    assert latency.deadline_pass is False


def test_expensive_information_that_changes_nothing_is_not_useful():
    info = InformationValueReceipt(
        "MC18",
        observations=100,
        decision_changes=0,
        uncertainty_reductions=0,
        avoided_false_opportunities=0,
        preserved_winners=0,
        incremental_information_gain=0.0,
        incremental_value=0.0,
        acquisition_cost_units=1000,
    )
    assert info.useful is False


def test_noncritical_failure_can_degrade_with_explicit_uncertainty():
    receipt = DegradedModeReceipt(
        capability_id="MC18",
        failed_dependency_ids=("SENSOR_A",),
        critical_dependency_failed=False,
        uncertainty_increased=True,
        affected_consumers_notified=True,
        disabled_capability_ids=("OPTIONAL_SUBHEAD",),
        disposition=DegradedDisposition.DEGRADED_USABLE,
    )
    assert receipt.passed is True


def test_critical_failure_cannot_continue_as_degraded_usable():
    receipt = DegradedModeReceipt(
        capability_id="MC18",
        failed_dependency_ids=("CAUSAL_CRITICAL",),
        critical_dependency_failed=True,
        uncertainty_increased=True,
        affected_consumers_notified=True,
        disabled_capability_ids=("MC18",),
        disposition=DegradedDisposition.DEGRADED_USABLE,
    )
    assert receipt.passed is False


def test_operational_reality_requires_all_three_dimensions():
    latency = ResourceLatencyReceipt("MC18", 10, 20, 30, 100, 50, 10, 1000)
    info = InformationValueReceipt("MC18", 100, 5, 10, 2, 1, 0.1, 0.2, 5)
    degraded = DegradedModeReceipt(
        "MC18",
        (),
        False,
        False,
        False,
        (),
        DegradedDisposition.FULL,
    )
    result = assess_operational_reality(
        latency=latency,
        information_value=info,
        degraded_mode=degraded,
    )
    assert result.operationally_usable is True
