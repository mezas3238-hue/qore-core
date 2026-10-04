"""L10 lab-of-the-lab checks for the data reality lane."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab import LabFault, LabIntegrityReceipt
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, ProviderDatum
from qore.infrastructure.core_stack_v2.shared_lab_temporal_harness import assess_temporal


@dataclass(frozen=True, slots=True)
class DataL10Receipt:
    injected: tuple[LabFault, ...]
    detected: tuple[LabFault, ...]
    core_receipt: LabIntegrityReceipt

    @property
    def passed(self) -> bool:
        return self.core_receipt.passed


def run_data_l10(
    *,
    stale_detected: bool,
    wrong_symbol_detected: bool,
    duplicate_detected: bool,
    fake_provider_detected: bool,
    temporal_probe: tuple[int, int, int, int],
) -> DataL10Receipt:
    injected = (
        LabFault.STALE_SENSOR,
        LabFault.FUTURE_LEAKAGE,
        LabFault.WRONG_SYMBOL_IDENTITY,
        LabFault.BROKEN_TIMESTAMP,
        LabFault.DUPLICATED_OUTPUT,
    )
    detected: list[LabFault] = []
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
    if wrong_symbol_detected or fake_provider_detected:
        detected.append(LabFault.WRONG_SYMBOL_IDENTITY)
    if duplicate_detected:
        detected.append(LabFault.DUPLICATED_OUTPUT)
    core = LabIntegrityReceipt(injected, tuple(dict.fromkeys(detected)))
    return DataL10Receipt(injected, tuple(dict.fromkeys(detected)), core)
