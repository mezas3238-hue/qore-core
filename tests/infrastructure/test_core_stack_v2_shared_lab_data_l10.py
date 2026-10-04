from qore.infrastructure.core_stack_v2.shared_lab import LabFault
from qore.infrastructure.core_stack_v2.shared_lab_data_l10 import run_data_l10


def test_l10_known_failures_are_detected() -> None:
    receipt = run_data_l10(
        stale_detected=True,
        wrong_symbol_detected=True,
        duplicate_detected=True,
        fake_provider_detected=True,
        temporal_probe=(0, 11, 10, 12),
        missing_observation_detected=True,
        provider_conflict_detected=True,
    )
    assert receipt.passed
    assert set(receipt.injected) == set(receipt.detected)


def test_l10_fails_if_known_failure_escapes_detection() -> None:
    receipt = run_data_l10(
        stale_detected=False,
        wrong_symbol_detected=False,
        duplicate_detected=False,
        fake_provider_detected=False,
        temporal_probe=(0, 1, 10, 11),
    )
    assert not receipt.passed
    assert LabFault.STALE_SENSOR in receipt.core_receipt.missing_detections
