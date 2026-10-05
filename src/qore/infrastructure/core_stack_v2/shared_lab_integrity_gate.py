"""Global L10 aggregation for QORE Shared Lab.

Combines independently produced lane receipts and refuses L10 PASS unless every
known deliberate fault class has been injected and detected.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab import LabFault, LabIntegrityReceipt


@dataclass(frozen=True, slots=True)
class GlobalLabIntegrityAssessment:
    receipt_count: int
    injected_faults: tuple[LabFault, ...]
    detected_faults: tuple[LabFault, ...]
    missing_injections: tuple[LabFault, ...]
    missing_detections: tuple[LabFault, ...]
    duplicate_injection_faults: tuple[LabFault, ...]
    l10_global_pass: bool


def assess_global_l10(
    receipts: tuple[LabIntegrityReceipt, ...],
) -> GlobalLabIntegrityAssessment:
    if not receipts:
        raise ValueError("global L10 requires lane integrity receipts")
    injected = tuple(fault for receipt in receipts for fault in receipt.injected_faults)
    detected = tuple(fault for receipt in receipts for fault in receipt.detected_faults)
    injected_set = set(injected)
    detected_set = set(detected)
    all_faults = set(LabFault)
    missing_injections = tuple(sorted(all_faults - injected_set, key=lambda item: item.value))
    missing_detections = tuple(sorted(injected_set - detected_set, key=lambda item: item.value))
    duplicates = tuple(
        sorted(
            (fault for fault in all_faults if injected.count(fault) > 1),
            key=lambda item: item.value,
        )
    )
    passed = not missing_injections and not missing_detections
    return GlobalLabIntegrityAssessment(
        receipt_count=len(receipts),
        injected_faults=injected,
        detected_faults=detected,
        missing_injections=missing_injections,
        missing_detections=missing_detections,
        duplicate_injection_faults=duplicates,
        l10_global_pass=passed,
    )
