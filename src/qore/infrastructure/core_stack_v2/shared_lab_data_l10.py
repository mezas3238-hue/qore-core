"""L10 lab-of-the-lab checks for the data reality lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab import LabFault, LabIntegrityReceipt
from qore.infrastructure.core_stack_v2.shared_lab_temporal_harness import assess_temporal


class DataL10Fault(StrEnum):
    FAKE_PROVIDER_PROVENANCE = "FAKE_PROVIDER_PROVENANCE"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    PROVIDER_CONFLICT = "PROVIDER_CONFLICT"


@dataclass(frozen=True, slots=True)
class DataL10Receipt:
    injected: tuple[LabFault, ...]
    detected: tuple[LabFault, ...]
    data_injected: tuple[DataL10Fault, ...]
    data_detected: tuple[DataL10Fault, ...]
    core_receipt: LabIntegrityReceipt

    @property
    def missing_data_detections(self) -> tuple[DataL10Fault, ...]:
        detected = set(self.data_detected)
        return tuple(item for item in self.data_injected if item not in detected)

    @property
    def passed(self) -> bool:
        return self.core_receipt.passed and not self.missing_data_detections


def run_data_l10(
    *,
    stale_detected: bool,
    wrong_symbol_detected: bool,
    duplicate_detected: bool,
    fake_provider_detected: bool,
    temporal_probe: tuple[int, int, int, int],
    missing_observation_detected: bool = False,
    provider_conflict_detected: bool = False,
) -> DataL10Receipt:
    injected = (
        LabFault.STALE_SENSOR,
        LabFault.FUTURE_LEAKAGE,
        LabFault.WRONG_SYMBOL_IDENTITY,
        LabFault.BROKEN_TIMESTAMP,
        LabFault.DUPLICATED_OUTPUT,
    )
    data_injected = (
        DataL10Fault.FAKE_PROVIDER_PROVENANCE,
        DataL10Fault.MISSING_OBSERVATION,
        DataL10Fault.PROVIDER_CONFLICT,
    )

    detected: list[LabFault] = []
    data_detected: list[DataL10Fault] = []

    if stale_detected:
        detected.append(LabFault.STALE_SENSOR)

    temporal = assess_temporal(
        datum_id="l10",
        observed_at_ns=temporal_probe[0],
        available_at_ns=temporal_probe[1],
        decision_at_ns=temporal_probe[2],
        consumed_at_ns=temporal_probe[3],
    )
    if temporal.detected_future_leakage:
        detected.append(LabFault.FUTURE_LEAKAGE)
    if temporal.failures:
        detected.append(LabFault.BROKEN_TIMESTAMP)
    if wrong_symbol_detected:
        detected.append(LabFault.WRONG_SYMBOL_IDENTITY)
    if duplicate_detected:
        detected.append(LabFault.DUPLICATED_OUTPUT)

    if fake_provider_detected:
        data_detected.append(DataL10Fault.FAKE_PROVIDER_PROVENANCE)
    if missing_observation_detected:
        data_detected.append(DataL10Fault.MISSING_OBSERVATION)
    if provider_conflict_detected:
        data_detected.append(DataL10Fault.PROVIDER_CONFLICT)

    core = LabIntegrityReceipt(injected, tuple(dict.fromkeys(detected)))
    return DataL10Receipt(
        injected,
        tuple(dict.fromkeys(detected)),
        data_injected,
        tuple(dict.fromkeys(data_detected)),
        core,
    )
