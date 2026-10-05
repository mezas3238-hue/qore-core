import pytest
from qore.infrastructure.core_stack_v2.shared_lab_temporal_harness import TemporalFailure, assess_sequence, assess_temporal


@pytest.mark.parametrize("delta", [1_000_000, 10_000_000, 1_000_000_000, 30_000_000_000, 300_000_000_000])
def test_allowed_positive_offsets_before_decision(delta: int) -> None:
    receipt = assess_temporal(datum_id="x", observed_at_ns=0, available_at_ns=delta, decision_at_ns=delta, consumed_at_ns=delta + 1)
    assert receipt.passed


def test_future_evidence_fails_automatically() -> None:
    receipt = assess_temporal(datum_id="leak", observed_at_ns=0, available_at_ns=11, decision_at_ns=10, consumed_at_ns=12)
    assert not receipt.passed
    assert receipt.detected_future_leakage
    assert TemporalFailure.FUTURE_TIMESTAMP in receipt.failures


def test_missing_duplicate_and_out_of_order_detection() -> None:
    missing = assess_temporal(datum_id="m", observed_at_ns=None, available_at_ns=1, decision_at_ns=2, consumed_at_ns=3)
    assert TemporalFailure.MISSING_TIMESTAMP in missing.failures
    failures = assess_sequence((1, 2, 2, 1))
    assert TemporalFailure.DUPLICATE_TIMESTAMP in failures
    assert TemporalFailure.OUT_OF_ORDER_SEQUENCE in failures



def test_negative_offset_fails_chronology() -> None:
    receipt = assess_temporal(
        datum_id="negative",
        observed_at_ns=100,
        available_at_ns=90,
        decision_at_ns=110,
        consumed_at_ns=120,
    )
    assert not receipt.passed
    assert TemporalFailure.NEGATIVE_OFFSET in receipt.failures


def test_clock_drift_above_bound_is_detected() -> None:
    receipt = assess_temporal(
        datum_id="drift",
        observed_at_ns=0,
        available_at_ns=101,
        decision_at_ns=200,
        consumed_at_ns=201,
        max_clock_drift_ns=100,
    )
    assert not receipt.passed
    assert TemporalFailure.CLOCK_DRIFT in receipt.failures
